from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import urlsplit, urlunsplit



MAX_ARCHIVE_MEMBERS = 10_000
MAX_JSON_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024

RESOURCE_KEYS = ("resources", "resourceEntries", "entries", "records", "items")
CATEGORY_KEYS = ("categories", "categoryDefinitions", "taxonomy", "needs")
RESOURCE_CATEGORY_KEYS = ("categories", "categoryIds", "category_ids", "category", "needs")
NAME_KEYS = ("name", "title", "resourceName", "displayName")
ALIAS_KEYS = ("alias", "aliases", "aka", "alsoKnownAs", "formerNames", "alternateNames")
WEBSITE_KEYS = ("website", "websites", "url", "urls", "homepage", "site")
ADDRESS_KEYS = ("address", "addresses", "location", "locations", "streetAddress")
RELATION_KEYS = (
    "organization",
    "organizationName",
    "parentOrganization",
    "provider",
    "providerName",
    "agency",
    "operator",
    "program",
    "programs",
    "service",
    "services",
)
ATTACHMENT_KEYS = ("pdf", "pdfs", "document", "documents", "attachment", "attachments")


class PackageImportError(ValueError):
    """Raised when a ZIP is safe to read but is not a recognizable resource package."""


def _normalized_label(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _string_values(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        value = value.strip()
        if value:
            yield value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield str(value)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)
    elif isinstance(value, dict):
        for key in ("name", "label", "title", "value", "url", "address", "id"):
            if key in value:
                yield from _string_values(value[key])
                break


def _first_string(record: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        for value in _string_values(record.get(key)):
            return value
    return ""


def _category_id(category: Any) -> str:
    if isinstance(category, dict):
        return _first_string(category, ("id", "key", "slug", "value", "name", "label"))
    return next(_string_values(category), "")


def _category_label(category: Any) -> str:
    if isinstance(category, dict):
        return _first_string(category, ("label", "name", "title", "id", "key", "slug"))
    return next(_string_values(category), "")


def resource_category_ids(record: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in RESOURCE_CATEGORY_KEYS:
        if key not in record:
            continue
        raw = record[key]
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            category = _category_id(item)
            if category and category not in values:
                values.append(category)
    return values


def resource_name(record: dict[str, Any]) -> str:
    return _first_string(record, NAME_KEYS)


def resource_id(record: dict[str, Any]) -> str:
    explicit = _first_string(record, ("id", "resourceId", "resource_id", "key", "slug"))
    if explicit:
        return explicit
    stable = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "generated-" + hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20]


def resource_attachments(record: dict[str, Any]) -> list[dict[str, str]]:
    """Return referenced package assets without changing the source record."""
    attachments: list[dict[str, str]] = []
    seen: set[str] = set()
    for key in ATTACHMENT_KEYS:
        if key not in record:
            continue
        raw = record[key]
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            if isinstance(item, str):
                asset_path = item.strip()
                name = Path(asset_path).name
            elif isinstance(item, dict):
                asset_path = _first_string(item, ("path", "file", "url", "href"))
                name = _first_string(item, ("name", "title", "label")) or Path(asset_path).name
            else:
                continue
            if not asset_path or asset_path in seen:
                continue
            seen.add(asset_path)
            attachments.append({"name": name or Path(asset_path).name, "path": asset_path})
    return attachments


def _walk_collections(value: Any, path: tuple[str, ...] = (), depth: int = 0) -> Iterator[tuple[tuple[str, ...], list[Any]]]:
    if depth > 4:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, list):
                yield path + (str(key),), child
            elif isinstance(child, dict):
                yield from _walk_collections(child, path + (str(key),), depth + 1)


def _resource_collection_score(path: tuple[str, ...], values: list[Any]) -> float:
    if not values or not all(isinstance(item, dict) for item in values):
        return -1
    key = path[-1] if path else ""
    sample = values[: min(len(values), 50)]
    name_ratio = sum(bool(resource_name(item)) for item in sample) / len(sample)
    id_ratio = sum(bool(_first_string(item, ("id", "resourceId", "key", "slug"))) for item in sample) / len(sample)
    category_ratio = sum(bool(resource_category_ids(item)) for item in sample) / len(sample)
    contact_ratio = sum(any(field in item for field in ("website", "url", "phone", "address", "description", "informationText")) for item in sample) / len(sample)
    preferred = 6 if key in RESOURCE_KEYS else 0
    category_penalty = 8 if key in CATEGORY_KEYS else 0
    return preferred + 4 * name_ratio + 2 * id_ratio + 3 * category_ratio + contact_ratio + min(len(values), 1_000) / 1_000 - category_penalty


def _category_collection_score(path: tuple[str, ...], values: list[Any]) -> float:
    if not values:
        return -1
    key = path[-1] if path else ""
    sample = values[: min(len(values), 50)]
    valid = sum(bool(_category_id(item) and _category_label(item)) for item in sample) / len(sample)
    resource_like = sum(isinstance(item, dict) and bool(resource_name(item)) and bool(resource_category_ids(item)) for item in sample) / len(sample)
    preferred = 6 if key in CATEGORY_KEYS else 0
    return preferred + 4 * valid - 8 * resource_like


def _path_text(path: tuple[str, ...]) -> str:
    return ".".join(path) if path else "$"


@dataclass(frozen=True)
class SchemaDiscovery:
    json_member: str
    resource_path: tuple[str, ...]
    category_path: tuple[str, ...] | None
    schema_version: Any
    package_version: Any

    def as_dict(self) -> dict[str, Any]:
        return {
            "jsonMember": self.json_member,
            "resourcePath": _path_text(self.resource_path),
            "categoryPath": _path_text(self.category_path) if self.category_path else None,
            "schemaVersion": self.schema_version,
            "packageVersion": self.package_version,
        }


@dataclass
class ImportedPackage:
    source_path: Path
    source_name: str
    sha256: str
    schema: SchemaDiscovery
    target_category_id: str
    target_category_label: str
    categories: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    target_resources: list[dict[str, Any]]
    manifest: list[dict[str, Any]]
    root_metadata: dict[str, Any] = field(default_factory=dict)
    for_groups: list[Any] = field(default_factory=list)
    seed_assets: dict[str, bytes] = field(default_factory=dict, repr=False)

    @property
    def target_assets(self) -> dict[str, bytes]:
        """Compatibility name retained for older callers and tests."""
        return self.seed_assets

    @property
    def multicategory_target_count(self) -> int:
        return sum(len(resource_category_ids(item)) > 1 for item in self.target_resources)

    def summary(self) -> dict[str, Any]:
        return {
            "sourceName": self.source_name,
            "sourceSha256": self.sha256,
            "schema": self.schema.as_dict(),
            "category": {"id": self.target_category_id, "label": self.target_category_label},
            "categoryCount": len(self.categories),
            "forGroups": self.for_groups,
            "resourceCount": len(self.resources),
            "targetResourceCount": len(self.target_resources),
            "multiCategoryTargetResourceCount": self.multicategory_target_count,
            "targetOnlyResourceCount": len(self.target_resources) - self.multicategory_target_count,
            "targetResources": [
                {
                    "id": resource_id(item),
                    "name": resource_name(item),
                    "categories": resource_category_ids(item),
                }
                for item in self.target_resources
            ],
        }


class ResourcePackageImporter:
    """Read and understand a Resource Assistant ZIP without modifying it."""

    def __init__(self, target_category: str = "Housing") -> None:
        self.target_category = target_category

    def read(self, source: str | Path) -> ImportedPackage:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise PackageImportError(f"Package does not exist: {path}")
        before = self._hash(path)
        try:
            archive = zipfile.ZipFile(path, "r")
        except (zipfile.BadZipFile, OSError) as error:
            raise PackageImportError(f"Not a readable ZIP package: {error}") from error

        with archive:
            infos = archive.infolist()
            self._validate_archive(infos)
            manifest = [
                {"path": info.filename, "bytes": info.file_size, "compressedBytes": info.compress_size, "crc": f"{info.CRC:08x}"}
                for info in infos
                if not info.is_dir()
            ]
            candidates: list[tuple[float, str, dict[str, Any], tuple[str, ...], list[Any]]] = []
            decoded_json: list[tuple[str, Any]] = []
            errors: list[str] = []
            for info in infos:
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                if info.file_size > MAX_JSON_BYTES:
                    errors.append(f"{info.filename} is larger than the JSON safety limit")
                    continue
                try:
                    data = json.loads(archive.read(info).decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    errors.append(f"{info.filename}: {error}")
                    continue
                decoded_json.append((info.filename, data))
                for collection_path, values in _walk_collections(data):
                    score = _resource_collection_score(collection_path, values)
                    if score >= 0 and isinstance(data, dict):
                        candidates.append((score, info.filename, data, collection_path, values))

            if not candidates:
                detail = "; ".join(errors) if errors else "no JSON object contained a resource-like collection"
                raise PackageImportError(f"Could not discover a resource collection: {detail}")
            candidates.sort(key=lambda item: item[0], reverse=True)
            _, member, root, resources_path, resource_values = candidates[0]
            resources = [dict(item) for item in resource_values]
            category_path, raw_categories = self._find_categories(root, resources_path)
            categories = self._normalize_categories(raw_categories, resources)
            target_id, target_label = self._resolve_target(categories)
            target_norm = _normalized_label(target_id)
            target_resources = [
                item
                for item in resources
                if target_norm in {_normalized_label(category) for category in resource_category_ids(item)}
            ]
            members_by_name = {info.filename: info for info in infos if not info.is_dir()}
            seed_resources = resources
            seed_asset_paths = {
                attachment["path"]
                for resource in seed_resources
                for attachment in resource_attachments(resource)
            }
            seed_assets = {
                asset_path: archive.read(members_by_name[asset_path])
                for asset_path in seed_asset_paths
                if asset_path in members_by_name
            }

            schema_version = root.get("resourcePackageSchemaVersion", root.get("schemaVersion"))
            package_version = root.get("packageVersion", root.get("version"))
            metadata = {key: value for key, value in root.items() if not isinstance(value, (list, dict))}
            result = ImportedPackage(
                source_path=path,
                source_name=path.name,
                sha256=before,
                schema=SchemaDiscovery(member, resources_path, category_path, schema_version, package_version),
                target_category_id=target_id,
                target_category_label=target_label,
                categories=categories,
                resources=resources,
                target_resources=target_resources,
                manifest=manifest,
                root_metadata=metadata,
                for_groups=list(root.get("forGroups") or []) if isinstance(root.get("forGroups"), list) else [],
                seed_assets=seed_assets,
            )

        after = self._hash(path)
        if before != after:
            raise RuntimeError("The source ZIP changed while it was being read; no import was saved")
        return result

    def _find_categories(self, root: dict[str, Any], resources_path: tuple[str, ...]) -> tuple[tuple[str, ...] | None, list[Any]]:
        candidates: list[tuple[float, tuple[str, ...], list[Any]]] = []
        for path, values in _walk_collections(root):
            if path == resources_path:
                continue
            score = _category_collection_score(path, values)
            if score >= 0:
                candidates.append((score, path, values))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            _, path, values = candidates[0]
            return path, values
        return None, []

    def _normalize_categories(self, raw: list[Any], resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw:
            category_id = _category_id(item)
            label = _category_label(item)
            if not category_id:
                continue
            normalized = _normalized_label(category_id)
            if normalized in seen:
                continue
            seen.add(normalized)
            result.append({"id": category_id, "label": label or category_id, "raw": item})
        for record in resources:
            for category_id in resource_category_ids(record):
                normalized = _normalized_label(category_id)
                if normalized not in seen:
                    seen.add(normalized)
                    result.append({"id": category_id, "label": category_id, "raw": category_id})
        return result

    def _resolve_target(self, categories: list[dict[str, Any]]) -> tuple[str, str]:
        wanted = _normalized_label(self.target_category)
        exact = [
            item
            for item in categories
            if wanted in {_normalized_label(item["id"]), _normalized_label(item["label"])}
        ]
        if len(exact) == 1:
            return str(exact[0]["id"]), str(exact[0]["label"])
        if len(exact) > 1:
            ids = ", ".join(str(item["id"]) for item in exact)
            raise PackageImportError(f"Category {self.target_category!r} is ambiguous: {ids}")
        available = ", ".join(str(item["label"]) for item in categories[:30]) or "none discovered"
        raise PackageImportError(f"Category {self.target_category!r} was not found. Available categories: {available}")

    def _validate_archive(self, infos: list[zipfile.ZipInfo]) -> None:
        if len(infos) > MAX_ARCHIVE_MEMBERS:
            raise PackageImportError(f"ZIP has too many members ({len(infos)})")
        total = 0
        for info in infos:
            path = Path(info.filename)
            if path.is_absolute() or ".." in path.parts:
                raise PackageImportError(f"Unsafe ZIP member path: {info.filename}")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise PackageImportError("ZIP exceeds the uncompressed-size safety limit")

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


def iter_index_values(record: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield the explicit and conservative inferred identity terms in a full record."""
    name = resource_name(record)
    if name:
        yield "name", name
        parenthetical = re.sub(r"\s*\([^)]{2,}\)\s*", " ", name).strip()
        if parenthetical and parenthetical != name:
            yield "name_variant", parenthetical
        parts = re.split(r"\s+(?:-|–|—)\s+", name, maxsplit=1)
        if len(parts) == 2 and all(len(part.strip()) >= 3 for part in parts):
            yield "organization_name", parts[0].strip()
            yield "program_name", parts[1].strip()
    for key in ALIAS_KEYS:
        for value in _string_values(record.get(key)):
            yield "alias", value
    for key in WEBSITE_KEYS:
        for value in _string_values(record.get(key)):
            for segment in re.split(r"\s*[;,]\s*", value):
                if segment:
                    yield "website", segment
    for key in ADDRESS_KEYS:
        for value in _string_values(record.get(key)):
            yield "address", value
    for key in RELATION_KEYS:
        for value in _string_values(record.get(key)):
            yield f"relationship:{key}", value


def normalize_index_value(term_type: str, value: str) -> str:
    if term_type == "website":
        raw = value.strip()
        if "@" in raw and not re.search(r"[/:]", raw):
            return "email:" + raw.casefold()
        candidate = raw if "://" in raw else "https://" + raw
        try:
            parts = urlsplit(candidate)
        except ValueError:
            return _normalized_label(raw)
        host = (parts.hostname or "").casefold()
        if host.startswith("www."):
            host = host[4:]
        path = re.sub(r"/+", "/", parts.path or "/").rstrip("/") or "/"
        if not host:
            return _normalized_label(raw)
        return urlunsplit(("https", host, path, "", ""))
    normalized = _normalized_label(value)
    if term_type == "address":
        replacements = {
            "street": "st", "avenue": "ave", "boulevard": "blvd", "road": "rd",
            "drive": "dr", "lane": "ln", "north": "n", "south": "s", "east": "e", "west": "w",
        }
        normalized = " ".join(replacements.get(word, word) for word in normalized.split())
    return normalized
