"""Lossless sharing of repeated, large research context within one checkpoint.

References live outside the resource data. A user's nulls or dictionary keys can
never be mistaken for a reference. No assignment, result or provenance is edited.
"""
from copy import deepcopy
import json

SHARED_FIELDS = frozenset({'knownIdentities', 'writingGuidance', 'playbooks', 'catalog',
                           'primaryResult', 'frozenResult', 'passResults', 'blindResults'})
MIN_FIELD_CHARACTERS = 4096
MIN_SAVING_CHARACTERS = 1024 * 1024


def compact_state(state):
    shared, replacements, indexes = [], [], {}
    saved = 0
    non_string_keys = False

    def walk(value, path):
        nonlocal saved, non_string_keys
        if isinstance(value, dict):
            if any(not isinstance(k, str) for k in value):
                non_string_keys = True
            out = {}
            for key, child in value.items():
                if key in SHARED_FIELDS and isinstance(child, (dict, list)):
                    serialized = json.dumps(child, ensure_ascii=False)
                    if len(serialized) >= MIN_FIELD_CHARACTERS:
                        index = indexes.get(serialized)
                        if index is None:
                            index = len(shared); indexes[serialized] = index; shared.append(child)
                        else:
                            saved += len(serialized)
                        replacements.append([path + [key], index]); out[key] = None
                        continue
                out[key] = walk(child, path + [key])
            return out
        if isinstance(value, list):
            return [walk(child, path + [i]) for i, child in enumerate(value)]
        return value

    try:
        skeleton = walk(state, [])
    except RecursionError:
        return None  # Let the ordinary JSON encoder handle unsupported depth/cycles.
    if non_string_keys or saved < MIN_SAVING_CHARACTERS:
        return None
    return {'state': skeleton, 'shared': shared, 'replacements': replacements}


def expand_state(document):
    if not isinstance(document, dict) or set(document) != {'state', 'shared', 'replacements'}:
        raise ValueError('Malformed compact checkpoint')
    state, shared, replacements = document['state'], document['shared'], document['replacements']
    if not isinstance(shared, list) or not isinstance(replacements, list):
        raise ValueError('Malformed checkpoint shared sections')
    seen = set()
    for replacement in replacements:
        if not isinstance(replacement, list) or len(replacement) != 2:
            raise ValueError('Malformed checkpoint reference')
        path, index = replacement
        if (not isinstance(path, list) or not path or any(type(p) not in (str, int) for p in path)
                or type(index) is not int or not 0 <= index < len(shared)):
            raise ValueError('Invalid checkpoint reference')
        location = tuple(path)
        if location in seen or any(location[:i] in seen for i in range(1,len(location))):
            raise ValueError('Duplicate checkpoint reference')
        seen.add(location)
        target = state
        try:
            for part in path[:-1]:
                if isinstance(target, list) and (type(part) is not int or part < 0):
                    raise ValueError('Invalid checkpoint list path')
                target = target[part]
            key = path[-1]
            if isinstance(target, list) and (type(key) is not int or key < 0):
                raise ValueError('Invalid checkpoint list path')
            if target[key] is not None:
                raise ValueError('Checkpoint reference must replace its own empty slot')
            # Distinct assignments remain distinct mutable objects after loading.
            target[key] = deepcopy(shared[index])
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError('Invalid checkpoint reference path') from error
    return state
