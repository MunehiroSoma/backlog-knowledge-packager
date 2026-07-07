"""Shared-file collector: recursive metadata listing and optional download."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from backlog_packager.client import BacklogApiError, ReadOnlyBacklogClient
from backlog_packager.sync import CachedItem, cached_item, filter_updated_items, should_fetch

from . import CollectionResult


def collect_shared_files(
    client: ReadOnlyBacklogClient,
    project_key: str,
    output_dir: Path,
    cache: dict[tuple[str, str], CachedItem] | None = None,
    count: int = 100,
    download: bool = True,
    root_path: str = "/",
) -> CollectionResult:
    failures: list[str] = []
    files = _list_directory_recursive(client, project_key, root_path, count=count, failures=failures, visited=set())
    item_cache = cache or {}
    changed = filter_updated_items("sharedFile", files, item_cache)
    downloaded = 0
    skipped = 0

    if download:
        for item in files:
            if item.get("type") != "file":
                continue
            source_id = item.get("id")
            if source_id is None:
                continue
            updated = item.get("updated") or item.get("updatedAt")
            cached = cached_item("sharedFile", str(source_id), item_cache)
            if updated is not None and not should_fetch("sharedFile", str(source_id), str(updated), item_cache):
                if cached and cached.content_path:
                    item["contentPath"] = cached.content_path
                skipped += 1
                continue
            if item not in changed:
                continue
            destination = output_dir / "files" / "shared" / _safe_relative_file_path(item)
            try:
                client.download(f"/api/v2/projects/{project_key}/files/{source_id}", destination)
                item["contentPath"] = str(destination.relative_to(output_dir)).replace("\\", "/")
                downloaded += 1
            except BacklogApiError as exc:
                failures.append(f"shared file download skipped: {source_id}: {exc}")
                continue

    file_count = len([item for item in files if item.get("type") == "file"])
    return CollectionResult(
        shared_files=files,
        metadata={"shared-files": files},
        summary={
            "shared-files": {
                "listed": len(files),
                "files": file_count,
                "downloaded": downloaded,
                "skippedByCache": skipped,
            }
        },
        failures=failures,
    )


def _list_directory_recursive(
    client: ReadOnlyBacklogClient,
    project_key: str,
    path: str,
    count: int,
    failures: list[str],
    visited: set[str],
) -> list[dict[str, Any]]:
    normalized_path = _normalize_directory_path(path)
    if normalized_path in visited:
        return []
    visited.add(normalized_path)
    items = _list_directory(client, project_key, normalized_path, count, failures)
    collected = list(items)
    for item in items:
        if item.get("type") == "directory":
            child_path = f"{item.get('dir', '/')}{item.get('name', '')}/"
            collected.extend(_list_directory_recursive(client, project_key, child_path, count, failures, visited))
    return collected


def _list_directory(
    client: ReadOnlyBacklogClient,
    project_key: str,
    path: str,
    count: int,
    failures: list[str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    encoded_path = quote(path.strip("/"), safe="/")
    endpoint = f"/api/v2/projects/{project_key}/files/metadata/{encoded_path}"
    while True:
        try:
            page = client.get(endpoint, params={"offset": offset, "count": count})
        except BacklogApiError as exc:
            failures.append(f"shared file directory skipped: {path}: {exc}")
            return items
        page_items = _as_list(page)
        items.extend(page_items)
        if len(page_items) < count:
            break
        offset += count
    return items


def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("files", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _safe_relative_file_path(item: dict[str, Any]) -> Path:
    directory = str(item.get("dir") or "/").strip("/")
    name = str(item.get("name") or item.get("id") or "file")
    safe_parts = [part for part in directory.split("/") if part not in ("", ".", "..")]
    safe_name = name.replace("/", "-").replace("\\", "-")
    return Path(*safe_parts, safe_name)


def _normalize_directory_path(path: str) -> str:
    parts = [part for part in str(path or "/").replace("\\", "/").split("/") if part not in ("", ".", "..")]
    if not parts:
        return "/"
    return "/" + "/".join(parts) + "/"
