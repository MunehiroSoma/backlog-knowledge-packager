"""Document collector: list and detail retrieval."""

from __future__ import annotations

from typing import Any

from backlog_packager.client import BacklogApiError, ReadOnlyBacklogClient
from backlog_packager.sync import CachedItem, cached_item, filter_updated_items

from . import CollectionResult


def collect_documents(
    client: ReadOnlyBacklogClient,
    project_id: str,
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
            summary={"documents": {"listed": 0, "detailFetched": 0, "skippedByCache": 0}},
            failures=[f"documents skipped: {exc}"],
        )
    changed = filter_updated_items("document", listed, cache or {})
    details_by_id: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    detail_fetched = 0
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
        metadata={"documents": {"list": listed, "details": list(details_by_id.values())}},
        summary={
            "documents": {
                "listed": len(listed),
                "detailFetched": detail_fetched,
                "skippedByCache": max(len(listed) - len(changed), 0),
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
