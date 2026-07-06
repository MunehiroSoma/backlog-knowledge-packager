"""Rule-based and semantic-lite classification."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from collections import Counter
from pathlib import Path

from .models import Category, ClassificationResult, KnowledgeItem


CLASSIFIABLE_CATEGORIES = (
    "template",
    "setup",
    "onboarding",
    "rule",
    "operation",
    "knowledge",
    "reference",
)
CategoryKeywords = list[tuple[Category, tuple[str, ...]]]
TagKeywords = dict[str, tuple[str, ...]]

CATEGORY_KEYWORDS: list[tuple[Category, tuple[str, ...]]] = [
    ("template", ("template", "テンプレート", "雛形", "ひな形", "フォーマット", "書式")),
    (
        "setup",
        ("setup", "セットアップ", "環境構築", "環境設定", "インストール", "初期設定", "ローカル起動", "導入手順"),
    ),
    ("onboarding", ("onboarding", "オンボーディング", "新人", "新メンバー", "入門", "読む順番")),
    ("rule", ("rule", "rules", "規約", "ルール", "規則", "命名", "コーディング規約", "ブランチ", "レビュー基準")),
    ("operation", ("operation", "運用", "手順", "リリース", "障害", "インシデント", "デプロイ", "当番")),
    ("knowledge", ("knowledge", "ナレッジ", "トラブル", "faq", "q&a", "qa", "障害対応", "意思決定", "議事録")),
    ("reference", ("reference", "参考", "参照", "リンク集", "url一覧", "url", "api", "仕様書")),
]

TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "development": ("開発", "実装", "coding", "コーディング", "レビュー", "ブランチ", "git"),
    "release": ("リリース", "deploy", "デプロイ", "本番", "staging"),
    "environment": ("環境", "setup", "セットアップ", "install", "インストール", "docker"),
    "template": ("template", "テンプレート", "雛形", "ひな形", "フォーマット"),
    "deprecated": ("旧", "old", "deprecated", "廃止", "obsolete"),
    "reference": ("http://", "https://", "url", "リンク", "参考", "参照"),
}
REFERENCE_EXTENSIONS = (
    ".csv",
    ".doc",
    ".docx",
    ".drawio",
    ".html",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsm",
    ".xlsx",
    ".zip",
)


def load_classification_rules(path: str | Path) -> tuple[CategoryKeywords, TagKeywords]:
    """Load optional project-specific classifier keywords from JSON."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("classification rules must be a JSON object")

    category_keywords = _merge_category_keywords(_parse_category_rules(payload.get("categories", {})))
    tag_keywords = _merge_tag_keywords(_parse_tag_rules(payload.get("tags", {})))
    return category_keywords, tag_keywords


def classify_text(
    title: str,
    path: str | None = None,
    content: str = "",
    category_keywords: CategoryKeywords | None = None,
    tag_keywords: TagKeywords | None = None,
) -> ClassificationResult:
    """Classify text by ordered keyword matching with content fallback."""

    resolved_categories = category_keywords or CATEGORY_KEYWORDS
    resolved_tags = tag_keywords or TAG_KEYWORDS
    primary = _normalize(" ".join(part for part in (title, path or "") if part))
    secondary = _normalize(content)

    for category, keywords in resolved_categories:
        keyword = _find_keyword(primary, keywords)
        if keyword:
            return ClassificationResult(category, keyword, 1.0, tags_for_text(primary + " " + secondary, resolved_tags))

    for category, keywords in resolved_categories:
        keyword = _find_keyword(secondary, keywords)
        if keyword:
            return ClassificationResult(category, keyword, 0.65, tags_for_text(primary + " " + secondary, resolved_tags))

    extension = _find_reference_extension(primary)
    if extension:
        return ClassificationResult("reference", extension, 0.45, tags_for_text(primary + " " + secondary, resolved_tags))

    return ClassificationResult("unclassified", None, 0.0, tags_for_text(primary + " " + secondary, resolved_tags))


def classify_item(
    item: KnowledgeItem,
    category_keywords: CategoryKeywords | None = None,
    tag_keywords: TagKeywords | None = None,
) -> KnowledgeItem:
    result = classify_text(item.title, item.content_path, item.content, category_keywords, tag_keywords)
    item.category = result.category
    item.matched_keyword = result.matched_keyword
    item.classification_confidence = result.confidence
    item.tags = sorted(set(item.tags).union(result.tags))
    return item


def classify_items(
    items: Iterable[KnowledgeItem],
    category_keywords: CategoryKeywords | None = None,
    tag_keywords: TagKeywords | None = None,
) -> list[KnowledgeItem]:
    return [classify_item(item, category_keywords, tag_keywords) for item in items]


def classification_summary(items: Iterable[KnowledgeItem]) -> dict[str, object]:
    item_list = list(items)
    counts = Counter(item.category for item in item_list)
    total = len(item_list)
    unclassified = counts.get("unclassified", 0)
    low_confidence_items = [item for item in item_list if item.classification_confidence < 0.5]
    return {
        "total": total,
        "counts": dict(sorted(counts.items())),
        "unclassified": unclassified,
        "unclassifiedRate": (unclassified / total) if total else 0.0,
        "averageConfidence": _average_confidence(item_list),
        "lowConfidence": len(low_confidence_items),
        "tagCounts": dict(sorted(Counter(tag for item in item_list for tag in item.tags).items())),
        "unclassifiedItems": [_classification_diagnostic(item) for item in item_list if item.category == "unclassified"],
        "lowConfidenceItems": [_classification_diagnostic(item) for item in low_confidence_items],
    }


def tags_for_text(text: str, tag_keywords: TagKeywords | None = None) -> list[str]:
    resolved_tags = tag_keywords or TAG_KEYWORDS
    normalized = _normalize(text)
    return sorted(tag for tag, keywords in resolved_tags.items() if _find_keyword(normalized, keywords))


def _parse_category_rules(value: object) -> CategoryKeywords:
    if value in (None, {}):
        return []
    if not isinstance(value, dict):
        raise ValueError("classification rule 'categories' must be an object")

    parsed: CategoryKeywords = []
    for category, keywords in value.items():
        if category not in CLASSIFIABLE_CATEGORIES:
            raise ValueError(f"unknown classification category: {category}")
        parsed.append((category, _parse_keywords(keywords, f"categories.{category}")))  # type: ignore[arg-type]
    return parsed


def _parse_tag_rules(value: object) -> TagKeywords:
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise ValueError("classification rule 'tags' must be an object")
    return {str(tag): _parse_keywords(keywords, f"tags.{tag}") for tag, keywords in value.items()}


def _parse_keywords(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"classification rule '{name}' must be a non-empty string array")
    keywords = tuple(keyword.strip() for keyword in value if isinstance(keyword, str) and keyword.strip())
    if len(keywords) != len(value):
        raise ValueError(f"classification rule '{name}' must contain only non-empty strings")
    return keywords


def _merge_category_keywords(custom: CategoryKeywords) -> CategoryKeywords:
    if not custom:
        return list(CATEGORY_KEYWORDS)
    return [*custom, *CATEGORY_KEYWORDS]


def _merge_tag_keywords(custom: TagKeywords) -> TagKeywords:
    if not custom:
        return dict(TAG_KEYWORDS)
    merged = dict(TAG_KEYWORDS)
    for tag, keywords in custom.items():
        merged[tag] = (*keywords, *merged.get(tag, ()))
    return merged


def _find_keyword(text: str, keywords: Iterable[str]) -> str | None:
    for keyword in keywords:
        normalized_keyword = _normalize(keyword)
        if re.search(re.escape(normalized_keyword), text):
            return keyword
    return None


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _find_reference_extension(text: str) -> str | None:
    return next((extension for extension in REFERENCE_EXTENSIONS if extension in text), None)


def _average_confidence(items: list[KnowledgeItem]) -> float:
    if not items:
        return 0.0
    return sum(item.classification_confidence for item in items) / len(items)


def _classification_diagnostic(item: KnowledgeItem) -> dict[str, object]:
    return {
        "sourceType": item.source_type,
        "sourceId": item.source_id,
        "title": item.title,
        "url": item.url,
        "updated": item.updated,
        "category": item.category,
        "classificationConfidence": item.classification_confidence,
        "matchedKeyword": item.matched_keyword,
        "tags": list(item.tags),
    }
