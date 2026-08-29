from __future__ import annotations

import json
import os
import re
import tempfile
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .scout_curation import (
    build_scout_review_seed,
    next_scout_curation_assignment,
    prepare_scout_curation_job,
    save_scout_curation_result,
)
from .scout_review import build_scout_review_file
from .candidate_package import CandidatePackageError, build_candidate_package
from .contact_lookup import apply_contact_lookup_results, build_contact_lookup_request
from .duplicates import DuplicateIndex
from .importer import PackageImportError, ResourcePackageImporter
from .manual_discovery import build_manual_discovery_assignment, parse_manual_contribution
from .manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
    leave_pending_manual_identities_unresolved,
    manual_consolidation_view,
    record_manual_identity_decision,
)
from .reconciliation import reconcile_completed_run
from .playbooks import PLAYBOOKS, playbook_for
from .review_export import build_review_copy
from .storage import ResearchStore


MAX_UPLOAD_BYTES = 256 * 1024 * 1024


class ResearchHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        store: ResearchStore,
        web_dir: Path,
        private_url: str | None = None,
    ) -> None:
        super().__init__(address, ResearchHandler)
        self.store = store
        self.duplicate_index = DuplicateIndex(store)
        self.web_dir = web_dir
        self.private_url = private_url


class ResearchHandler(BaseHTTPRequestHandler):
    server: ResearchHTTPServer

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/api/status":
                self._json({
                    "ok": True,
                    "version": __version__,
                    "latestImport": self.server.store.import_summary(),
                    "playbookCategories": [
                        {
                            "id": playbook.category_id,
                            "label": playbook.label,
                            "types": [],
                            "resourceCount": 0,
                            "multiCategoryResourceCount": 0,
                            "supported": True,
                            "defaultAssignment": playbook.default_assignment,
                        }
                        for playbook in sorted(
                            PLAYBOOKS.values(), key=lambda item: item.label.casefold()
                        )
                    ],
                    "access": self._access_context(),
                })
            elif parsed.path == "/api/imports":
                self._json({"imports": self.server.store.list_imports()})
            elif parsed.path == "/api/categories":
                query = parse_qs(parsed.query)
                import_id = int(query["importId"][0]) if query.get("importId") else None
                effective_import_id = import_id or self.server.store.latest_import_id()
                self._json({
                    "categories": self.server.store.list_import_categories(effective_import_id),
                    "forGroups": (
                        self.server.store.import_taxonomy(effective_import_id)["forGroups"]
                        if effective_import_id else []
                    ),
                })
            elif parsed.path == "/api/discoveries":
                self._json({"discoveries": self._discoveries_with_match_details()})
            elif parsed.path == "/api/research-runs":
                self._json({"runs": self.server.store.list_runs()})
            elif parsed.path == "/api/candidate-package":
                query = parse_qs(parsed.query)
                import_id = int(query["importId"][0]) if query.get("importId") else None
                package = build_candidate_package(self.server.store, import_id)
                self._download(package.content, "application/zip", package.filename)
            elif parsed.path == "/api/scout-curation-jobs":
                query = parse_qs(parsed.query)
                import_id = int(query["importId"][0]) if query.get("importId") else None
                self._json({
                    "jobs": self.server.store.list_scout_curation_jobs(import_id)
                })
            elif (job_id := self._path_id(
                parsed.path, "/api/scout-curation-jobs", "progress"
            )) is not None:
                self._json({
                    "events": self.server.store.list_scout_curation_progress(job_id)
                })
            elif (job_id := self._path_id(
                parsed.path, "/api/scout-curation-jobs", "seed"
            )) is not None:
                self._json(build_scout_review_seed(self.server.store, job_id))
            elif (job_id := self._path_id(
                parsed.path, "/api/scout-curation-jobs", "review-file"
            )) is not None:
                review_file = build_scout_review_file(
                    self.server.store,
                    job_id,
                )
                self._download(
                    review_file.content,
                    "text/html; charset=utf-8",
                    review_file.filename,
                )
            elif (job_id := self._path_id(
                parsed.path, "/api/scout-curation-jobs"
            )) is not None:
                job = self.server.store.get_scout_curation_job(job_id)
                if job:
                    self._json(job)
                else:
                    self._error(HTTPStatus.NOT_FOUND, "Resource Scout curation job not found")
            elif (run_id := self._path_id(
                parsed.path, "/api/manual-discovery-runs", "contributions"
            )) is not None:
                run = self.server.store.get_run(run_id)
                if not run:
                    self._error(HTTPStatus.NOT_FOUND, "Discovery run not found")
                else:
                    self._json({
                        "run": run,
                        "contributions": self.server.store.list_manual_contributions(run_id),
                        "consolidation": manual_consolidation_view(self.server.store, run_id),
                    })
            elif (run_id := self._path_id(
                parsed.path, "/api/research-runs", "contact-lookup"
            )) is not None:
                lookup = build_contact_lookup_request(self.server.store, run_id)
                self._download(
                    lookup.content,
                    "application/json; charset=utf-8",
                    lookup.filename,
                )
            elif (run_id := self._path_id(parsed.path, "/api/research-runs", "review-copy")) is not None:
                review_copy = build_review_copy(
                    self.server.store, run_id, template_path=self.server.web_dir / "review-copy.html"
                )
                self._download(review_copy.html, "text/html; charset=utf-8", review_copy.filename)
            elif (run_id := self._path_id(parsed.path, "/api/research-runs")) is not None:
                run = self.server.store.get_run(run_id)
                if run:
                    self._json(run)
                else:
                    self._error(HTTPStatus.NOT_FOUND, "Research run not found")
            elif parsed.path in ("/", "/index.html"):
                self._file(self.server.web_dir / "index.html", "text/html; charset=utf-8")
            elif parsed.path == "/app.css":
                self._file(self.server.web_dir / "app.css", "text/css; charset=utf-8")
            elif parsed.path == "/app.js":
                self._file(self.server.web_dir / "app.js", "text/javascript; charset=utf-8")
            else:
                self._error(HTTPStatus.NOT_FOUND, "Not found")
        except (ValueError, PackageImportError, CandidatePackageError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Unexpected error: {error}")

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/api/import":
                self._import_upload()
            elif parsed.path == "/api/manual-discovery-assignment":
                payload = self._read_json()
                context = self._manual_discovery_context(payload)
                self._json({
                    "assignment": build_manual_discovery_assignment(
                        category_label=context["categoryLabel"],
                        service_area=context["serviceArea"],
                        office_name=context["officeName"],
                        regional_scope=context["regionalScope"],
                        known_resources=context["knownResources"],
                        include=context["include"],
                        exclude=context["exclude"],
                    ),
                    "context": context,
                })
            elif parsed.path == "/api/manual-discovery-runs":
                self._json(
                    self._create_manual_discovery_run(self._read_json()),
                    HTTPStatus.CREATED,
                )
            elif parsed.path == "/api/scout-curation-jobs":
                payload = self._read_json()
                job = prepare_scout_curation_job(
                    self.server.store,
                    int(payload["importId"]) if payload.get("importId") else None,
                )
                self._json(job, HTTPStatus.CREATED)
            elif (job_id := self._path_id(
                parsed.path, "/api/scout-curation-jobs", "next-assignment"
            )) is not None:
                self._read_json()
                self._json({
                    "assignment": next_scout_curation_assignment(
                        self.server.store, job_id
                    )
                })
            elif (job_id := self._path_id(
                parsed.path, "/api/scout-curation-jobs", "results"
            )) is not None:
                payload = self._read_json()
                result = payload.get("result")
                if not isinstance(result, dict):
                    raise ValueError("Resource Scout curation result must be one JSON object")
                self._json(save_scout_curation_result(
                    self.server.store,
                    job_id,
                    str(payload.get("categoryId") or ""),
                    result,
                ))
            elif (job_id := self._path_id(
                parsed.path, "/api/scout-curation-jobs", "progress"
            )) is not None:
                payload = self._read_json()
                phase = str(payload.get("phase") or "").strip()
                message = str(payload.get("message") or "").strip()
                if not phase or not message:
                    raise ValueError("Resource Scout curation progress needs a phase and message")
                details = payload.get("details") or {}
                if not isinstance(details, dict):
                    raise ValueError("Resource Scout curation progress details must be an object")
                self._json(self.server.store.record_scout_curation_progress(
                    job_id,
                    phase,
                    message,
                    category_id=str(payload.get("categoryId") or "") or None,
                    details=details,
                ), HTTPStatus.CREATED)
            elif parsed.path == "/api/manual-discovery-runs/initial-contribution":
                payload = self._read_json()
                initial = payload.get("initialContribution")
                if not isinstance(initial, dict):
                    raise ValueError("An initial response is required")
                parsed_contribution = parse_manual_contribution(initial.get("rawText"))
                if parsed_contribution["status"] != "parsed":
                    raise ValueError(
                        "Correct the response before starting discovery: "
                        + parsed_contribution["error"]
                    )
                run = self._create_manual_discovery_run(payload)
                try:
                    contribution = self.server.store.save_manual_contribution(
                        run["id"],
                        str(initial.get("sourceLabel") or ""),
                        initial.get("rawText"),
                        filename=str(initial.get("filename") or ""),
                    )
                except Exception:
                    self.server.store.delete_empty_manual_discovery_run(run["id"])
                    raise
                self._json(
                    {
                        "run": self.server.store.get_run(run["id"]),
                        "contribution": contribution,
                    },
                    HTTPStatus.CREATED,
                )
            elif (run_id := self._path_id(
                parsed.path, "/api/manual-discovery-runs", "contributions"
            )) is not None:
                payload = self._read_json()
                contribution = self.server.store.save_manual_contribution(
                    run_id,
                    str(payload.get("sourceLabel") or ""),
                    payload.get("rawText"),
                    filename=str(payload.get("filename") or ""),
                )
                self._json(contribution, HTTPStatus.CREATED)
            elif (run_id := self._path_id(
                parsed.path, "/api/manual-discovery-runs", "finish"
            )) is not None:
                self._read_json()
                self._json(
                    finish_manual_discovery(self.server.store, run_id)
                )
            elif (run_id := self._path_id(
                parsed.path, "/api/manual-discovery-runs", "consolidate"
            )) is not None:
                self._read_json()
                self._json(
                    consolidate_manual_discovery(
                        self.server.store, run_id, self.server.duplicate_index
                    )
                )
            elif (run_id := self._path_id(
                parsed.path, "/api/manual-discovery-runs", "identity-decision"
            )) is not None:
                payload = self._read_json()
                self._json(
                    record_manual_identity_decision(
                        self.server.store,
                        run_id,
                        str(payload.get("leftKey") or ""),
                        str(payload.get("rightKey") or ""),
                        str(payload.get("decision") or ""),
                        self.server.duplicate_index,
                    )
                )
            elif (run_id := self._path_id(
                parsed.path, "/api/manual-discovery-runs", "leave-pending-unresolved"
            )) is not None:
                self._read_json()
                self._json(
                    leave_pending_manual_identities_unresolved(
                        self.server.store, run_id, self.server.duplicate_index
                    )
                )
            elif (run_id := self._path_id(
                parsed.path, "/api/research-runs", "contact-lookup"
            )) is not None:
                self._json(
                    apply_contact_lookup_results(
                        self.server.store, run_id, self._read_json()
                    )
                )
            elif (run_id := self._path_id(
                parsed.path, "/api/research-runs", "reconcile"
            )) is not None:
                payload = self._read_json()
                self._json(
                    reconcile_completed_run(
                        self.server.store,
                        run_id,
                        int(payload["importId"]) if payload.get("importId") else None,
                    )
                )
            else:
                self._error(HTTPStatus.NOT_FOUND, "Not found")
        except (ValueError, PackageImportError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Unexpected error: {error}")

    def do_DELETE(self) -> None:
        parsed = urlsplit(self.path)
        try:
            match = re.fullmatch(
                r"/api/manual-discovery-runs/(\d+)/contributions/(\d+)", parsed.path
            )
            if not match:
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            run_id, contribution_id = (int(value) for value in match.groups())
            if self.server.store.delete_manual_contribution(run_id, contribution_id):
                self._json({"ok": True})
            else:
                self._error(HTTPStatus.NOT_FOUND, "Contribution not found")
        except ValueError as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Unexpected error: {error}")

    def _manual_discovery_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        research_mode = str(payload.get("researchMode") or "package")
        if research_mode not in {"package", "standalone-location"}:
            raise ValueError("Unsupported research context")
        regional_scope = " ".join(str(payload.get("regionalScope") or "").split())
        category_id = str(payload.get("categoryId") or "housing").strip() or "housing"
        if research_mode == "package":
            import_id = int(payload.get("sourceImportId") or self.server.store.latest_import_id() or 0)
            summary = self.server.store.import_summary(import_id)
            if not summary:
                raise ValueError("Connect a resource package before preparing this assignment")
            category = self.server.store.import_category(import_id, category_id)
            if not category:
                raise ValueError("The selected category is not in the connected package")
            service_area = str(summary.get("serviceArea") or summary.get("officeName") or "").strip()
            if not service_area:
                raise ValueError("The connected package does not identify a service area")
            known_resources = [
                {"id": seed["resourceId"], "name": seed["name"]}
                for seed in self.server.store.list_seeds(import_id, category["id"])
            ]
            source_package = {
                "importId": import_id,
                "sourceName": summary["sourceName"],
                "sourceSha256": summary["sourceSha256"],
                "contentSha256": summary["contentSha256"],
                "officeName": summary["officeName"],
                "serviceArea": summary["serviceArea"],
            }
            guidance = playbook_for(category["id"], category["label"], service_area)
            return {
                "researchMode": research_mode,
                "sourceImportId": import_id,
                "sourcePackage": source_package,
                "officeName": str(summary.get("officeName") or ""),
                "serviceArea": service_area,
                "regionalScope": regional_scope,
                "categoryId": str(category["id"]),
                "categoryLabel": str(category["label"]),
                "knownResources": known_resources,
                "include": list(guidance.scope),
                "exclude": list(guidance.exclusions),
            }
        service_area = " ".join(str(payload.get("targetLocation") or "").split())
        if not service_area:
            raise ValueError("Enter a research location")
        category_label = " ".join(str(payload.get("categoryLabel") or category_id).split())
        guidance = playbook_for(category_id, category_label, service_area)
        return {
            "researchMode": research_mode,
            "sourceImportId": None,
            "sourcePackage": None,
            "officeName": "",
            "serviceArea": service_area,
            "regionalScope": regional_scope,
            "categoryId": category_id,
            "categoryLabel": category_label,
            "knownResources": [],
            "include": list(guidance.scope),
            "exclude": list(guidance.exclusions),
        }

    def _create_manual_discovery_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = self._manual_discovery_context(payload)
        assignment = str(payload.get("assignment") or "").strip()
        if not assignment:
            assignment = build_manual_discovery_assignment(
                category_label=context["categoryLabel"],
                service_area=context["serviceArea"],
                office_name=context["officeName"],
                regional_scope=context["regionalScope"],
                known_resources=context["knownResources"],
                include=context["include"],
                exclude=context["exclude"],
            )
        prompt = {
            "assignment": assignment,
            "researchContext": {
                "mode": context["researchMode"],
                "sourcePackage": context["sourcePackage"],
                "serviceArea": context["serviceArea"],
                "regionalScope": context["regionalScope"],
                "knownResources": context["knownResources"],
            },
            "targetCategory": {
                "id": context["categoryId"],
                "label": context["categoryLabel"],
            },
        }
        run_id = self.server.store.create_manual_discovery_run(
            assignment,
            prompt,
            context["sourceImportId"],
            research_mode=context["researchMode"],
            target_location=(
                context["serviceArea"]
                if context["researchMode"] == "standalone-location"
                else None
            ),
            regional_scope=context["regionalScope"],
            target_category_id=context["categoryId"],
            target_category_label=context["categoryLabel"],
        )
        run = self.server.store.get_run(run_id)
        if run is None:  # pragma: no cover - guarded by the insert above
            raise RuntimeError("Created discovery could not be read")
        return run

    def _import_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            raise ValueError("Use multipart/form-data with a package field")
        length = self._content_length()
        body = self.rfile.read(length)
        message = BytesParser(policy=default).parsebytes(
            b"Content-Type: " + content_type.encode("ascii", "replace") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
        )
        part = next((item for item in message.iter_parts() if item.get_param("name", header="content-disposition") == "package"), None)
        if part is None:
            raise ValueError("No package file was uploaded")
        filename = part.get_filename() or "resource-package.zip"
        payload = part.get_payload(decode=True) or b""
        if not payload:
            raise ValueError("The uploaded package is empty")
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(prefix="resource-package-", suffix=".zip", delete=False) as handle:
                handle.write(payload)
                temporary_path = handle.name
            package = ResourcePackageImporter(None).read(temporary_path)
            package.source_name = Path(filename).name
            import_id = self.server.store.save_import(package)
            summary = self.server.store.import_summary(import_id)
            self._json({"ok": True, "import": summary}, HTTPStatus.CREATED)
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _path_id(path: str, prefix: str, suffix: str | None = None) -> int | None:
        ending = f"/{re.escape(suffix)}" if suffix else ""
        match = re.fullmatch(re.escape(prefix) + r"/(\d+)" + ending, path)
        return int(match.group(1)) if match else None

    def _discoveries_with_match_details(self) -> list[dict[str, Any]]:
        discoveries = self.server.store.list_discoveries()
        reconciliations: dict[int, dict[str, Any] | None] = {}
        reconciliation_matches: dict[int, dict[int, dict[str, Any]]] = {}
        result = []
        for discovery in discoveries:
            run_id = int(discovery["runId"])
            if run_id not in reconciliations:
                reconciliation = self.server.store.latest_run_reconciliation(run_id)
                reconciliations[run_id] = reconciliation
                if reconciliation:
                    reconciliation_matches[run_id] = self.server.store.reconciliation_matches(
                        int(reconciliation["id"])
                    )
            reconciliation = reconciliations[run_id]
            stored_match = (
                reconciliation_matches.get(run_id, {}).get(discovery["id"])
                if reconciliation
                else discovery.get("match")
            )
            value = dict(discovery)
            value["matchDetails"] = self.server.duplicate_index.explain_match(
                discovery.get("candidate", {}), stored_match
            )
            result.append(value)
        return result

    def _access_context(self) -> dict[str, Any]:
        requester = None
        if self.server.private_url:
            login = self._decoded_header("Tailscale-User-Login")
            name = self._decoded_header("Tailscale-User-Name")
            if login or name:
                requester = {"login": login, "name": name}
        return {
            "mode": "tailscale" if self.server.private_url else "local",
            "privateUrl": self.server.private_url,
            "requester": requester,
        }

    def _decoded_header(self, name: str) -> str:
        value = self.headers.get(name, "").strip()
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except (LookupError, UnicodeError):
            return value

    def _read_json(self) -> dict[str, Any]:
        length = self._content_length(maximum=5 * 1024 * 1024)
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid JSON: {error}") from error
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object")
        return value

    def _content_length(self, maximum: int = MAX_UPLOAD_BYTES) -> int:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid Content-Length") from error
        if length <= 0:
            raise ValueError("Request body is empty")
        if length > maximum:
            raise ValueError(f"Request body exceeds {maximum // (1024 * 1024)} MB")
        return length

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._error(HTTPStatus.NOT_FOUND, "Not found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _binary(self, data: bytes, content_type: str, filename: str) -> None:
        safe_name = filename.replace("\r", "").replace("\n", "").replace('"', "'")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'inline; filename="{safe_name}"')
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _download(self, data: bytes, content_type: str, filename: str) -> None:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or "research-review.html"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json({"ok": False, "error": message}, status)


def serve(
    store_path: str | Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    private_url: str | None = None,
) -> None:
    web_dir = Path(__file__).resolve().parent.parent / "web"
    store = ResearchStore(store_path, recover_interrupted=True)
    server = ResearchHTTPServer((host, port), store, web_dir, private_url=private_url)
    print(f"Resource Scout is running at http://{host}:{port}")
    if private_url:
        print(f"Private Tailscale address: {private_url}")
    print(f"Research database: {store.path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
