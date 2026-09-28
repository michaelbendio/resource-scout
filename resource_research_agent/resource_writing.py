"""Versioned writing guidance and composition, independent of research strategy."""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_GUIDANCE_PATH = Path(__file__).with_name('writing_guidance') / 'default.json'


class ResourceWritingError(ValueError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode('utf-8')).hexdigest()


def validate_guidance(bundle: Any) -> dict[str, Any]:
    if (not isinstance(bundle, dict) or type(bundle.get('schemaVersion')) is not int
            or bundle['schemaVersion'] != 1):
        raise ResourceWritingError('Unsupported writing guidance schema')
    for key in ('version', 'instructionsFile', 'instructionsText'):
        if not isinstance(bundle.get(key), str) or not bundle[key].strip():
            raise ResourceWritingError(f'Writing guidance needs {key}')
    sections = bundle.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ResourceWritingError('Writing guidance needs section definitions')
    keys, headings = set(), set()
    for section in sections:
        if not isinstance(section, dict) or set(section) != {'key', 'heading'}:
            raise ResourceWritingError('Malformed writing section definition')
        key, heading = section['key'], section['heading']
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][A-Za-z0-9]*', key):
            raise ResourceWritingError('Invalid writing section key')
        if (not isinstance(heading, str) or not heading.strip()
                or heading != heading.strip() or any(c in heading for c in '\r\n*#<>_')):
            raise ResourceWritingError('Invalid writing section heading')
        if key in keys or heading.casefold() in headings:
            raise ResourceWritingError('Duplicate writing section key or heading')
        keys.add(key)
        headings.add(heading.casefold())
    retired = bundle.get('retiredHeadings')
    if (not isinstance(retired, list)
            or any(not isinstance(h, str) or not h.strip() or '\n' in h or '\r' in h for h in retired)):
        raise ResourceWritingError('Malformed retired writing headings')
    if headings.intersection(h.casefold() for h in retired):
        raise ResourceWritingError('Active writing heading is also retired')
    expected = _digest({k: v for k, v in bundle.items() if k != 'sha256'})
    if bundle.get('sha256') != expected:
        raise ResourceWritingError('Writing guidance hash does not match its content')
    return bundle


def load_writing_guidance(path: str | Path | None = None) -> dict[str, Any]:
    path = Path(path) if path is not None else DEFAULT_GUIDANCE_PATH
    try:
        definition = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(definition, dict) or 'instructionsText' in definition or 'sha256' in definition:
            raise ResourceWritingError('Malformed writing guidance definition')
        ref = definition.get('instructionsFile')
        if not isinstance(ref, str) or not ref.strip():
            raise ResourceWritingError('Writing guidance needs instructionsFile')
        instructions = (path.parent / ref).resolve()
        if not instructions.is_relative_to(path.parent.resolve()):
            raise ResourceWritingError('Writing instructions must be inside the guidance directory')
        bundle = {**definition, 'instructionsText': instructions.read_text(encoding='utf-8')}
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ResourceWritingError(f'Cannot load writing guidance: {error}') from error
    bundle['sha256'] = _digest(bundle)
    return validate_guidance(bundle)


def compose_information(sections: Any, bundle: dict[str, Any]) -> str:
    validate_guidance(bundle)
    expected = {section['key'] for section in bundle['sections']}
    if not isinstance(sections, dict) or set(sections) != expected:
        raise ResourceWritingError('Information sections must match the assigned section keys exactly')
    reserved = [s['heading'] for s in bundle['sections']] + bundle['retiredHeadings']
    heading_pattern = re.compile(
        r'^\s*(?:#{1,6}\s*)?(?:\*\*|__)?(?:'
        + '|'.join(re.escape(h) for h in reserved)
        + r')(?:\*\*|__)?\s*(?::|$)', re.IGNORECASE
    )
    blocks = []
    for section in bundle['sections']:
        body = sections[section['key']]
        if not isinstance(body, str) or not body.strip():
            raise ResourceWritingError(f"{section['heading']} needs a nonempty section body")
        body = body.replace('\r\n', '\n').replace('\r', '\n').strip()
        if any(heading_pattern.match(line) for line in body.splitlines()):
            raise ResourceWritingError('Section bodies must not contain reserved headings')
        blocks.append(f"**{section['heading']}**\n{body}")
    return '\n\n'.join(blocks)


def normalize_written_resource(resource: Any, bundle: dict[str, Any]) -> tuple[dict, dict]:
    if not isinstance(resource, dict):
        raise ResourceWritingError('Every written resource must be an object')
    if 'informationText' in resource:
        raise ResourceWritingError('Return informationSections, not competing informationText')
    if 'email' in resource:
        raise ResourceWritingError('Put email in How to Best Connect; there is no email resource field')
    if not isinstance(resource.get('description'), str) or not resource['description'].strip():
        raise ResourceWritingError('Every written resource needs a nonempty Description')
    if resource.get('verifiedOn') not in (None, ''):
        raise ResourceWritingError('AI curation cannot set a human verifiedOn date')
    text = compose_information(resource.get('informationSections'), bundle)
    evidence = resource.get('writingEvidence')
    if not isinstance(evidence, dict) or set(evidence) != {'candidateIds', 'sources'}:
        raise ResourceWritingError('writingEvidence needs candidateIds and sources')
    refs, sources = evidence['candidateIds'], evidence['sources']
    if (not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs)
            or not isinstance(sources, list) or not (refs or sources)):
        raise ResourceWritingError('Writing evidence needs supporting candidate IDs or sources')
    candidates = resource.get('candidateIds')
    if not isinstance(candidates, list) or any(not isinstance(c, str) for c in candidates):
        raise ResourceWritingError('Written resources need candidateIds')
    if set(refs) - set(candidates):
        raise ResourceWritingError('Writing evidence references unknown contributing candidates')
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'url', 'accessedOn', 'excerpt'}:
            raise ResourceWritingError('New writing sources need url, accessedOn, and excerpt')
        if any(not isinstance(value, str) or not value.strip() for value in source.values()):
            raise ResourceWritingError('New writing source fields must be nonempty text')
        parsed = urlparse(source['url'])
        if parsed.scheme not in {'https', 'http'} or not parsed.netloc:
            raise ResourceWritingError('Writing source needs an HTTP(S) URL')
        try:
            date.fromisoformat(source['accessedOn'])
        except ValueError as error:
            raise ResourceWritingError('Writing source accessedOn must be an ISO date') from error
    metadata = {
        'informationSections': deepcopy(resource['informationSections']),
        'evidence': deepcopy(evidence),
        'guidanceSha256': bundle['sha256'],
    }
    normalized = deepcopy(resource)
    normalized.pop('informationSections')
    normalized.pop('writingEvidence')
    normalized['informationText'] = text
    from .open_questions import make_questions
    from .improvement_packages import ImprovementError
    if 'openQuestions' in resource:
        try:
            normalized['openQuestions'] = make_questions(resource['openQuestions'], {'kind':'scout-curation', 'resourceId':resource.get('id')})
        except ImprovementError as error:
            raise ResourceWritingError(str(error)) from error
    normalized['verifiedOn'] = None
    return normalized, metadata
