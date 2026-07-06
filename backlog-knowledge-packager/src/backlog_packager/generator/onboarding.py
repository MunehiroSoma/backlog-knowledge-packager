"""Phase 2 onboarding.md generation."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from backlog_packager.models import KnowledgeItem

from .common import generated_at, item_source_line, sort_by_updated_desc


def render_onboarding_markdown(
    project_key: str,
    items: Iterable[KnowledgeItem],
    now: datetime | None = None,
) -> str:
    item_list = list(items)
    read_order = _reading_order(item_list)
    team_rules = sort_by_updated_desc(item for item in item_list if item.category == "rule")
    past_knowledge = sort_by_updated_desc(item for item in item_list if item.category in {"knowledge", "operation"})

    lines = [
        f"# {project_key} onboarding",
        "",
        f"> Generated: {generated_at(now)}",
        "> Every entry links back to its Backlog source.",
        "",
        "## Reading order",
        "",
    ]
    for index, item in enumerate(read_order, start=1):
        lines.extend([f"{index}. {item.title}", f"   - URL: {item.url}", f"   - Updated: {item.updated}"])
    if not read_order:
        lines.append("(No source-backed onboarding materials were found.)")

    lines.extend(["", "## Team rules", ""])
    lines.extend(_summaries(team_rules))
    lines.extend(["", "## Past knowledge", ""])
    lines.extend(_summaries(past_knowledge))
    return "\n".join(lines).rstrip() + "\n"


def _reading_order(items: list[KnowledgeItem]) -> list[KnowledgeItem]:
    ordered: list[KnowledgeItem] = []
    for category in ("onboarding", "rule", "setup", "operation", "knowledge", "reference"):
        ordered.extend(sort_by_updated_desc(item for item in items if item.category == category))
    return ordered


def _summaries(items: Iterable[KnowledgeItem]) -> list[str]:
    lines: list[str] = []
    for item in items:
        summary = _first_meaningful_line(item.content)
        lines.extend([f"### {item.title}", item_source_line(item), "", summary, ""])
    return lines or ["(No matching items)"]


def _first_meaningful_line(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return "(No summary text)"
