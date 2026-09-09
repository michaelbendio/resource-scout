"""Lossless storage for large research projects; small/legacy rows stay plain JSON."""
import base64
import json
import zlib
from .performance import measured
from .checkpoint_compaction import compact_state, expand_state


COMPRESSION_THRESHOLD = 8 * 1024 * 1024
ENCODING = 'scout-project-json-zlib-v1'
COMPACT_ENCODING = 'scout-project-shared-json-zlib-v2'
# Large checkpoints are rewritten for each assignment/result. Prefer fast saves
# over the smallest file. Shared-context envelopes require the v2 decoder.
COMPRESSION_LEVEL = zlib.Z_BEST_SPEED


def encode_project_state(state, *, compact=True):
    encoding = ENCODING
    serializable = state
    if compact:
        with measured('checkpoint.share_repeated_context'):
            shared = compact_state(state)
        if shared is not None:
            serializable = shared
            encoding = COMPACT_ENCODING
    with measured('checkpoint.json_encode') as metrics:
        payload = json.dumps(serializable, ensure_ascii=False)
        metrics['characters'] = len(payload)
    if len(payload) < COMPRESSION_THRESHOLD and encoding == ENCODING:
        return payload
    with measured('checkpoint.compress') as metrics:
        raw = payload.encode('utf-8')
        compressed = zlib.compress(raw, level=COMPRESSION_LEVEL)
        metrics.update(inputBytes=len(raw), outputBytes=len(compressed))
    with measured('checkpoint.envelope_encode'):
        return json.dumps({'_scoutStateEncoding': encoding,
                          'payload': base64.b64encode(compressed).decode('ascii')})


def decode_project_state(payload):
    with measured('checkpoint.json_decode') as metrics:
        state = json.loads(payload)
        metrics['characters'] = len(payload)
    if isinstance(state, dict) and '_scoutStateEncoding' in state:
        if state.get('_scoutStateEncoding') not in (ENCODING, COMPACT_ENCODING) or set(state) != {'_scoutStateEncoding', 'payload'}:
            raise ValueError('Unsupported Scout project storage encoding')
        encoding = state['_scoutStateEncoding']
        with measured('checkpoint.decompress') as metrics:
            raw = zlib.decompress(base64.b64decode(state['payload'], validate=True))
            metrics['outputBytes'] = len(raw)
        with measured('checkpoint.inner_json_decode'):
            state = json.loads(raw)
        if encoding == COMPACT_ENCODING:
            with measured('checkpoint.expand_shared_context'):
                state = expand_state(state)
    return state
