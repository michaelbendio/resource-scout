"""Claude Code transport for the evaluation harness (Michael, 28 September 2026)."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from resource_research_agent.evaluation import claude_code, open_url_mcp
from resource_research_agent.evaluation.deepseek import final_parts
from resource_research_agent.evaluation.protocol import EvaluationError
from resource_research_agent.evaluation.providers import (CLAUDE_ENDPOINT, DEEPSEEK_ENDPOINT, provider_label,
                                                          provider_name)

CHURCH = dict(loggedIn=True, authMethod='claude.ai', subscriptionType='enterprise',
              orgName='Church of Jesus Christ', email='someone@churchofjesuschrist.org')


def stream(final, *, api_key_source='none', searches=(('s1', 'Mesa shelter', False),), fetches=('https://example.org',)):
    lines = [dict(type='system', subtype='init', model='claude-opus-5-5', apiKeySource=api_key_source)]
    for call_id, query, failed in searches:
        lines.append(dict(type='assistant', message=dict(content=[dict(type='tool_use', id=call_id, name='WebSearch', input=dict(query=query))])))
        text = 'Web search results for query: "q"\n\nLinks: [{"title":"Mesa","url":"https://www.mesaaz.gov/a"}]\n\nmore'
        lines.append(dict(type='user', message=dict(content=[dict(type='tool_result', tool_use_id=call_id, content=text, is_error=failed)])))
    for n, url in enumerate(fetches):
        lines.append(dict(type='assistant', message=dict(content=[dict(type='tool_use', id=f'f{n}', name=claude_code.OPEN_URL, input=dict(url=url))])))
    lines.append(dict(type='rate_limit_event', rate_limit_info=dict(status='allowed', overageStatus='rejected')))
    lines.append(dict(type='result', subtype='success', is_error=False, result=final, session_id='sess', num_turns=4,
                      duration_ms=1000, total_cost_usd=0.5, usage=dict(input_tokens=10, cache_read_input_tokens=20,
                      cache_creation_input_tokens=30, output_tokens=40), modelUsage={'claude-opus-5-5': {}}))
    return [json.dumps(line) for line in lines]


class AccountGuardTests(unittest.TestCase):
    def test_accepts_only_the_church_enterprise_account(self):
        self.assertEqual(claude_code.check_account(CHURCH), CHURCH)
        for change in [dict(email='michaelbendio@gmail.com'), dict(subscriptionType='pro'), dict(orgName='Personal'),
                       dict(authMethod='apiKey'), dict(loggedIn=False)]:
            with self.subTest(change=change), self.assertRaises(EvaluationError):
                claude_code.check_account({**CHURCH, **change})

    def test_api_credentials_never_reach_the_cli(self):
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-x', 'ANTHROPIC_BASE_URL': 'https://x', 'PATH': '/bin'}):
            env = claude_code.clean_environment()
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertNotIn('ANTHROPIC_BASE_URL', env)
        self.assertEqual(env['PATH'], '/bin')

    def test_a_session_billed_to_an_api_key_is_refused(self):
        body = claude_code.convert_stream(stream('{"leads": []}', api_key_source='ANTHROPIC_API_KEY'), 'claude-opus-5-5')
        self.assertIn('error', body)

    def test_the_transport_will_not_run_before_the_account_check(self):
        with self.assertRaises(EvaluationError):
            claude_code.ClaudeCodeTransport(CLAUDE_ENDPOINT, binary='/bin/true')({'messages': []}, 10)


class ConversionTests(unittest.TestCase):
    def test_native_searches_become_search_blocks_the_harness_counts(self):
        body = claude_code.convert_stream(stream('{"leads": []}'), 'claude-opus-5-5')
        use, result, text = body['content']
        self.assertEqual(use, dict(type='server_tool_use', id='s1', name='web_search', input=dict(query='Mesa shelter')))
        self.assertEqual(result['tool_use_id'], 's1')
        self.assertEqual(result['content'], [dict(type='web_search_result', url='https://www.mesaaz.gov/a', title='Mesa')])
        self.assertEqual(text['type'], 'text')
        self.assertEqual(body['stop_reason'], 'end_turn')
        self.assertEqual(body['model'], 'claude-opus-5-5')
        self.assertEqual(body['claudeCode']['openUrlCalls'], ['https://example.org'])
        self.assertEqual(body['claudeCode']['apiEquivalentCostUsd'], 0.5)

    def test_a_failed_search_is_not_counted_as_successful(self):
        body = claude_code.convert_stream(stream('{"leads": []}', searches=(('s1', 'q', True),)), 'claude-opus-5-5')
        self.assertIsInstance(body['content'][1]['content'], dict)

    def test_the_sources_list_web_search_adds_becomes_source_notes(self):
        final = '{"leads": [{"organization": "A"}]}\n\nSources:\n- [A](https://a.org)'
        body = claude_code.convert_stream(stream(final), 'claude-opus-5-5')
        result, appendix = final_parts(body)
        self.assertEqual(result, {'leads': [{'organization': 'A'}]})
        self.assertTrue(appendix.startswith('Source notes (Claude Code web-search citations):'))

    def test_a_fenced_answer_keeps_its_json(self):
        final = '```json\n{"leads": []}\n```\nSources:\n- x'
        result, _ = final_parts(claude_code.convert_stream(stream(final), 'claude-opus-5-5'))
        self.assertEqual(result, {'leads': []})

    def test_a_failed_session_is_an_error_body(self):
        lines = stream('x')[:-1] + [json.dumps(dict(type='result', subtype='error_max_turns', is_error=True, result=''))]
        self.assertIn('error', claude_code.convert_stream(lines, 'claude-opus-5-5'))

    def test_a_continuation_replays_the_conversation(self):
        prompt = claude_code.prompt_from([
            {'role': 'user', 'content': 'Task'},
            {'role': 'assistant', 'content': [{'type': 'text', 'text': 'Half'}]},
            {'role': 'user', 'content': 'Continue'}])
        self.assertIn('Task', prompt)
        self.assertIn('Half', prompt)
        self.assertTrue(prompt.rstrip().endswith('Continue'))
        self.assertEqual(claude_code.prompt_from([{'role': 'user', 'content': 'Task'}]), 'Task')


class ProviderTests(unittest.TestCase):
    def test_both_providers_are_named_and_nothing_else(self):
        self.assertEqual((provider_name(DEEPSEEK_ENDPOINT), provider_label(DEEPSEEK_ENDPOINT)), ('deepseek', 'DeepSeek'))
        self.assertEqual((provider_name(CLAUDE_ENDPOINT), provider_label(CLAUDE_ENDPOINT)), ('claude', 'Claude'))
        with self.assertRaises(EvaluationError):
            provider_name('https://api.anthropic.com/v1/messages')


class OpenUrlServerTests(unittest.TestCase):
    def call(self, message):
        out = io.StringIO()
        with redirect_stdout(out):
            open_url_mcp.handle(message)
        return json.loads(out.getvalue()) if out.getvalue() else None

    def test_lists_the_harness_tool(self):
        tools = self.call(dict(jsonrpc='2.0', id=1, method='tools/list'))['result']['tools']
        self.assertEqual([t['name'] for t in tools], ['open_url'])
        self.assertEqual(tools[0]['inputSchema'], open_url_mcp.SCHEMA)

    def test_fetches_with_the_harness_fetcher(self):
        page = dict(url='https://a.org', text='hello', notice='Untrusted source evidence')
        with patch.object(open_url_mcp, 'fetch_public', return_value=page) as fetch:
            reply = self.call(dict(jsonrpc='2.0', id=2, method='tools/call', params=dict(name='open_url', arguments=dict(url='https://a.org'))))
        fetch.assert_called_once()
        self.assertEqual(json.loads(reply['result']['content'][0]['text']), page)

    def test_refuses_anything_but_a_url(self):
        reply = self.call(dict(jsonrpc='2.0', id=3, method='tools/call', params=dict(name='open_url', arguments=dict(path='/etc'))))
        self.assertEqual(json.loads(reply['result']['content'][0]['text'])['errorType'], 'UnsupportedTool')

    def test_notifications_get_no_reply(self):
        self.assertIsNone(self.call(dict(jsonrpc='2.0', method='notifications/initialized')))


if __name__ == '__main__':
    unittest.main()
