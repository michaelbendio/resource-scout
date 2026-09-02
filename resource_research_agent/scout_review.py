from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import __build__, __version__
from .scout_curation import ScoutCurationError, build_scout_review_seed
from .storage import ResearchStore


TEMPLATE_PATH = Path(__file__).resolve().with_name("scout_review_template.html")


@dataclass(frozen=True)
class ScoutReviewFile:
    filename: str
    content: bytes
    scout_version: str
    scout_build: int


def _replace_once(pattern: str, replacement: str, text: str, description: str) -> str:
    updated, count = re.subn(
        pattern,
        lambda _match: replacement,
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    if count != 1:
        raise ScoutCurationError(
            f"Scout review template is missing its {description} placeholder"
        )
    return updated


def _slug(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    if not parts:
        raise ScoutCurationError("Scout review location has no usable name")
    return "-".join(part.lower() for part in parts)


def _replace_meta(document: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    return _replace_once(
        rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\'][^"\']*["\']\s*>',
        f'<meta name="{name}" content="{escaped}">',
        document,
        f"{name} meta tag",
    )


def _build_scout_review_file_from_seed(
    store: ResearchStore,
    job: dict[str, object],
    seed: dict[str, object],
    *,
    taxonomy: dict[str, object] | None = None,
) -> ScoutReviewFile:
    job_id = int(job["id"])
    location_name = str(job["locationName"] or "").strip()
    location_token = "".join(
        character for character in location_name if character.isalnum()
    )
    if not location_token:
        raise ScoutCurationError("Scout review location has no usable filename characters")
    filename = f"auto{location_token}.html"

    try:
        document = TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ScoutCurationError("Resource Scout review template is missing") from error

    curated_category_ids = (
        [str(item["id"]) for item in seed.get("categories") or []]
        if taxonomy
        else [
            str(item["categoryId"])
            for item in job["categories"]
            if item["status"] == "completed"
        ]
    )
    meta_values = {
        "tso-storage-id": f"scout-review-{_slug(location_name)}",
        "tso-office-name": f"Auto{location_token}",
        "tso-sharepoint-package-url": "",
        "tso-commit": "",
        "scout-review-location-name": location_name,
        "scout-review-category-id": "",
        "scout-review-category-label": "",
        "scout-review-curated-category-ids": ",".join(curated_category_ids),
        "scout-review-candidate-package-sha256": job["candidatePackageSha256"],
        "scout-review-taxonomy-study-id": (
            str(taxonomy["studyId"]) if taxonomy else ""
        ),
        "scout-review-taxonomy-corpus-sha256": (
            str(taxonomy["basedOnCorpusSha256"]) if taxonomy else ""
        ),
        "scout-review-taxonomy-category-proposal-sha256": (
            str(taxonomy["categoryProposalSha256"]) if taxonomy else ""
        ),
        "scout-review-taxonomy-type-manifest-sha256": (
            str(taxonomy["typeDesignManifestSha256"]) if taxonomy else ""
        ),
        "scout-review-taxonomy-group-proposal-sha256": (
            str(taxonomy["groupProposalSha256"]) if taxonomy else ""
        ),
        "scout-review-taxonomy-seed-sha256": (
            str(taxonomy["seedSha256"]) if taxonomy else ""
        ),
    }
    for name, value in meta_values.items():
        document = _replace_meta(document, name, str(value))

    title = f"Auto{location_token} TSO Resources"
    document = _replace_once(
        r"<title>.*?</title>",
        f"<title>{html.escape(title)}</title>",
        document,
        "page title",
    )
    seed_json = json.dumps(seed, ensure_ascii=False, indent=2).replace("</", "<\\/")
    artifact_seed = dict(seed)
    artifact_seed.pop("packageCreatedAt", None)
    artifact_seed.pop("lastModified", None)
    artifact_source = json.dumps(
        artifact_seed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    artifact_id = f"scout-review-{hashlib.sha256(artifact_source).hexdigest()[:24]}"
    document = _replace_meta(document, "scout-review-artifact-id", artifact_id)
    document = _replace_once(
        r'<script\s+id=["\']seed-data["\']\s+type=["\']application/json["\']>[\s\S]*?</script>',
        f'<script id="seed-data" type="application/json">\n{seed_json}\n</script>',
        document,
        "seed data",
    )
    release = {
        "version": __version__,
        "build": __build__,
        "date": "2026-09-02",
        "message": "Curate resources and preview missionary handouts",
        "changes": [
            {
                "date": "2026-09-02",
                "version": __version__,
                "message": "Curate resources, package the curated selection, and preview the open resource for printing",
            },
            {
                "date": "2026-09-01",
                "version": "0.47.0",
                "message": "Apply reviewed need Categories, Types, and comprehensive For groups",
            },
            {
                "date": "2026-08-29",
                "version": "0.42.1",
                "message": "Keep review edits and package selections reliable in Safari",
            },
        ],
    }
    release_json = json.dumps(release, ensure_ascii=False, indent=2).replace("</", "<\\/")
    document = _replace_once(
        r'<script\s+id=["\']app-release-data["\']\s+type=["\']application/json["\']>[\s\S]*?</script>',
        f'<script id="app-release-data" type="application/json">\n{release_json}\n</script>',
        document,
        "Scout review release data",
    )
    obsolete_name = "Auto" + "Curator"
    if obsolete_name in document:
        raise ScoutCurationError("Scout review template still contains an obsolete product name")
    content = document.encode("utf-8")
    taxonomy_suffix = (
        f" from taxonomy study {taxonomy['studyId']}" if taxonomy else ""
    )
    store.record_scout_curation_progress(
        job_id,
        "review-file-built",
        f"Built {filename}{taxonomy_suffix} with Resource Scout {__version__} "
        f"build {__build__}.",
        details={
            "filename": filename,
            "scoutVersion": __version__,
            "scoutBuild": __build__,
            "byteCount": len(content),
            **(
                {
                    "taxonomyStudyId": taxonomy["studyId"],
                    "taxonomySeedSha256": taxonomy["seedSha256"],
                }
                if taxonomy else {}
            ),
        },
    )
    return ScoutReviewFile(
        filename=filename,
        content=content,
        scout_version=__version__,
        scout_build=__build__,
    )


def build_scout_review_file(store: ResearchStore, job_id: int) -> ScoutReviewFile:
    job = store.get_scout_curation_job(job_id)
    if not job:
        raise ScoutCurationError("Resource Scout curation job not found")
    taxonomy = store.latest_taxonomy_compilation_for_curation_job(job_id)
    seed = (
        taxonomy["seed"]
        if taxonomy is not None
        else build_scout_review_seed(store, job_id)
    )
    return _build_scout_review_file_from_seed(
        store,
        job,
        seed,
        taxonomy=taxonomy,
    )
