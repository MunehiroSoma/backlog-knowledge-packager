"""Differential-sync helpers for Phase 2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CachedItem:
    source_type: str
    source_id: str
    updated: str
    content_path: str | None = None


def load_cached_items(source_map_path: Path) -> dict[tuple[str, str], CachedItem]:
    """Load previously generated source-map metadata.

    Missing metadata is treated as an empty cache, which makes the first run
    fetch everything.
    """

    if not source_map_path.exists():
        return {}

    try:
        payload = json.loads(source_map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_items = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        return {}
    cache: dict[tuple[str, str], CachedItem] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        source_type = raw_item.get("sourceType") or raw_item.get("source_type")
        source_id = str(raw_item.get("sourceId") or raw_item.get("source_id") or "")
        updated = raw_item.get("updated") or ""
        if not source_type or not source_id or not updated:
            continue
        content_path = _safe_content_path(raw_item.get("contentPath") or raw_item.get("content_path"))
        cache[(source_type, source_id)] = CachedItem(source_type, source_id, updated, content_path or None)
    return cache


def should_fetch(
    source_type: str,
    source_id: str,
    updated: str,
    cache: dict[tuple[str, str], CachedItem],
) -> bool:
    """Return True when an item is new or has a different updated timestamp."""

    cached = cache.get((source_type, str(source_id)))
    return cached is None or cached.updated != updated


def cached_item(
    source_type: str,
    source_id: str,
    cache: dict[tuple[str, str], CachedItem],
) -> CachedItem | None:
    return cache.get((source_type, str(source_id)))


def filter_updated_items(
    source_type: str,
    raw_items: list[dict[str, Any]],
    cache: dict[tuple[str, str], CachedItem],
    id_keys: tuple[str, ...] = ("id", "sourceId"),
    updated_keys: tuple[str, ...] = ("updated", "updatedAt"),
) -> list[dict[str, Any]]:
    """Filter raw list responses down to items requiring detail re-fetch."""

    updated_items: list[dict[str, Any]] = []
    for raw_item in raw_items:
        source_id = _first_present(raw_item, id_keys)
        updated = _first_present(raw_item, updated_keys)
        if source_id is None or updated is None:
            updated_items.append(raw_item)
            continue
        if should_fetch(source_type, str(source_id), str(updated), cache):
            updated_items.append(raw_item)
    return updated_items


def _first_present(raw_item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = raw_item.get(key)
        if value not in (None, ""):
            return value
    return None


def _safe_content_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return value
