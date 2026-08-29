from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .autocurator import AutoCuratorError, build_autocurator_seed
from .candidate_package import build_candidate_package
from .storage import ResearchStore


@dataclass(frozen=True)
class AutoCuratorReviewFile:
    filename: str
    content: bytes
    resource_assistant_version: str
    resource_assistant_build: int


def _resource_assistant_release(checkout: Path) -> tuple[str, int]:
    release_path = checkout / "src" / "release.json"
    try:
        release = json.loads(release_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AutoCuratorError(
            f"Resource Assistant release metadata was not found in {checkout}"
        ) from error
    except json.JSONDecodeError as error:
        raise AutoCuratorError("Resource Assistant release metadata is invalid") from error
    version = str(release.get("version") or "").strip()
    try:
        build = int(release.get("build"))
    except (TypeError, ValueError) as error:
        raise AutoCuratorError("Resource Assistant build number is invalid") from error
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or build < 1:
        raise AutoCuratorError("Resource Assistant needs a version and positive build number")
    return version, build


def build_autocurator_review_file(
    store: ResearchStore,
    job_id: int,
    resource_assistant_checkout: str | Path,
) -> AutoCuratorReviewFile:
    checkout = Path(resource_assistant_checkout).expanduser().resolve()
    helper = checkout / "make-autocurator"
    if not helper.is_file():
        raise AutoCuratorError(
            f"Resource Assistant make-autocurator was not found in {checkout}"
        )
    version, build = _resource_assistant_release(checkout)
    job = store.get_autocurator_job(job_id)
    if not job:
        raise AutoCuratorError("AutoCurator job not found")
    seed = build_autocurator_seed(store, job_id)
    candidate_package = build_candidate_package(store, job["importId"])
    location_token = "".join(
        character for character in job["locationName"] if character.isalnum()
    )
    if not location_token:
        raise AutoCuratorError("AutoCurator location has no usable filename characters")
    filename = f"auto{location_token}.html"

    with tempfile.TemporaryDirectory(prefix="resource-scout-autocurator-") as directory:
        temporary = Path(directory)
        candidates_path = temporary / candidate_package.filename
        seed_path = temporary / "autocurator-seed.json"
        output_path = temporary / filename
        candidates_path.write_bytes(candidate_package.content)
        seed_path.write_text(
            json.dumps(seed, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(helper),
                str(candidates_path),
                "--seed",
                str(seed_path),
                "--output",
                str(output_path),
            ],
            cwd=checkout,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise AutoCuratorError(
                "Resource Assistant could not build the AutoCurator review file"
                + (f": {detail}" if detail else "")
            )
        try:
            content = output_path.read_bytes()
        except FileNotFoundError as error:
            raise AutoCuratorError(
                "Resource Assistant reported success without creating the review file"
            ) from error

    expected_meta = (
        '<meta name="autocurator-location-name" content="'
        + html.escape(job["locationName"], quote=True)
        + '">'
    ).encode("utf-8")
    if expected_meta not in content:
        raise AutoCuratorError(
            "Generated review file does not contain the expected AutoCurator location"
        )
    store.record_autocurator_progress(
        job_id,
        "review-file-built",
        f"Built {filename} with Resource Assistant {version} build {build}.",
        details={
            "filename": filename,
            "resourceAssistantVersion": version,
            "resourceAssistantBuild": build,
            "byteCount": len(content),
        },
    )
    return AutoCuratorReviewFile(
        filename=filename,
        content=content,
        resource_assistant_version=version,
        resource_assistant_build=build,
    )
