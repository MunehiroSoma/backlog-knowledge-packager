"""Local update proposal generation and review-state helpers."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


ReviewStatus = Literal["pending", "approved", "rejected"]
VALID_REVIEW_STATUSES: set[str] = {"pending", "approved", "rejected"}


@dataclass(frozen=True, slots=True)
class SuggestionPaths:
    source_type: str
    source_id: str
    title: str
    proposal_path: Path
    diff_path: Path
    review_path: Path


@dataclass(frozen=True, slots=True)
class ReviewEntry:
    source_type: str
    source_id: str
    title: str
    url: str
    updated: str
    status: str
    proposal_path: str
    diff_path: str
    reviewer: str | None = None
    reviewed_at: str | None = None
    note: str | None = None


class SuggestionError(ValueError):
    """Raised when local suggestion inputs are invalid."""


def generate_suggestions(
    output_dir: Path | str,
    suggestions_dir: Path | str | None = None,
    now: datetime | None = None,
) -> list[SuggestionPaths]:
    """Generate local proposal, diff, and review files from collected outputs."""

    output_path = Path(output_dir)
    suggestion_path = Path(suggestions_dir) if suggestions_dir else output_path / "suggestions"
    knowledge_payload = _load_json_object(output_path / "knowledge.json")
    source_payload = _load_json_object(output_path / "metadata" / "source-map.json")
    knowledge_items = _items_by_key(knowledge_payload.get("items"), "knowledge.json")
    source_items = _items_by_key(source_payload.get("items"), "metadata/source-map.json")
    warnings_by_key = _warnings_by_key(knowledge_payload.get("warnings", []))

    written: list[SuggestionPaths] = []
    suggestion_path.mkdir(parents=True, exist_ok=True)
    for key in sorted(source_items):
        source_item = source_items[key]
        item = {**source_item, **knowledge_items.get(key, {})}
        _require_source_fields(item, key)
        before = _item_content(item, output_path)
        reason = _proposal_reason(item, warnings_by_key.get(_warning_key(item), []))
        after = _proposed_content(before, reason)
        stem = _suggestion_stem(item)
        proposal = suggestion_path / f"{stem}.update.md"
        diff = suggestion_path / f"{stem}.diff.md"
        review = suggestion_path / f"{stem}.review.json"

        proposal.write_text(_render_proposal(item, after, reason), encoding="utf-8")
        diff.write_text(_render_diff(item, before, after, reason), encoding="utf-8")
        review.write_text(
            json.dumps(_review_payload(item, proposal, diff, suggestion_path), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(
            SuggestionPaths(
                source_type=str(item["sourceType"]),
                source_id=str(item["sourceId"]),
                title=str(item["title"]),
                proposal_path=proposal,
                diff_path=diff,
                review_path=review,
            )
        )
    return written


def list_reviews(suggestions_dir: Path | str, status: ReviewStatus = "approved") -> list[ReviewEntry]:
    """Read local review files and return entries with the requested status."""

    if status not in VALID_REVIEW_STATUSES:
        raise SuggestionError(f"unknown review status: {status}")
    suggestion_path = Path(suggestions_dir)
    entries: list[ReviewEntry] = []
    for path in sorted(suggestion_path.glob("*.review.json")):
        payload = _load_json_object(path)
        payload_status = payload.get("status")
        if payload_status not in VALID_REVIEW_STATUSES:
            raise SuggestionError(f"{path} has invalid status: {payload_status}")
        if payload_status != status:
            continue
        entries.append(
            ReviewEntry(
                source_type=str(payload.get("sourceType", "")),
                source_id=str(payload.get("sourceId", "")),
                title=str(payload.get("title", "")),
                url=str(payload.get("url", "")),
                updated=str(payload.get("updated", "")),
                status=str(payload_status),
                proposal_path=str(payload.get("proposalPath", "")),
                diff_path=str(payload.get("diffPath", "")),
                reviewer=payload.get("reviewer"),
                reviewed_at=payload.get("reviewedAt"),
                note=payload.get("note"),
            )
        )
    return entries


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SuggestionError(f"missing input file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SuggestionError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SuggestionError(f"{path} must be a JSON object")
    return payload


def _items_by_key(value: Any, source_name: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        raise SuggestionError(f"{source_name} must contain an items array")
    items: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise SuggestionError(f"{source_name} item {index} must be an object")
        key = _item_key(item)
        if key in items:
            raise SuggestionError(f"{source_name} contains duplicate item: {key}")
        items[key] = item
    return items


def _warnings_by_key(value: Any) -> dict[str, list[dict[str, Any]]]:
    warnings: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(value, list):
        return warnings
    for warning in value:
        if not isinstance(warning, dict):
            continue
        source_type = warning.get("sourceType")
        url = warning.get("url")
        if not source_type or not url:
            continue
        warnings.setdefault(f"{source_type}:{url}", []).append(warning)
    return warnings


def _item_key(item: dict[str, Any]) -> str:
    return f"{item.get('sourceType')}:{item.get('sourceId')}"


def _warning_key(item: dict[str, Any]) -> str:
    return f"{item.get('sourceType')}:{item.get('url')}"


def _require_source_fields(item: dict[str, Any], key: str) -> None:
    for field in ("sourceType", "sourceId", "title", "url", "updated"):
        if not item.get(field):
            raise SuggestionError(f"{key} is missing {field}")


def _item_content(item: dict[str, Any], output_dir: Path) -> str:
    content = item.get("content")
    if isinstance(content, str) and content.strip():
        return content.rstrip() + "\n"
    content_path = item.get("contentPath")
    if isinstance(content_path, str) and content_path:
        path = Path(content_path)
        if path.is_absolute() or ".." in path.parts:
            raise SuggestionError(f"{_item_key(item)} contentPath must stay inside output")
        resolved = output_dir / path
        if resolved.is_file():
            return resolved.read_text(encoding="utf-8").rstrip() + "\n"
    return ""


def _proposal_reason(item: dict[str, Any], warnings: list[dict[str, Any]]) -> str:
    if warnings:
        messages = [str(warning.get("message", "")).strip() for warning in warnings if warning.get("message")]
        if messages:
            return " / ".join(messages)
    category = item.get("category") or "unclassified"
    return f"Source item is classified as {category}; generate a reviewable local update draft."


def _proposed_content(before: str, reason: str) -> str:
    body = before.rstrip()
    addition = "\n".join(
        [
            "## Proposed update notes",
            "",
            f"- Rationale: {reason}",
            "- Review this draft manually before copying any content into Backlog.",
        ]
    )
    return f"{body}\n\n{addition}\n" if body else f"{addition}\n"


def _render_proposal(item: dict[str, Any], after: str, reason: str) -> str:
    return "\n".join(
        [
            f"# Update proposal: {item['title']}",
            "",
            f"- Source type: {item['sourceType']}",
            f"- Source ID: {item['sourceId']}",
            f"- Backlog source URL: {item['url']}",
            f"- Last updated: {item['updated']}",
            f"- Proposal reason: {reason}",
            "",
            "## Proposed content",
            "",
            after.rstrip(),
            "",
            "## Note",
            "",
            "This content has NOT been applied to Backlog.",
            "\u0042acklog\u306b\u306f\u672a\u53cd\u6620\u3067\u3059\u3002"
            "\u4eba\u9593\u306e\u30ec\u30d3\u30e5\u30fc\u5f8c\u306b"
            "\u624b\u52d5\u3067\u6271\u3063\u3066\u304f\u3060\u3055\u3044\u3002",
            "",
        ]
    )


def _render_diff(item: dict[str, Any], before: str, after: str, reason: str) -> str:
    diff_lines = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(
        [
            f"# Update proposal diff: {item['title']}",
            "",
            "## Target",
            "",
            f"- Title: {item['title']}",
            f"- Source type: {item['sourceType']}",
            f"- Source ID: {item['sourceId']}",
            f"- Backlog source URL: {item['url']}",
            f"- Last updated: {item['updated']}",
            "",
            "## Proposal reason",
            "",
            reason,
            "",
            "## Before / After",
            "",
            "```diff",
            *diff_lines,
            "```",
            "",
            "## Note",
            "",
            "This content has NOT been applied to Backlog.",
            "\u0042acklog\u306b\u306f\u672a\u53cd\u6620\u3067\u3059\u3002"
            "\u4eba\u9593\u306e\u30ec\u30d3\u30e5\u30fc\u5f8c\u306b"
            "\u624b\u52d5\u3067\u6271\u3063\u3066\u304f\u3060\u3055\u3044\u3002",
            "",
        ]
    )


def _review_payload(item: dict[str, Any], proposal: Path, diff: Path, suggestions_dir: Path) -> dict[str, Any]:
    return {
        "sourceType": item["sourceType"],
        "sourceId": item["sourceId"],
        "title": item["title"],
        "url": item["url"],
        "updated": item["updated"],
        "proposalPath": proposal.relative_to(suggestions_dir).as_posix(),
        "diffPath": diff.relative_to(suggestions_dir).as_posix(),
        "status": "pending",
        "reviewer": None,
        "reviewedAt": None,
        "note": None,
    }


def _suggestion_stem(item: dict[str, Any]) -> str:
    return f"{_safe_part(str(item['sourceType']))}-{_safe_part(str(item['sourceId']))}"


def _safe_part(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in value.strip())
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "unknown"
