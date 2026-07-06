"""setup-checklist.md generation with Phase 2 content-derived tasks."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime

from backlog_packager.models import KnowledgeItem

from .common import generated_at, markdown_link, sort_by_updated_desc

ACTION_PATTERNS = (
    re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(?P<task>.+)$"),
    re.compile(r"^\s*[-*]\s+(?P<task>(?:install|configure|set up|setup|create|copy|run|start|enable|verify)\b.+)$", re.I),
    re.compile(r"^\s*[-*]\s+(?P<task>.+(?:する|してください|確認|設定|作成|配置|起動|実行|インストール).*)$"),
    re.compile(r"^\s*\d+[.)]\s+(?P<task>.+(?:する|してください|確認|設定|作成|配置|起動|実行|インストール).*)$"),
)


def render_setup_checklist_markdown(
    project_key: str,
    items: Iterable[KnowledgeItem],
    now: datetime | None = None,
) -> str:
    item_list = list(items)
    lines = [
        f"# {project_key} environment-setup checklist",
        "",
        f"> Generated: {generated_at(now)}",
        "",
        "## 1. Check conventions",
        "",
    ]
    lines.extend(_linked_tasks((item for item in item_list if item.category == "rule"), "Read"))
    lines.extend(_content_derived_tasks((item for item in item_list if item.category == "rule"), fallback=False))
    lines.extend(["", "## 2. Place templates", ""])
    lines.extend(_linked_tasks((item for item in item_list if item.category == "template"), "Fetch"))
    lines.extend(["", "## 3. Project-specific setup tasks", ""])
    lines.extend(_content_derived_tasks(item for item in item_list if item.category in {"setup", "operation"}))
    lines.extend(["", "## 4. Reference URLs", "", "- [ ] Review `references.md` for source documents and related links."])
    return "\n".join(lines).rstrip() + "\n"


def _linked_tasks(items: Iterable[KnowledgeItem], verb: str) -> list[str]:
    lines = [f"- [ ] {verb} {_source_context(item)}" for item in sort_by_updated_desc(items)]
    return lines or ["- [ ] No matching source-backed items were found."]


def _content_derived_tasks(items: Iterable[KnowledgeItem], fallback: bool = True) -> list[str]:
    lines: list[str] = []
    for item in sort_by_updated_desc(items):
        tasks = extract_checklist_tasks(item.content)
        if not tasks:
            if not fallback:
                continue
            lines.append(f"- [ ] Review {_source_context(item)}")
            continue
        for task in tasks:
            lines.append(f"- [ ] {task} - {_source_context(item)}")
    if lines:
        return lines
    return ["- [ ] No setup or operation documents were found."] if fallback else []


def extract_checklist_tasks(content: str, limit: int = 8) -> list[str]:
    tasks: list[str] = []
    seen: set[str] = set()
    for line in content.splitlines():
        task = _extract_task(line)
        if not task:
            continue
        task = _clean_task(task)
        key = task.casefold()
        if key in seen:
            continue
        seen.add(key)
        tasks.append(task)
        if len(tasks) >= limit:
            break
    return tasks


def _extract_task(line: str) -> str | None:
    for pattern in ACTION_PATTERNS:
        match = pattern.match(line)
        if match:
            return match.group("task")
    return None


def _clean_task(task: str) -> str:
    task = re.sub(r"\s+", " ", task.strip())
    return task.rstrip("。.")


def _source_context(item: KnowledgeItem) -> str:
    return f"{markdown_link(item)} (updated: {item.updated})"
