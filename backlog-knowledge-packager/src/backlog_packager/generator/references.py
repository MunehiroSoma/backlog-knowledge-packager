"""references.md generation."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from backlog_packager.models import KnowledgeItem

from .common import generated_at, sort_by_updated_desc


def render_references_markdown(
    project_key: str,
    items: Iterable[KnowledgeItem],
    now: datetime | None = None,
) -> str:
    item_list = list(items)
    read_first = _ordered_read_first(item_list)
    templates = sort_by_updated_desc(item for item in item_list if item.category == "template")
    knowledge = sort_by_updated_desc(item for item in item_list if item.category in {"knowledge", "operation"})

    lines = [
        f"# {project_key} reference documents",
        "",
        f"> Generated: {generated_at(now)}",
        "",
        "## Read first",
        "",
    ]
    lines.extend(_numbered_items(read_first))
    lines.extend(["", "## Templates", ""])
    lines.extend(_numbered_items(templates))
    lines.extend(["", "## Past knowledge", ""])
    lines.extend(_numbered_items(knowledge))
    return "\n".join(lines).rstrip() + "\n"


def _ordered_read_first(items: list[KnowledgeItem]) -> list[KnowledgeItem]:
    ordered: list[KnowledgeItem] = []
    for category in ("rule", "setup", "onboarding"):
        ordered.extend(sort_by_updated_desc(item for item in items if item.category == category))
    return ordered


def _numbered_items(items: Iterable[KnowledgeItem]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. {item.title}",
                f"   - Type: {item.source_type}",
                f"   - URL: {item.url}",
                f"   - Updated: {item.updated}",
            ]
        )
    if not lines:
        lines.append("(No matching items)")
    return lines
