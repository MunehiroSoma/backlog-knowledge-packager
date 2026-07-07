"""Source-structure index Markdown generation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backlog_packager.models import KnowledgeItem

from .common import generated_at


@dataclass(slots=True)
class _WikiNode:
    children: dict[str, "_WikiNode"] = field(default_factory=dict)
    items: list[KnowledgeItem] = field(default_factory=list)


def render_document_index_markdown(
    project_key: str,
    items: Iterable[KnowledgeItem],
    metadata: Mapping[str, object] | None = None,
    now: datetime | None = None,
) -> str:
    document_items = [item for item in items if item.source_type == "document"]
    by_id = {item.source_id: item for item in document_items}
    lines = [f"# {project_key} document structure", "", f"Generated: {generated_at(now)}", ""]

    documents_metadata = _mapping(metadata.get("documents")) if metadata else {}
    tree = _mapping(documents_metadata.get("tree"))
    active_tree = _mapping(tree.get("activeTree"))
    trash_tree = _mapping(tree.get("trashTree"))

    if active_tree:
        lines.extend(["## Active documents", ""])
        _append_document_tree(lines, active_tree, by_id, depth=0)
    elif document_items:
        lines.extend(["## Documents", ""])
        for item in sorted(document_items, key=lambda source: source.title):
            lines.append(f"- {_item_link(item)}")
    else:
        lines.append("(No documents were collected.)")

    if trash_tree and _node_children(trash_tree):
        lines.extend(["", "## Trash documents", ""])
        _append_document_tree(lines, trash_tree, by_id, depth=0)

    return "\n".join(lines).rstrip() + "\n"


def render_wiki_index_markdown(
    project_key: str,
    items: Iterable[KnowledgeItem],
    now: datetime | None = None,
) -> str:
    wiki_items = [item for item in items if item.source_type == "wiki"]
    root = _WikiNode()
    for item in sorted(wiki_items, key=lambda source: source.title):
        parts = [part for part in item.title.split("/") if part]
        if not parts:
            parts = [item.title]
        node = root
        for part in parts[:-1]:
            node = node.children.setdefault(part, _WikiNode())
        node.children.setdefault(parts[-1], _WikiNode()).items.append(item)

    lines = [f"# {project_key} wiki structure", "", f"Generated: {generated_at(now)}", ""]
    if wiki_items:
        _append_wiki_tree(lines, root, depth=0)
    else:
        lines.append("(No wiki pages were collected.)")
    return "\n".join(lines).rstrip() + "\n"


def _append_document_tree(lines: list[str], node: Mapping[str, object], by_id: dict[str, KnowledgeItem], depth: int) -> None:
    node_id = str(node.get("id") or "")
    title = str(node.get("name") or node_id or "Untitled")
    if node_id in by_id:
        lines.append(f"{_indent(depth)}- {_item_link(by_id[node_id], label=title)}")
    else:
        lines.append(f"{_indent(depth)}- {title}")
    for child in _node_children(node):
        _append_document_tree(lines, child, by_id, depth + 1)


def _append_wiki_tree(lines: list[str], node: _WikiNode, depth: int) -> None:
    for name, child in sorted(node.children.items()):
        if child.items and len(child.items) == 1 and not child.children:
            lines.append(f"{_indent(depth)}- {_item_link(child.items[0], label=name)}")
        else:
            lines.append(f"{_indent(depth)}- {name}")
            for item in child.items:
                lines.append(f"{_indent(depth + 1)}- {_item_link(item, label=item.title)}")
            _append_wiki_tree(lines, child, depth + 1)


def _node_children(node: Mapping[str, object]) -> list[Mapping[str, object]]:
    children = node.get("children")
    if not isinstance(children, list):
        return []
    return [child for child in children if isinstance(child, dict)]


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def _item_link(item: KnowledgeItem, label: str | None = None) -> str:
    title = _escape_link_text(label or item.title)
    return f"[{title}]({item.url}) (updated: {item.updated})"


def _escape_link_text(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]")


def _indent(depth: int) -> str:
    return "  " * depth
