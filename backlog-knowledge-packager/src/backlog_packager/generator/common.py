"""Shared helpers for Markdown generators."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from backlog_packager.models import KnowledgeItem


CATEGORY_LABELS = {
    "rule": "Conventions",
    "setup": "Environment setup",
    "operation": "Operations",
    "knowledge": "Past knowledge",
    "onboarding": "Onboarding",
    "reference": "References",
    "template": "Templates",
    "unclassified": "Unclassified",
}
CATEGORY_ORDER = ["rule", "setup", "operation", "knowledge", "onboarding", "reference", "template", "unclassified"]


def generated_at(now: datetime | None = None) -> str:
    return (now or datetime.now().astimezone()).isoformat(timespec="seconds")


def sort_by_updated_desc(items: Iterable[KnowledgeItem]) -> list[KnowledgeItem]:
    return sorted(items, key=lambda item: item.updated or "", reverse=True)


def item_source_line(item: KnowledgeItem) -> str:
    user = f" / by {item.updated_user}" if item.updated_user else ""
    return f"- Source: {item.url} (last updated: {item.updated}{user})"


def markdown_link(item: KnowledgeItem) -> str:
    return f"[{item.title}]({item.url})"
