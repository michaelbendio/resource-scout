from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


PLAYBOOK_LIBRARY_DIR = Path(__file__).with_name("playbook_library")
DEFAULT_SERVICE_AREA = "Utah County"
PLAYBOOK_LIBRARY_VERSION = "chat-discovery-v1"


@dataclass(frozen=True)
class CategoryPlaybook:
    category_id: str
    label: str
    default_assignment: str
    scope: tuple[str, ...]
    exclusions: tuple[str, ...]
    aliases: tuple[str, ...]
    library_version: str
    source: str


def normalize_supported_category(category_id: str) -> str | None:
    wanted = str(category_id or "").strip().casefold()
    return wanted or None


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read discovery guidance {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Discovery guidance {path.name} must contain one JSON object")
    return value


def _text(value: Any, field: str, path: Path) -> str:
    result = str(value or "").strip()
    if not result:
        raise RuntimeError(f"{path.name}: {field} must not be blank")
    return result


def _text_list(value: Any, field: str, path: Path, *, required: bool = True) -> tuple[str, ...]:
    if value is None and not required:
        return ()
    if not isinstance(value, list) or (required and not value):
        qualifier = "a non-empty" if required else "a"
        raise RuntimeError(f"{path.name}: {field} must be {qualifier} JSON array")
    result = tuple(_text(item, field, path) for item in value)
    if len(set(result)) != len(result):
        raise RuntimeError(f"{path.name}: {field} contains a duplicate entry")
    return result


def _load_library() -> tuple[dict[str, CategoryPlaybook], dict[str, str]]:
    playbooks: dict[str, CategoryPlaybook] = {}
    aliases: dict[str, str] = {}
    for path in sorted(PLAYBOOK_LIBRARY_DIR.glob("*.json")):
        value = _read_object(path)
        category_id = _text(value.get("categoryId"), "categoryId", path)
        label = _text(value.get("label"), "label", path)
        normalized_id = normalize_supported_category(category_id)
        if path.stem != category_id:
            raise RuntimeError(f"{path.name}: filename must match categoryId ({category_id}.json)")
        if not normalized_id or normalized_id in playbooks:
            raise RuntimeError(f"{path.name}: categoryId must be unique")
        assignment_template = _text(value.get("assignment"), "assignment", path)
        if assignment_template.count("{") != assignment_template.count("{service_area}"):
            raise RuntimeError(
                f"{path.name}: assignment may use only the {{service_area}} placeholder"
            )
        raw_aliases = _text_list(value.get("aliases", []), "aliases", path, required=False)
        playbook = CategoryPlaybook(
            category_id=category_id,
            label=label,
            default_assignment=assignment_template.format(service_area=DEFAULT_SERVICE_AREA),
            scope=_text_list(value.get("include"), "include", path),
            exclusions=_text_list(value.get("exclude"), "exclude", path),
            aliases=raw_aliases,
            library_version=PLAYBOOK_LIBRARY_VERSION,
            source=path.name,
        )
        playbooks[normalized_id] = playbook
        for alias in (category_id, label, *raw_aliases):
            normalized_alias = normalize_supported_category(alias)
            if normalized_alias:
                owner = aliases.setdefault(normalized_alias, normalized_id)
                if owner != normalized_id:
                    raise RuntimeError(f"{path.name}: alias {alias!r} is already in use")
    if not playbooks:
        raise RuntimeError("The discovery-guidance library contains no category files")
    return playbooks, aliases


PLAYBOOKS, PLAYBOOK_ALIASES = _load_library()


def _generic_playbook(category_id: str, category_label: str) -> CategoryPlaybook:
    label = str(category_label or category_id).strip() or "Resource"
    subject = label.casefold()
    return CategoryPlaybook(
        category_id=str(category_id).strip() or subject,
        label=label,
        default_assignment=(
            f"Discover credible {subject} resource leads for people in {DEFAULT_SERVICE_AREA}. "
            "Prioritize distinct providers, named programs, and practical ways to begin receiving help."
        ),
        scope=(
            f"Direct and practical {subject} help",
            f"Public, nonprofit, and credible private {subject} programs",
            "Programs that credibly serve the selected area",
        ),
        exclusions=(
            "Directories with no specific useful provider or program behind the listing",
            "Organizations with no credible indication that the relevant service is available",
            "Ordinary commercial options that do not materially improve access for people facing hardship",
        ),
        aliases=(),
        library_version=PLAYBOOK_LIBRARY_VERSION,
        source="generated fallback",
    )


def playbook_for(
    category_id: str,
    category_label: str | None = None,
    service_area: str | None = None,
) -> CategoryPlaybook:
    normalized = normalize_supported_category(category_id)
    if not normalized:
        raise ValueError("A discovery category is required")
    label_key = normalize_supported_category(category_label or "")
    owner = PLAYBOOK_ALIASES.get(normalized) or PLAYBOOK_ALIASES.get(label_key or "")
    playbook = PLAYBOOKS[owner] if owner else _generic_playbook(category_id, category_label or category_id)
    wanted_area = str(service_area or DEFAULT_SERVICE_AREA).strip() or DEFAULT_SERVICE_AREA
    if wanted_area == DEFAULT_SERVICE_AREA:
        return playbook
    return replace(
        playbook,
        default_assignment=playbook.default_assignment.replace(DEFAULT_SERVICE_AREA, wanted_area),
    )
