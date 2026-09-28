"""Evaluation transport: one sealed request through Claude Code on the Church account.

The harness builds Anthropic-format Messages payloads and runs a tool loop for
DeepSeek. Claude Code runs its own loop, so each payload becomes one `claude -p`
session with the payload's own system text and task, native web search, and the
harness's `open_url` fetcher served over MCP (`open_url_mcp`). The session's
stream is converted back into one Anthropic-format response the harness already
validates: native searches as `server_tool_use` / `web_search_tool_result`
blocks, then the final text. Fetches are preserved under `claudeCode.fetches`.

Account guard (the $125 personal overage of September 2026 must not recur):
`prepare()` refuses unless `claude auth status` shows the Church enterprise
subscription, every run strips Anthropic API credentials from the environment,
and a response whose session was billed to an API key is refused.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .protocol import EvaluationError

CHURCH_DOMAIN = '@churchofjesuschrist.org'
CHURCH_ORG = 'Church of Jesus Christ'
STRIPPED = ['ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_USE_BEDROCK',
            'CLAUDE_CODE_USE_VERTEX', 'ANTHROPIC_BEDROCK_BASE_URL', 'ANTHROPIC_VERTEX_PROJECT_ID']
OPEN_URL = 'mcp__scout__open_url'


def clean_environment():
    env = {k: v for k, v in os.environ.items() if k not in STRIPPED}
    env['DISABLE_AUTOUPDATER'] = '1'
    return env


def check_account(status):
    """The parsed `claude auth status`; raises unless it is the Church enterprise plan."""
    if (not status.get('loggedIn') or status.get('authMethod') != 'claude.ai'
            or status.get('subscriptionType') != 'enterprise' or status.get('orgName') != CHURCH_ORG
            or not str(status.get('email', '')).endswith(CHURCH_DOMAIN)):
        raise EvaluationError('Claude Code is not signed in to the Church enterprise account; refusing to run')
    return status


def _user_text(content):
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if block.get('type') == 'text':
            parts.append(block['text'])
        elif block.get('type') == 'tool_result':
            parts.append('[tool result]\n' + str(block.get('content', ''))[:4000])
    return '\n'.join(parts)


def prompt_from(messages):
    """The first message is the sealed task. A continuation (a length recovery or a
    harness follow-up) replays the earlier turns as a plain transcript, because a
    Claude Code session cannot be seeded with foreign assistant blocks."""
    if not messages or messages[0].get('role') != 'user':
        raise EvaluationError('The first message must be the user task')
    if len(messages) == 1:
        return _user_text(messages[0]['content'])
    lines = ['The conversation so far follows. Continue it.', '', '[user]', _user_text(messages[0]['content'])]
    for message in messages[1:]:
        if message['role'] == 'assistant':
            text = '\n'.join(b.get('text', '') for b in message['content'] if b.get('type') == 'text')
            lines += ['', '[assistant]', text]
        else:
            lines += ['', '[user]', _user_text(message['content'])]
    return '\n'.join(lines)


def _search_links(text):
    match = re.search(r'Links:\s*(\[.*?\])\s*(?:\n|$)', text, re.S)
    if match:
        try:
            links = json.loads(match.group(1))
            return [dict(type='web_search_result', url=link['url'], title=link.get('title', ''))
                    for link in links if isinstance(link, dict) and link.get('url')]
        except json.JSONDecodeError:
            pass
    return [dict(type='web_search_result', url=url, title='') for url in dict.fromkeys(re.findall(r'https?://[^\s"\)\]]+', text))]


def _tool_text(content):
    if isinstance(content, str):
        return content
    return '\n'.join(b.get('text', '') for b in content if isinstance(b, dict))


def normalize_final(text):
    """Claude Code's web search asks for a "Sources:" list after the answer; the
    harness accepts an appendix only as "Source notes". Relabel it, nothing else."""
    body = text.strip()
    fence = ''
    if body.startswith('```'):
        first, _, rest = body.partition('\n')
        if '```' in rest:
            data, _, after = rest.partition('```')
            fence, body = first, data.strip() + '\n' + after.strip()
    try:
        _, end = json.JSONDecoder().raw_decode(body)
    except json.JSONDecodeError:
        return text
    head, tail = body[:end], body[end:].strip()
    if tail.startswith('Source notes'):
        pass  # Already relabelled.
    elif tail.startswith('Sources:'):
        tail = 'Source notes (Claude Code web-search citations):' + tail[len('Sources:'):]
    elif re.match(r'Sources?\b', tail):
        tail = 'Source notes (Claude Code web-search citations):\n' + tail
    return head + ('\n' + tail if tail else '')


def convert_stream(lines, requested_model):
    """Claude Code stream-json lines -> one Anthropic-format response body."""
    events = [json.loads(line) for line in lines if line.strip()]
    init = next((e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init'), {})
    result = next((e for e in reversed(events) if e.get('type') == 'result'), None)
    if result is None:
        return {'error': {'claudeCode': 'No result event', 'events': len(events)}}
    if init.get('apiKeySource') not in (None, 'none'):
        return {'error': {'claudeCode': 'Session was billed to an API key, not the Church subscription',
                          'apiKeySource': init.get('apiKeySource')}}
    searches, results, fetch_calls = {}, {}, []
    for event in events:
        if event.get('type') not in ('assistant', 'user'):
            continue
        for block in event['message'].get('content', []):
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('name') == 'WebSearch':
                searches[block['id']] = block.get('input', {})
            elif block.get('type') == 'tool_use' and block.get('name') == OPEN_URL:
                fetch_calls.append(block.get('input', {}).get('url'))
            elif block.get('type') == 'tool_result' and block.get('tool_use_id') in searches:
                results[block['tool_use_id']] = block
    content = []
    for call_id, query in searches.items():
        content.append(dict(type='server_tool_use', id=call_id, name='web_search', input=query))
        outcome = results.get(call_id)
        if outcome is None or outcome.get('is_error'):
            content.append(dict(type='web_search_tool_result', tool_use_id=call_id,
                                content={'type': 'web_search_tool_result_error', 'error_code': 'unavailable'}))
        else:
            content.append(dict(type='web_search_tool_result', tool_use_id=call_id,
                                content=_search_links(_tool_text(outcome.get('content', '')))))
    if result.get('is_error') or result.get('subtype') != 'success':
        return {'error': {'claudeCode': result.get('subtype'), 'result': str(result.get('result', ''))[:4000]}}
    content.append(dict(type='text', text=normalize_final(result.get('result', ''))))
    usage = result.get('usage', {})
    models = result.get('modelUsage', {})
    return dict(id=result.get('session_id'), type='message', role='assistant',
                model=init.get('model') or requested_model, content=content, stop_reason='end_turn',
                usage={k: usage.get(k) for k in ['input_tokens', 'cache_read_input_tokens',
                                                 'cache_creation_input_tokens', 'output_tokens']},
                claudeCode=dict(numTurns=result.get('num_turns'), durationMs=result.get('duration_ms'),
                                apiEquivalentCostUsd=result.get('total_cost_usd'), modelUsage=models,
                                apiKeySource=init.get('apiKeySource'), openUrlCalls=fetch_calls,
                                rateLimits=[e.get('rate_limit_info') for e in events if e.get('type') == 'rate_limit_event']))


class ClaudeCodeTransport:
    is_live = True

    def __init__(self, endpoint, binary=None):
        self.endpoint = endpoint
        self.binary = binary or shutil.which('claude')
        self._checked = False

    def prepare(self):
        if not self.binary:
            raise EvaluationError('Claude Code CLI not found')
        status = subprocess.run([self.binary, 'auth', 'status'], capture_output=True, text=True,
                                env=clean_environment(), stdin=subprocess.DEVNULL, timeout=60)
        check_account(json.loads(status.stdout))
        self._checked = True

    def command(self, payload, prompt, mcp_config):
        return [self.binary, '-p', prompt, '--system-prompt', payload['system'],
                '--model', payload['model'], '--effort', payload.get('output_config', {}).get('effort', 'high'),
                '--tools', 'WebSearch', '--allowedTools', 'WebSearch', OPEN_URL,
                '--mcp-config', str(mcp_config), '--strict-mcp-config', '--setting-sources', '',
                '--no-session-persistence', '--output-format', 'stream-json', '--verbose']

    def __call__(self, payload, timeout):
        if not self._checked:
            raise EvaluationError('Account preflight required')
        prompt = prompt_from(payload['messages'])
        with tempfile.TemporaryDirectory(prefix='scout-claude-') as work:
            work = Path(work)
            evidence = work / 'evidence'
            env = clean_environment()
            env['SCOUT_EVIDENCE_DIR'] = str(evidence)
            root = Path(__file__).resolve().parents[2]
            mcp_config = work / 'mcp.json'
            mcp_config.write_text(json.dumps({'mcpServers': {'scout': {
                'command': sys.executable, 'args': ['-m', 'resource_research_agent.evaluation.open_url_mcp'],
                'env': {'PYTHONPATH': str(root), 'SCOUT_EVIDENCE_DIR': str(evidence)}}}}))
            started = time.monotonic()
            try:
                run = subprocess.run(self.command(payload, prompt, mcp_config), capture_output=True, text=True,
                                     cwd=work, env=env, stdin=subprocess.DEVNULL, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                body = {'error': {'claudeCode': 'timeout', 'timeoutSeconds': timeout,
                                  'partialStream': (error.stdout or b'')[-4000:].decode('utf-8', 'replace')
                                  if isinstance(error.stdout, bytes) else str(error.stdout or '')[-4000:]}}
                return json.dumps(body).encode()
            body = convert_stream(run.stdout.splitlines(), payload['model'])
            if run.returncode != 0 and 'error' not in body:
                body = {'error': {'claudeCode': 'exit ' + str(run.returncode), 'stderr': run.stderr[-4000:]}}
            if 'error' not in body:
                body['claudeCode']['elapsedSeconds'] = time.monotonic() - started
                body['claudeCode']['fetches'] = [json.loads(p.read_text()) for p in sorted(evidence.glob('fetch-*.json'))]
            return json.dumps(body, ensure_ascii=False).encode()
