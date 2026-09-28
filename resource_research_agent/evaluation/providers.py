"""Which provider an evaluation's sealed endpoint names, and its transport.

DeepSeek is reached over its Anthropic-format API with the Mac's DeepSeek key.
Claude is reached through the Claude Code CLI signed in to the Church enterprise
account (Michael, 28 September 2026: "Let's use Claude"), never an API key.
"""
from __future__ import annotations

from .protocol import EvaluationError

DEEPSEEK_ENDPOINT = 'https://api.deepseek.com/anthropic/v1/messages'
CLAUDE_ENDPOINT = 'claude-code-cli:church-enterprise'

_PROVIDERS = {DEEPSEEK_ENDPOINT: ('deepseek', 'DeepSeek'), CLAUDE_ENDPOINT: ('claude', 'Claude')}


def _known(endpoint):
    if endpoint not in _PROVIDERS:
        raise EvaluationError('Unknown provider endpoint; only DeepSeek and Claude Code are supported')
    return _PROVIDERS[endpoint]


def provider_name(endpoint):
    """The billing provider an authorization must name."""
    return _known(endpoint)[0]


def provider_label(endpoint):
    """The provider's name as prompts and reports show it."""
    return _known(endpoint)[1]


def make_transport(endpoint):
    name = provider_name(endpoint)
    if name == 'claude':
        from .claude_code import ClaudeCodeTransport
        return ClaudeCodeTransport(endpoint)
    from .deepseek import LiveTransport
    return LiveTransport(endpoint)


def experiment_label(root):
    """The provider label for an experiment folder; folders made before Claude was
    supported, and test fixtures without a config, are DeepSeek's."""
    from pathlib import Path
    from .protocol import read
    config = Path(root) / 'config.json'
    return provider_label(read(config)['provider']['endpoint']) if config.exists() else 'DeepSeek'
