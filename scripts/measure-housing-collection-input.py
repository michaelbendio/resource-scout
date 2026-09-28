#!/usr/bin/env python3
"""Offline only: measure a frozen first request using DeepSeek's V4.1 tokenizer.

Run with a Python environment containing tokenizers. The tokenizer JSON comes
from deepseek-ai/deepseek-recipe/static/tokenizers/v41/tokenizer.json; its pinned
hash is checked below. No model calls or network requests are made here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resource_research_agent.evaluation.deepseek import (
    OFFICIAL_V41_TOKENIZER_SHA256, measured_initial_allowance)
from resource_research_agent.evaluation.protocol import digest, now, read, write_once


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment',type=Path,required=True)
    parser.add_argument('--assignment',choices=['reviewed-collection','import-reconciliation'],required=True)
    parser.add_argument('--tokenizer',type=Path,required=True)
    args=parser.parse_args()
    raw=args.tokenizer.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=OFFICIAL_V41_TOKENIZER_SHA256:
        raise ValueError('Official tokenizer hash mismatch')
    request=read(args.experiment/'attempts'/(args.assignment+'-00')/'request.json')
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_str(raw.decode())
    text=request['messages'][0]['content']
    proof=dict(requestSha256=digest(request),tokenizerSha256=OFFICIAL_V41_TOKENIZER_SHA256,
        tokenizerSource='https://github.com/deepseek-ai/deepseek-recipe/tree/main/static/tokenizers/v41',
        method='official-v41-plain-text-with-headroom',
        textTokens=len(tokenizer.encode(text,add_special_tokens=False).ids),
        recordedBy='Codex supervisor',recordedAt=now(),
        reason='Retain the complete authorized Housing evidence. Replace the overly conservative byte count for this exact plain-text first request with the official offline count plus 25 percent headroom, byte-counted metadata and 8192 framing tokens. Native API usage remains authoritative; this is not billing.')
    allowance=measured_initial_allowance(request,proof)
    write_once(args.experiment/'context-token-counts'/(args.assignment+'.json'),proof)
    print(json.dumps(dict(textTokens=proof['textTokens'],inputTokenAllowance=allowance,
                         outputAllowance=request['max_tokens'])))


if __name__=='__main__':main()
