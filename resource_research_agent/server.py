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
from .contact_lookup import apply_contact_lookup_results, build_contact_lookup_request
from .duplicates import DuplicateIndex
from .importer import PackageImportError, ResourcePackageImporter
from .manual_discovery import build_manual_discovery_assignment
from .manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
    leave_pending_manual_identities_unresolved,
    manual_consolidation_view,
    record_manual_identity_decision,
)
from .playbooks import PLAYBOOKS
from .review_export import build_optimization_review_copy, build_review_copy
from .research import ResearchCoordinator
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
        self.research = ResearchCoordinator(store)
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
                    "agent": self.server.research.agent_status(),
                    "access": self._access_context(),
                })
            elif parsed.path == "/api/agent/status":
                self._json(self.server.research.agent_status())
            elif parsed.path == "/api/agent/settings":
                self._json({"settings": self.server.research.agent_status()["settings"]})
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
            elif parsed.path == "/api/seeds":
                query = parse_qs(parsed.query)
                import_id = int(query["importId"][0]) if query.get("importId") else None
                category_id = query.get("categoryId", [None])[0]
                self._json({"seeds": self.server.store.list_seeds(import_id, category_id)})
            elif parsed.path == "/api/seed-asset":
                query = parse_qs(parsed.query)
                if not all(query.get(key) for key in ("importId", "resourceId", "path")):
                    raise ValueError("importId, resourceId, and path are required")
                asset = self.server.store.seed_asset(
                    int(query["importId"][0]), query["resourceId"][0], query["path"][0]
                )
                if not asset:
                    self._error(HTTPStatus.NOT_FOUND, "Attachment is not available; re-import the source package")
                else:
                    self._binary(asset["content"], asset["mediaType"], asset["name"])
            elif parsed.path == "/api/discoveries":
                self._json({
                    "discoveries": [
                        self._with_match_details(discovery)
                        for discovery in self.server.store.list_discoveries()
                    ]
                })
            elif parsed.path == "/api/research-runs":
                self._json({"runs": self.server.store.list_runs()})
            elif (run_id := self._path_id(
                parsed.path, "/api/manual-discovery-runs", "contributions"
            )) is not None:
                run = self.server.store.get_run(run_id)
                if not run or run["runKind"] != "manual-discovery":
                    self._error(HTTPStatus.NOT_FOUND, "Manual discovery run not found")
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
            elif (run_id := self._path_id(
                parsed.path, "/api/optimization-runs", "review-copy"
            )) is not None:
                review_copy = build_optimization_review_copy(
                    self.server.store,
                    run_id,
                    template_path=self.server.web_dir / "review-copy.html",
                )
                self._download(
                    review_copy.html,
                    "text/html; charset=utf-8",
                    review_copy.filename,
                )
            elif (run_id := self._path_id(parsed.path, "/api/research-runs")) is not None:
                run = self.server.store.get_run(run_id)
                if run:
                    self._json(run)
                else:
                    self._error(HTTPStatus.NOT_FOUND, "Research run not found")
            elif parsed.path == "/api/lessons":
                self._json({"lessons": self.server.store.list_lessons()})
            elif parsed.path in ("/", "/index.html"):
                self._file(self.server.web_dir / "index.html", "text/html; charset=utf-8")
            elif parsed.path == "/app.css":
                self._file(self.server.web_dir / "app.css", "text/css; charset=utf-8")
            elif parsed.path == "/app.js":
                self._file(self.server.web_dir / "app.js", "text/javascript; charset=utf-8")
            else:
                self._error(HTTPStatus.NOT_FOUND, "Not found")
        except (ValueError, PackageImportError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Unexpected error: {error}")

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/api/import":
                self._import_upload()
            elif parsed.path == "/api/agent/settings":
                payload = self._read_json()
                self.server.store.save_settings(payload.get("settings", payload))
                agent = self.server.research.agent_status()
                self._json({"settings": agent["settings"], "agent": agent})
            elif parsed.path == "/api/research-runs":
                payload = self._read_json()
                assignment = str(payload.get("assignment") or "")
                seed_resource_id = str(payload.get("seedResourceId") or "").strip() or None
                run = self.server.research.start(
                    assignment,
                    seed_resource_id,
                    research_mode=str(payload.get("researchMode") or "package"),
                    target_location=str(payload.get("targetLocation") or "").strip() or None,
                    regional_scope=str(payload.get("regionalScope") or ""),
                    target_category_id=str(payload.get("categoryId") or "housing"),
                )
                self._json(run, HTTPStatus.ACCEPTED)
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
                    ),
                    "context": context,
                })
            elif parsed.path == "/api/manual-discovery-runs":
                payload = self._read_json()
                context = self._manual_discovery_context(payload)
                assignment = str(payload.get("assignment") or "").strip()
                if not assignment:
                    assignment = build_manual_discovery_assignment(
                        category_label=context["categoryLabel"],
                        service_area=context["serviceArea"],
                        office_name=context["officeName"],
                        regional_scope=context["regionalScope"],
                        known_resources=context["knownResources"],
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
                    target_location=(
                        context["serviceArea"]
                        if context["researchMode"] == "standalone-location"
                        else None
                    ),
                    regional_scope=context["regionalScope"],
                    target_category_id=context["categoryId"],
                    target_category_label=context["categoryLabel"],
                )
                self._json(self.server.store.get_run(run_id), HTTPStatus.CREATED)
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
            elif (run_id := self._path_id(parsed.path, "/api/research-runs", "resume")) is not None:
                self._json(self.server.research.resume(run_id), HTTPStatus.ACCEPTED)
            elif (run_id := self._path_id(
                parsed.path, "/api/research-runs", "contact-lookup"
            )) is not None:
                self._json(
                    apply_contact_lookup_results(
                        self.server.store, run_id, self._read_json()
                    )
                )
            elif parsed.path == "/api/duplicate-check":
                payload = self._read_json()
                candidate = payload.get("candidate", payload)
                if not isinstance(candidate, dict):
                    raise ValueError("candidate must be a JSON object")
                self._json({"matches": self.server.duplicate_index.match(candidate)})
            elif parsed.path == "/api/discoveries":
                payload = self._read_json()
                candidate = payload.get("candidate")
                if not isinstance(candidate, dict):
                    raise ValueError("candidate must be a JSON object")
                matches = self.server.duplicate_index.match(candidate, limit=1)
                match = matches[0] if matches else None
                saved = self.server.store.save_discovery(candidate, match, str(payload.get("notes", "")))
                self._json(saved, HTTPStatus.CREATED)
            elif parsed.path == "/api/lessons":
                payload = self._read_json()
                lesson = self.server.store.save_lesson(
                    str(payload.get("text", "")), scope=str(payload.get("scope", "category")),
                    rationale=str(payload.get("rationale", "")), status=str(payload.get("status", "active")),
                    source="human",
                    research_mode=str(payload.get("researchMode") or "package"),
                    target_location=str(payload.get("targetLocation") or "").strip() or None,
                    target_category_id=str(payload.get("categoryId") or "housing"),
                    target_category_label=str(payload.get("categoryLabel") or "Housing"),
                )
                self._json(lesson, HTTPStatus.CREATED)
            elif (lesson_id := self._path_id(parsed.path, "/api/lessons", "status")) is not None:
                payload = self._read_json()
                lesson = self.server.store.update_lesson_status(lesson_id, str(payload.get("status", "")))
                if lesson:
                    self._json(lesson)
                else:
                    self._error(HTTPStatus.NOT_FOUND, "Lesson not found")
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
                "officeName": summary["officeName"],
                "serviceArea": summary["serviceArea"],
            }
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
            }
        service_area = " ".join(str(payload.get("targetLocation") or "").split())
        if not service_area:
            raise ValueError("Enter a research location")
        category_label = " ".join(str(payload.get("categoryLabel") or category_id).split())
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
        }

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

    def _with_match_details(self, discovery: dict[str, Any]) -> dict[str, Any]:
        value = dict(discovery)
        value["matchDetails"] = self.server.duplicate_index.explain_saved_match(discovery)
        return value

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
    print(f"Resource Research Agent is running at http://{host}:{port}")
    if private_url:
        print(f"Private Tailscale address: {private_url}")
    print(f"Research database: {store.path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
