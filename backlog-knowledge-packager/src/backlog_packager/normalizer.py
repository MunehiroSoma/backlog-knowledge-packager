"""Normalize raw API responses into KnowledgeItem."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backlog_packager.collector import CollectionResult
from backlog_packager.models import KnowledgeItem


def normalize_collection(
    collection: CollectionResult,
    project_key: str,
    base_url: str,
    output_dir: Path,
) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    items.extend(normalize_documents(collection.documents, project_key, base_url, output_dir))
    items.extend(normalize_wikis(collection.wikis, project_key, base_url, output_dir))
    items.extend(normalize_shared_files(collection.shared_files, project_key, base_url))
    items.extend(normalize_attachments(collection.attachments, project_key, base_url))
    return items


def normalize_documents(
    documents: list[dict[str, Any]],
    project_key: str,
    base_url: str,
    output_dir: Path,
) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    for raw in documents:
        source_id = _string(raw.get("id"))
        title = _string(raw.get("title"))
        updated = _string(raw.get("updated"))
        if not source_id or not title or not updated:
            continue
        cached_content_path = _safe_content_path(raw.get("contentPath"))
        content = _content_from_raw_or_cache(raw, output_dir, cached_content_path)
        url = _source_url(raw, f"{base_url.rstrip('/')}/document/{source_id}")
        item = KnowledgeItem(
            id=f"document-{source_id}",
            source_type="document",
            source_id=source_id,
            project_key=project_key,
            title=title,
            url=url,
            created=_string(raw.get("created")) or None,
            created_user=_user_name(raw.get("createdUser")),
            updated=updated,
            updated_user=_user_name(raw.get("updatedUser")),
            content_path=_write_content_file(output_dir, "documents", title, content) if content else cached_content_path,
            content=content,
            tags=_tag_names(raw.get("tags")),
        )
        items.append(item)
    return items


def normalize_wikis(
    wikis: list[dict[str, Any]],
    project_key: str,
    base_url: str,
    output_dir: Path,
) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    for raw in wikis:
        source_id = _string(raw.get("id"))
        title = _string(raw.get("name") or raw.get("title"))
        updated = _string(raw.get("updated"))
        if not source_id or not title or not updated:
            continue
        cached_content_path = _safe_content_path(raw.get("contentPath"))
        content = _content_from_raw_or_cache(raw, output_dir, cached_content_path)
        url = _source_url(raw, f"{base_url.rstrip('/')}/alias/wiki/{source_id}")
        item = KnowledgeItem(
            id=f"wiki-{source_id}",
            source_type="wiki",
            source_id=source_id,
            project_key=project_key,
            title=title,
            url=url,
            created=_string(raw.get("created")) or None,
            created_user=_user_name(raw.get("createdUser")),
            updated=updated,
            updated_user=_user_name(raw.get("updatedUser")),
            content_path=_write_content_file(output_dir, "wikis", title, content) if content else cached_content_path,
            content=content,
            tags=_tag_names(raw.get("tags")),
        )
        items.append(item)
    return items


def normalize_shared_files(
    files: list[dict[str, Any]],
    project_key: str,
    base_url: str,
) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    for raw in files:
        if raw.get("type") == "directory":
            continue
        source_id = _string(raw.get("id"))
        title = _string(raw.get("name"))
        updated = _string(raw.get("updated") or raw.get("created"))
        if not source_id or not title or not updated:
            continue
        content_path = _safe_content_path(raw.get("contentPath"))
        file_path = f"{_string(raw.get('dir')).rstrip('/')}/{title}".replace("//", "/")
        url = _source_url(raw, f"{base_url.rstrip('/')}/file/{project_key}{file_path}")
        items.append(
            KnowledgeItem(
                id=f"sharedFile-{source_id}",
                source_type="sharedFile",
                source_id=source_id,
                project_key=project_key,
                title=title,
                url=url,
                created=_string(raw.get("created")) or None,
                created_user=_user_name(raw.get("createdUser")),
                updated=updated,
                updated_user=_user_name(raw.get("updatedUser")),
                content_path=content_path,
                content="",
            )
        )
    return items


def normalize_attachments(
    attachments: list[dict[str, Any]],
    project_key: str,
    base_url: str,
) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    for raw in attachments:
        source_id = _string(raw.get("id"))
        title = _string(raw.get("name") or raw.get("filename"))
        updated = _string(raw.get("updated") or raw.get("created"))
        parent_type = _string(raw.get("parentType"))
        parent_id = _string(raw.get("parentId"))
        if not source_id or not title or not updated or not parent_type or not parent_id:
            continue
        content_path = _safe_content_path(raw.get("contentPath"))
        parent_url = _string(raw.get("parentUrl"))
        fallback = parent_url or f"{base_url.rstrip('/')}/{parent_type}/{parent_id}"
        url = _source_url(raw, fallback)
        items.append(
            KnowledgeItem(
                id=f"attachment-{parent_type}-{parent_id}-{source_id}",
                source_type="attachment",
                source_id=source_id,
                project_key=project_key,
                title=title,
                url=url,
                created=_string(raw.get("created")) or None,
                created_user=_user_name(raw.get("createdUser")),
                updated=updated,
                updated_user=_user_name(raw.get("updatedUser")),
                content_path=content_path,
                content="",
            )
        )
    return items


def _write_content_file(output_dir: Path, folder: str, title: str, content: str) -> str:
    path = output_dir / "files" / folder / f"{_safe_filename(title)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path.relative_to(output_dir)).replace("\\", "/")


def _content_from_raw_or_cache(raw: dict[str, Any], output_dir: Path, content_path: str | None) -> str:
    content = _string(raw.get("plain") or raw.get("content") or raw.get("text"))
    if content or not content_path:
        return content
    path = Path(content_path)
    if path.is_absolute() or ".." in path.parts:
        return ""
    path = output_dir / path
    try:
        path.resolve().relative_to(output_dir.resolve())
    except ValueError:
        return ""
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def _safe_content_path(value: Any) -> str | None:
    content_path = _string(value)
    if not content_path:
        return None
    path = Path(content_path)
    if path.is_absolute() or ".." in path.parts:
        return None
    return content_path


def _source_url(raw: dict[str, Any], fallback: str) -> str:
    for key in ("url", "webUrl", "htmlUrl", "link"):
        value = _string(raw.get(key))
        if value:
            return value
    return fallback


def _user_name(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    return _string(value.get("name") or value.get("userId") or value.get("keyword")) or None


def _tag_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for tag in value:
        if isinstance(tag, dict):
            name = _string(tag.get("name"))
            if name:
                names.append(name)
    return names


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_filename(title: str) -> str:
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in title.strip())
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "item"
