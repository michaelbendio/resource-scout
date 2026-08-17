from __future__ import annotations

import json
import os
import re
import tempfile
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .duplicates import DuplicateIndex
from .importer import PackageImportError, ResourcePackageImporter
from .review_export import build_review_copy
from .research import ResearchCoordinator
from .storage import ResearchStore


MAX_UPLOAD_BYTES = 256 * 1024 * 1024


class ResearchHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], store: ResearchStore, web_dir: Path) -> None:
        super().__init__(address, ResearchHandler)
        self.store = store
        self.duplicate_index = DuplicateIndex(store)
        self.research = ResearchCoordinator(store)
        self.web_dir = web_dir


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
                    "latestImport": self.server.store.import_summary(),
                    "agent": self.server.research.agent_status(),
                })
            elif parsed.path == "/api/agent/status":
                self._json(self.server.research.agent_status())
            elif parsed.path == "/api/agent/settings":
                self._json({"settings": self.server.research.agent_status()["settings"]})
            elif parsed.path == "/api/imports":
                self._json({"imports": self.server.store.list_imports()})
            elif parsed.path == "/api/seeds":
                query = parse_qs(parsed.query)
                import_id = int(query["importId"][0]) if query.get("importId") else None
                self._json({"seeds": self.server.store.list_seeds(import_id)})
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
                settings = self.server.store.save_settings(payload.get("settings", payload))
                self._json({"settings": settings, "agent": self.server.research.agent_status()})
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
                )
                self._json(run, HTTPStatus.ACCEPTED)
            elif (run_id := self._path_id(parsed.path, "/api/research-runs", "resume")) is not None:
                self._json(self.server.research.resume(run_id), HTTPStatus.ACCEPTED)
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
            elif (discovery_id := self._path_id(parsed.path, "/api/discoveries", "review")) is not None:
                payload = self._read_json()
                status = str(payload.get("status", ""))
                feedback = str(payload.get("feedback", "")).strip()
                discovery = self.server.store.review_discovery(discovery_id, status, feedback)
                if not discovery:
                    self._error(HTTPStatus.NOT_FOUND, "Candidate not found")
                    return
                lesson = None
                if payload.get("learn") and feedback:
                    run = self.server.store.get_run(discovery["runId"]) if discovery.get("runId") else None
                    lesson = self.server.store.save_lesson(
                        feedback, scope=str(payload.get("scope", "category")),
                        rationale=f"Human review of {discovery['name']}", source="human-feedback",
                        discovery_id=discovery_id,
                        research_mode=run.get("researchMode", "package") if run else "package",
                        target_location=run.get("targetLocation") if run else None,
                    )
                self._json({"discovery": self._with_match_details(discovery), "lesson": lesson})
            elif (discovery_id := self._path_id(
                parsed.path, "/api/discoveries", "match-assessment"
            )) is not None:
                payload = self._read_json()
                discovery = self.server.store.assess_discovery_match(
                    discovery_id, str(payload.get("assessment", ""))
                )
                if not discovery:
                    self._error(HTTPStatus.NOT_FOUND, "Candidate not found")
                    return
                self._json({"discovery": self._with_match_details(discovery)})
            elif parsed.path == "/api/lessons":
                payload = self._read_json()
                lesson = self.server.store.save_lesson(
                    str(payload.get("text", "")), scope=str(payload.get("scope", "category")),
                    rationale=str(payload.get("rationale", "")), status=str(payload.get("status", "active")),
                    source="human",
                    research_mode=str(payload.get("researchMode") or "package"),
                    target_location=str(payload.get("targetLocation") or "").strip() or None,
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
            package = ResourcePackageImporter("Housing").read(temporary_path)
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


def serve(store_path: str | Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    web_dir = Path(__file__).resolve().parent.parent / "web"
    store = ResearchStore(store_path)
    server = ResearchHTTPServer((host, port), store, web_dir)
    print(f"Resource Research Agent is running at http://{host}:{port}")
    print(f"Research database: {store.path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
