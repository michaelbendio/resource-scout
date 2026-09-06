"""Lossless standard-package snapshots and field-level update reconciliation."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any

from .importer import MAX_ARCHIVE_MEMBERS, MAX_JSON_BYTES, MAX_UNCOMPRESSED_BYTES

EDITABLE_FIELDS = ('description', 'informationText')


class ImprovementError(ValueError):
    pass


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImprovementError(f'{label} must be nonempty text')
    return value.strip()


def read_package(payload: bytes) -> dict:
    """Read bytes without extracting files or rewriting unknown package fields."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED_BYTES:
                raise ImprovementError('Package exceeds archive limits')
            names = [i.filename for i in infos]
            if len(names) != len(set(names)):
                raise ImprovementError('Duplicate ZIP member names')
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
                    raise ImprovementError('Unsafe ZIP member path')
            if 'tso-resources.json' not in names:
                raise ImprovementError('Choose a standard resource package ZIP containing tso-resources.json; an HTML shell is not a package')
            if archive.getinfo('tso-resources.json').file_size > MAX_JSON_BYTES:
                raise ImprovementError('Resource JSON exceeds size limit')
            data = json.loads(archive.read('tso-resources.json').decode('utf-8-sig'))
            if not isinstance(data, dict) or type(data.get('resourcePackageSchemaVersion')) is not int or data['resourcePackageSchemaVersion'] != 3:
                raise ImprovementError('Existing-resource updates require standard package schema 3')
            if type(data.get('packageVersion')) is not int or data['packageVersion'] < 0:
                raise ImprovementError('Package needs a nonnegative integer version')
            for field in ('resources', 'categories', 'forGroups'):
                if not isinstance(data.get(field), list):
                    raise ImprovementError(f'Package needs {field} array')
            for field in ('changes', 'deletions', 'deletionRequests', 'categoryMigrations'):
                if field in data and not isinstance(data[field], list):
                    raise ImprovementError(f'{field} must be an array')
            resources = {}
            assets = {}
            for resource in data['resources']:
                if not isinstance(resource, dict):
                    raise ImprovementError('Resource must be an object')
                rid = nonempty(resource.get('id'), 'Resource ID')
                if rid != resource['id'] or rid in resources:
                    raise ImprovementError('Duplicate or unnormalized resource ID')
                resources[rid] = resource
                for field in EDITABLE_FIELDS:
                    if field in resource and not isinstance(resource[field], str):
                        raise ImprovementError(f'{field} must be text')
                pdfs = resource.get('pdfs', [])
                if not isinstance(pdfs, list):
                    raise ImprovementError('PDF references must be an array')
                for pdf in pdfs:
                    if not isinstance(pdf, dict):
                        raise ImprovementError('Malformed PDF reference')
                    path = nonempty(pdf.get('path'), 'PDF path')
                    if path not in names or not path.lower().endswith('.pdf'):
                        raise ImprovementError(f'Missing PDF asset: {path}')
                    assets[path] = archive.read(path)
            return {'data': data, 'resources': resources, 'assets': assets,
                    'sha256': hashlib.sha256(payload).hexdigest(), 'contentSha256': digest(data),
                    'assetHashes': {p: hashlib.sha256(b).hexdigest() for p, b in assets.items()}}
    except (zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError, RuntimeError) as error:
        raise ImprovementError(f'Invalid resource package: {error}') from error


def resource_blocked(package: dict, rid: str) -> str:
    if rid not in package['resources']:
        return 'This resource is absent from the latest package; it cannot be recreated by an update.'
    for field in ('deletions', 'deletionRequests'):
        if any(isinstance(d, dict) and d.get('kind') == 'resource' and d.get('targetId') == rid
               for d in package['data'].get(field, [])):
            return 'This resource has a deletion record or request in the latest package.'
    return ''


def compare_fields(base: dict, current: dict, proposal: dict) -> dict:
    fields = {}
    for field in EDITABLE_FIELDS:
        old, latest, proposed = base.get(field, ''), current.get(field, ''), proposal[field]
        changed = proposed != old
        fields[field] = {'base': old, 'current': latest, 'proposed': proposed,
                         'changed': changed, 'conflict': changed and latest != old and latest != proposed,
                         'alreadyApplied': changed and latest == proposed}
    return fields


def materialize(base: dict, current: dict, proposal: dict, choices: dict) -> dict:
    """Choices are explicit for both fields; later unrelated fields come from current."""
    if not isinstance(choices, dict) or set(choices) != set(EDITABLE_FIELDS):
        raise ImprovementError('Review must choose current or proposed for both writing fields')
    result = deepcopy(current)
    for field, comparison in compare_fields(base, current, proposal).items():
        choice = choices[field]
        if choice not in ('current', 'proposed'):
            raise ImprovementError('Unknown field review choice')
        if choice == 'proposed' and comparison['changed']:
            result[field] = proposal[field]
    return result


def next_timestamp(records: list[dict]) -> str:
    stamp = datetime.now(timezone.utc)
    for record in records:
        raw = record.get('lastModified')
        if not raw:
            continue
        try:
            previous = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
            if previous.tzinfo is None:
                raise ValueError('No timezone')
        except ValueError as error:
            raise ImprovementError('Latest resource has an invalid lastModified timestamp') from error
        stamp = max(stamp, previous + timedelta(milliseconds=1))
    return stamp.isoformat(timespec='milliseconds')


def write_package(data: dict, assets: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('tso-resources.json', json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode())
        for path, payload in sorted(assets.items()):
            archive.writestr(path, payload)
    return stream.getvalue()
