"""Wiki collector: list and detail retrieval."""

from __future__ import annotations

from typing import Any

from backlog_packager.client import BacklogApiError, ReadOnlyBacklogClient
from backlog_packager.sync import CachedItem, cached_item, filter_updated_items

from . import CollectionResult


def collect_wikis(
    client: ReadOnlyBacklogClient,
    project_key: str,
    cache: dict[tuple[str, str], CachedItem] | None = None,
) -> CollectionResult:
    """Collect wiki pages, gracefully skipping unavailable wiki support."""

    try:
        listed = _as_list(client.get("/api/v2/wikis", params={"projectIdOrKey": project_key}))
    except BacklogApiError as exc:
        return CollectionResult(
            metadata={"wiki": []},
            summary={"wiki": {"listed": 0, "detailFetched": 0, "skippedByCache": 0}},
            failures=[f"wiki skipped: {exc}"],
        )

    changed = filter_updated_items("wiki", listed, cache or {})
    details_by_id: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    detail_fetched = 0
    for item in changed:
        source_id = str(item.get("id") or "")
        if not source_id:
            continue
        try:
            details_by_id[source_id] = client.get(f"/api/v2/wikis/{source_id}")
        except BacklogApiError as exc:
            failures.append(f"wiki detail skipped: {source_id}: {exc}")
            details_by_id[source_id] = item
        else:
            detail_fetched += 1

    wikis = []
    for item in listed:
        source_id = str(item.get("id") or "")
        wiki = details_by_id.get(source_id, dict(item))
        cached = cached_item("wiki", source_id, cache or {})
        if cached and cached.content_path and not wiki.get("contentPath"):
            wiki["contentPath"] = cached.content_path
        wikis.append(wiki)

    return CollectionResult(
        wikis=wikis,
        metadata={"wiki": {"list": listed, "details": list(details_by_id.values())}},
        summary={
            "wiki": {
                "listed": len(listed),
                "detailFetched": detail_fetched,
                "skippedByCache": max(len(listed) - len(changed), 0),
            }
        },
        failures=failures,
    )


def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("wikis", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []
