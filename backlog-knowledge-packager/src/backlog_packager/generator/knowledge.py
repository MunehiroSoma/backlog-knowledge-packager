"""knowledge.md / knowledge.json generation."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime

from backlog_packager.models import KnowledgeItem, WarningItem

from .common import CATEGORY_LABELS, CATEGORY_ORDER, generated_at, item_source_line, sort_by_updated_desc


def render_knowledge_markdown(
    project_key: str,
    items: Iterable[KnowledgeItem],
    now: datetime | None = None,
) -> str:
    grouped = {category: [] for category in CATEGORY_ORDER}
    for item in items:
        grouped.setdefault(item.category, []).append(item)

    lines = [
        f"# {project_key} knowledge (auto-generated)",
        "",
        f"> Generated: {generated_at(now)} / by Backlog Knowledge Packager",
        "> Every item carries its source URL. Always check the source for the latest state.",
        "",
    ]

    for category in CATEGORY_ORDER:
        category_items = sort_by_updated_desc(grouped.get(category, []))
        if not category_items:
            continue
        lines.extend([f"## {CATEGORY_LABELS[category]} ({category})", ""])
        for item in category_items:
            lines.extend([f"### {item.title}", item_source_line(item)])
            if item.tags:
                lines.append(f"- Tags: {', '.join(item.tags)}")
            lines.extend(["", item.content.strip() or "(No text content)", ""])

    return "\n".join(lines).rstrip() + "\n"


def render_knowledge_json(
    project_key: str,
    items: Iterable[KnowledgeItem],
    warnings: Iterable[WarningItem] = (),
    now: datetime | None = None,
) -> str:
    payload = {
        "projectKey": project_key,
        "generated": generated_at(now),
        "items": [item.to_dict() for item in items],
        "warnings": [warning.to_dict() for warning in warnings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
