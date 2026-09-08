"""Lossless storage for large research projects; small/legacy rows stay plain JSON."""
import base64
import json
import zlib


COMPRESSION_THRESHOLD = 8 * 1024 * 1024
ENCODING = 'scout-project-json-zlib-v1'
# Large checkpoints are rewritten for each assignment/result. Prefer fast saves
# over the smallest file; zlib streams remain readable by the existing decoder.
COMPRESSION_LEVEL = zlib.Z_BEST_SPEED


def encode_project_state(state):
    payload = json.dumps(state, ensure_ascii=False)
    if len(payload) < COMPRESSION_THRESHOLD:
        return payload
    return json.dumps({'_scoutStateEncoding': ENCODING,
                      'payload': base64.b64encode(zlib.compress(
                          payload.encode('utf-8'), level=COMPRESSION_LEVEL)).decode('ascii')})


def decode_project_state(payload):
    state = json.loads(payload)
    if isinstance(state, dict) and '_scoutStateEncoding' in state:
        if state.get('_scoutStateEncoding') != ENCODING or set(state) != {'_scoutStateEncoding', 'payload'}:
            raise ValueError('Unsupported Scout project storage encoding')
        state = json.loads(zlib.decompress(base64.b64decode(state['payload'], validate=True)))
    return state
