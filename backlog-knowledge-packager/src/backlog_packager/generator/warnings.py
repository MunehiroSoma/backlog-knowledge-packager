"""Phase 2 stale, duplicate, and broken-link warning detection."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from difflib import SequenceMatcher

import requests

from backlog_packager.models import KnowledgeItem, WarningItem

DEPRECATED_TERMS = ("旧", "old", "deprecated", "廃止", "obsolete")
URL_PATTERN = re.compile(r"https?://[^\s<>)\]}\"']+")
SIMILAR_TITLE_THRESHOLD = 0.86


def detect_warnings(
    items: Iterable[KnowledgeItem],
    now: datetime | None = None,
    url_checker: Callable[[str], bool] | None = None,
    check_source_urls: bool = False,
) -> list[WarningItem]:
    item_list = list(items)
    current = now or datetime.now().astimezone()
    warnings: list[WarningItem] = []

    for item in item_list:
        if _is_stale(item, current):
            warnings.append(_warning("stale", "Updated more than 1 year ago.", item))
        if _has_deprecated_term(item.title) or _has_deprecated_term(item.content):
            warnings.append(_warning("deprecated_term", "Title or content contains a deprecated/old marker.", item))
        if url_checker is not None:
            if check_source_urls and not url_checker(item.url):
                warnings.append(_warning("broken_url", "Source URL could not be reached.", item))
            for linked_url in _extract_urls(item.content):
                if not url_checker(linked_url):
                    warnings.append(
                        _warning(
                            "broken_url",
                            f"Linked URL could not be reached: {linked_url}",
                            item,
                        )
                    )

    warnings.extend(_duplicate_warnings(item_list))
    return warnings


def build_requests_url_checker(timeout_seconds: float = 5.0) -> Callable[[str], bool]:
    """Build a conservative URL reachability checker for optional Phase 2 use."""

    def check(url: str) -> bool:
        try:
            response = requests.head(url, allow_redirects=True, timeout=timeout_seconds)
            if response.status_code == 405:
                response = requests.get(url, stream=True, allow_redirects=True, timeout=timeout_seconds)
            return response.status_code < 400
        except requests.RequestException:
            return False

    return check


def render_warnings_markdown(
    project_key: str,
    warnings: Iterable[WarningItem],
    now: datetime | None = None,
) -> str:
    generated = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
    lines = [f"# {project_key} warnings", "", f"> Generated: {generated}", ""]
    warning_list = list(warnings)
    if not warning_list:
        lines.append("No warnings.")
        return "\n".join(lines) + "\n"

    for warning in warning_list:
        lines.extend(
            [
                f"## {warning.type}: {warning.title}",
                "",
                f"- Message: {warning.message}",
                f"- Source: {warning.url}",
                f"- Updated: {warning.updated}",
                f"- Type: {warning.source_type}",
            ]
        )
        if warning.related:
            lines.append("- Related candidates:")
            for related in warning.related:
                lines.append(f"  - {related['title']} ({related['sourceType']}, {related['updated']}): {related['url']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _is_stale(item: KnowledgeItem, now: datetime) -> bool:
    updated = _parse_datetime(item.updated)
    return updated is not None and updated < now - timedelta(days=365)


def _parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _has_deprecated_term(title: str) -> bool:
    normalized = title.casefold()
    return any(term.casefold() in normalized for term in DEPRECATED_TERMS)


def _extract_urls(content: str) -> list[str]:
    return sorted(set(match.group(0).rstrip(".,;:") for match in URL_PATTERN.finditer(content)))


def _duplicate_warnings(items: list[KnowledgeItem]) -> list[WarningItem]:
    candidates = [item for item in items if item.category in {"template", "rule"} or item.source_type in {"document", "wiki"}]
    by_name: dict[str, list[KnowledgeItem]] = defaultdict(list)
    for item in candidates:
        by_name[_normalize_title(item.title)].append(item)

    warnings: list[WarningItem] = []
    warned_pairs: set[tuple[str, str]] = set()
    for duplicates in by_name.values():
        if len(duplicates) < 2:
            continue
        _mark_pairs(duplicates, warned_pairs)
        for item in duplicates:
            warnings.append(
                _warning(
                    "duplicate",
                    "Same or similar title appears in multiple source-backed items.",
                    item,
                    [candidate for candidate in duplicates if candidate is not item],
                )
            )

    warnings.extend(_similar_duplicate_warnings(candidates, warned_pairs))
    return warnings


def _similar_duplicate_warnings(items: list[KnowledgeItem], warned_pairs: set[tuple[str, str]]) -> list[WarningItem]:
    warnings: list[WarningItem] = []
    for index, left in enumerate(items):
        for right in items[index + 1 :]:
            pair_key = _pair_key(left, right)
            if pair_key in warned_pairs:
                continue
            left_title = _normalize_title(left.title)
            right_title = _normalize_title(right.title)
            if not left_title or not right_title:
                continue
            if _similarity(left_title, right_title) < SIMILAR_TITLE_THRESHOLD:
                continue
            warned_pairs.add(pair_key)
            warnings.append(_warning("duplicate", "Similar title appears in multiple source-backed items.", left, [right]))
            warnings.append(_warning("duplicate", "Similar title appears in multiple source-backed items.", right, [left]))
    return warnings


def _normalize_title(title: str) -> str:
    normalized = re.sub(r"[\s_\-./]+", "", title.casefold())
    normalized = re.sub(r"(templates|template|テンプレート|雛形|ひな形)$", "", normalized)
    return normalized


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _mark_pairs(items: list[KnowledgeItem], warned_pairs: set[tuple[str, str]]) -> None:
    for index, left in enumerate(items):
        for right in items[index + 1 :]:
            warned_pairs.add(_pair_key(left, right))


def _pair_key(left: KnowledgeItem, right: KnowledgeItem) -> tuple[str, str]:
    left_key = f"{left.source_type}:{left.source_id}"
    right_key = f"{right.source_type}:{right.source_id}"
    return tuple(sorted((left_key, right_key)))  # type: ignore[return-value]


def _warning(
    warning_type: str,
    message: str,
    item: KnowledgeItem,
    related: list[KnowledgeItem] | None = None,
) -> WarningItem:
    return WarningItem(
        type=warning_type,  # type: ignore[arg-type]
        message=message,
        title=item.title,
        url=item.url,
        updated=item.updated,
        source_type=item.source_type,
        related=[
            {
                "title": candidate.title,
                "url": candidate.url,
                "updated": candidate.updated,
                "sourceType": candidate.source_type,
            }
            for candidate in (related or [])
        ],
    )
