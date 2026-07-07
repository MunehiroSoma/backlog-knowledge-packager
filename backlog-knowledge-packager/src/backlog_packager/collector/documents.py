"""Document collector: list and detail retrieval."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backlog_packager.client import BacklogApiError, ReadOnlyBacklogClient
from backlog_packager.sync import CachedItem, cached_item, filter_updated_items

from . import CollectionResult


def collect_documents(
    client: ReadOnlyBacklogClient,
    project_id: str,
    output_dir: Path | None = None,
    download_attachments: bool = True,
    cache: dict[tuple[str, str], CachedItem] | None = None,
    count: int = 100,
) -> CollectionResult:
    """Collect document pages with offset paging.

    Backlog's document list endpoint already includes plain text, but changed
    items are still detail-fetched so fields added only by the detail endpoint
    are preserved when available.
    """

    try:
        listed = _list_all_documents(client, project_id, count=count)
    except BacklogApiError as exc:
        return CollectionResult(
            metadata={"documents": {"list": [], "details": []}},
            summary={
                "documents": {
                    "listed": 0,
                    "detailFetched": 0,
                    "skippedByCache": 0,
                    "treeFetched": 0,
                    "attachments": 0,
                    "attachmentDownloaded": 0,
                }
            },
            failures=[f"documents skipped: {exc}"],
        )
    tree: Any = None
    tree_fetched = 0
    failures: list[str] = []
    try:
        tree = client.get("/api/v2/documents/tree", params={"projectIdOrKey": project_id})
    except BacklogApiError as exc:
        failures.append(f"document tree skipped: {exc}")
    else:
        tree_fetched = 1
    changed = filter_updated_items("document", listed, cache or {})
    details_by_id: dict[str, dict[str, Any]] = {}
    detail_fetched = 0
    attachments: list[dict[str, Any]] = []
    attachment_downloaded = 0
    for item in changed:
        source_id = str(item.get("id") or "")
        if not source_id:
            continue
        try:
            details_by_id[source_id] = client.get(f"/api/v2/documents/{source_id}")
        except BacklogApiError as exc:
            failures.append(f"document detail skipped: {source_id}: {exc}")
            details_by_id[source_id] = item
        else:
            detail_fetched += 1
        parent = details_by_id.get(source_id, item)
        downloaded = _collect_document_attachments(
            client,
            parent,
            output_dir if download_attachments else None,
            failures,
        )
        attachments.extend(downloaded)
        attachment_downloaded += len([item for item in downloaded if item.get("contentPath")])

    documents = []
    for item in listed:
        source_id = str(item.get("id") or "")
        document = details_by_id.get(source_id, dict(item))
        cached = cached_item("document", source_id, cache or {})
        if cached and cached.content_path and not document.get("contentPath"):
            document["contentPath"] = cached.content_path
        documents.append(document)

    return CollectionResult(
        documents=documents,
        attachments=attachments,
        metadata={"documents": {"list": listed, "details": list(details_by_id.values()), "tree": tree, "attachments": attachments}},
        summary={
            "documents": {
                "listed": len(listed),
                "detailFetched": detail_fetched,
                "skippedByCache": max(len(listed) - len(changed), 0),
                "treeFetched": tree_fetched,
                "attachments": len(attachments),
                "attachmentDownloaded": attachment_downloaded,
            }
        },
        failures=failures,
    )


def _list_all_documents(client: ReadOnlyBacklogClient, project_id: str, count: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = client.get(
            "/api/v2/documents",
            params={"projectId[]": project_id, "offset": offset, "count": count},
        )
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
        for key in ("documents", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _collect_document_attachments(
    client: ReadOnlyBacklogClient,
    document: dict[str, Any],
    output_dir: Path | None,
    failures: list[str],
) -> list[dict[str, Any]]:
    document_id = str(document.get("id") or "")
    if not document_id:
        return []
    raw_attachments = _as_list(document.get("attachments"))
    collected: list[dict[str, Any]] = []
    parent_title = str(document.get("title") or document_id)
    parent_updated = str(document.get("updated") or "")
    parent_url = str(document.get("url") or document.get("webUrl") or "")
    for raw in raw_attachments:
        attachment_id = str(raw.get("id") or "")
        name = str(raw.get("name") or raw.get("filename") or attachment_id or "attachment")
        if not attachment_id:
            continue
        item = dict(raw)
        item.update(
            {
                "sourceType": "attachment",
                "parentType": "document",
                "parentId": document_id,
                "parentTitle": parent_title,
                "parentUrl": parent_url,
                "updated": str(raw.get("updated") or raw.get("created") or parent_updated),
                "name": name,
            }
        )
        if output_dir is not None:
            destination = output_dir / "files" / "attachments" / "documents" / document_id / _safe_filename(name)
            try:
                client.download(f"/api/v2/documents/{document_id}/attachments/{attachment_id}", destination)
            except BacklogApiError as exc:
                failures.append(f"document attachment download skipped: {document_id}/{attachment_id}: {exc}")
            else:
                item["contentPath"] = str(destination.relative_to(output_dir)).replace("\\", "/")
        collected.append(item)
    return collected


def _safe_filename(name: str) -> str:
    safe = name.replace("/", "-").replace("\\", "-").strip()
    return safe or "attachment"
