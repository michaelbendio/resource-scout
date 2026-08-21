from __future__ import annotations

import json
import sys
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


def _normalized_url(value: Any) -> tuple[str, str] | None:
    text = str(value or "").strip()
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    scheme = parsed.scheme.casefold()
    hostname = parsed.hostname.casefold()
    rendered_host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        rendered_host = f"{rendered_host}:{port}"
    path = parsed.path or "/"
    normalized = urlunsplit((scheme, rendered_host, path, parsed.query, ""))
    dedupe_key = normalized[:-1] if path == "/" and not parsed.query else normalized
    return normalized, dedupe_key


def normalize_results(rows: Iterable[Any], max_results: int) -> dict[str, Any]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    dropped = False
    for row in rows:
        if not isinstance(row, dict):
            dropped = True
            continue
        normalized = _normalized_url(row.get("href") or row.get("url"))
        if normalized is None:
            dropped = True
            continue
        url, dedupe_key = normalized
        if dedupe_key in seen:
            dropped = True
            continue
        if len(sources) >= max_results:
            dropped = True
            continue
        seen.add(dedupe_key)
        source = {"url": url}
        title = str(row.get("title") or "").strip()
        snippet = str(row.get("body") or row.get("snippet") or "").strip()
        published_at = str(row.get("date") or row.get("publishedAt") or "").strip()
        if title:
            source["title"] = title
        if snippet:
            source["snippet"] = snippet
        if published_at:
            source["publishedAt"] = published_at
        sources.append(source)
    return {"sources": sources, "truncated": dropped}


def main() -> int:
    try:
        request = json.load(sys.stdin)
        query = str(request.get("query") or "").strip()
        max_results = max(1, min(int(request.get("maxResults") or 8), 20))
        if not query:
            raise ValueError("query is empty")
        from ddgs import DDGS

        rows = DDGS(timeout=30).text(query, max_results=max_results * 2)
        json.dump(normalize_results(rows, max_results), sys.stdout, ensure_ascii=False)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
