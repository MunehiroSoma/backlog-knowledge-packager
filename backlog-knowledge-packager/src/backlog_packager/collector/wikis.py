"""Wiki collector: list and detail retrieval."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backlog_packager.client import BacklogApiError, ReadOnlyBacklogClient
from backlog_packager.sync import CachedItem, cached_item, filter_updated_items

from . import CollectionResult


def collect_wikis(
    client: ReadOnlyBacklogClient,
    project_key: str,
    output_dir: Path | None = None,
    download_attachments: bool = True,
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
    attachments: list[dict[str, Any]] = []
    attachment_downloaded = 0
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
        parent = details_by_id.get(source_id, item)
        downloaded = _collect_wiki_attachments(
            client,
            parent,
            output_dir if download_attachments else None,
            failures,
        )
        attachments.extend(downloaded)
        attachment_downloaded += len([item for item in downloaded if item.get("contentPath")])

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
        attachments=attachments,
        metadata={"wiki": {"list": listed, "details": list(details_by_id.values()), "attachments": attachments}},
        summary={
            "wiki": {
                "listed": len(listed),
                "detailFetched": detail_fetched,
                "skippedByCache": max(len(listed) - len(changed), 0),
                "attachments": len(attachments),
                "attachmentDownloaded": attachment_downloaded,
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


def _collect_wiki_attachments(
    client: ReadOnlyBacklogClient,
    wiki: dict[str, Any],
    output_dir: Path | None,
    failures: list[str],
) -> list[dict[str, Any]]:
    wiki_id = str(wiki.get("id") or "")
    if not wiki_id:
        return []
    try:
        raw_attachments = _as_list(client.get(f"/api/v2/wikis/{wiki_id}/attachments"))
    except BacklogApiError as exc:
        failures.append(f"wiki attachments skipped: {wiki_id}: {exc}")
        return []
    collected: list[dict[str, Any]] = []
    parent_title = str(wiki.get("name") or wiki.get("title") or wiki_id)
    parent_updated = str(wiki.get("updated") or "")
    parent_url = str(wiki.get("url") or wiki.get("webUrl") or "")
    for raw in raw_attachments:
        attachment_id = str(raw.get("id") or "")
        name = str(raw.get("name") or raw.get("filename") or attachment_id or "attachment")
        if not attachment_id:
            continue
        item = dict(raw)
        item.update(
            {
                "sourceType": "attachment",
                "parentType": "wiki",
                "parentId": wiki_id,
                "parentTitle": parent_title,
                "parentUrl": parent_url,
                "updated": str(raw.get("updated") or raw.get("created") or parent_updated),
                "name": name,
            }
        )
        if output_dir is not None:
            destination = output_dir / "files" / "attachments" / "wikis" / wiki_id / _safe_filename(name)
            try:
                client.download(f"/api/v2/wikis/{wiki_id}/attachments/{attachment_id}", destination)
            except BacklogApiError as exc:
                failures.append(f"wiki attachment download skipped: {wiki_id}/{attachment_id}: {exc}")
            else:
                item["contentPath"] = str(destination.relative_to(output_dir)).replace("\\", "/")
        collected.append(item)
    return collected


def _safe_filename(name: str) -> str:
    safe = name.replace("/", "-").replace("\\", "-").strip()
    return safe or "attachment"
