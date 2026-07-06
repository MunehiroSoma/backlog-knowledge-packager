import pytest

from backlog_packager.classifier import classification_summary, classify_item, classify_text, load_classification_rules
from backlog_packager.models import KnowledgeItem


def test_template_wins_before_rule() -> None:
    result = classify_text("規約テンプレート")

    assert result.category == "template"
    assert result.matched_keyword == "テンプレート"


def test_each_category_has_rule_based_match() -> None:
    cases = {
        "issue template": "template",
        "環境構築手順": "setup",
        "新人向け読む順番": "onboarding",
        "命名ルール": "rule",
        "リリース運用": "operation",
        "FAQ トラブル集": "knowledge",
        "API 参考リンク集": "reference",
    }

    for title, category in cases.items():
        assert classify_text(title).category == category


def test_content_fallback_and_tags() -> None:
    item = KnowledgeItem(
        id="document-1",
        source_type="document",
        source_id="1",
        project_key="DEMO",
        title="Project notes",
        url="https://example.backlog.com/document/1",
        updated="2026-07-01T00:00:00+09:00",
        content="- Docker をインストールする\n- git ブランチを作成する",
    )

    classified = classify_item(item)

    assert classified.category == "setup"
    assert classified.matched_keyword == "インストール"
    assert classified.classification_confidence == 0.65
    assert "environment" in classified.tags
    assert "development" in classified.tags


def test_custom_classification_rules_take_precedence(tmp_path) -> None:
    rules = tmp_path / "classification-rules.json"
    rules.write_text(
        """
        {
          "categories": {
            "rule": ["ADR"]
          },
          "tags": {
            "architecture": ["ADR", "decision record"]
          }
        }
        """,
        encoding="utf-8",
    )

    category_keywords, tag_keywords = load_classification_rules(rules)
    result = classify_text("ADR-001: logging policy", category_keywords=category_keywords, tag_keywords=tag_keywords)

    assert result.category == "rule"
    assert result.matched_keyword == "ADR"
    assert result.tags == ["architecture"]


def test_custom_classification_rules_reject_unknown_category(tmp_path) -> None:
    rules = tmp_path / "classification-rules.json"
    rules.write_text('{"categories": {"unknown": ["ADR"]}}', encoding="utf-8")

    with pytest.raises(ValueError, match="unknown classification category"):
        load_classification_rules(rules)


def test_unclassified_fallback() -> None:
    assert classify_text("random memo").category == "unclassified"


def test_classification_summary_reports_unclassified_rate_and_tags() -> None:
    items = [
        KnowledgeItem(
            id="document-1",
            source_type="document",
            source_id="1",
            project_key="DEMO",
            title="setup guide",
            url="https://example.backlog.com/document/1",
            updated="2026-07-01T00:00:00+09:00",
            category="setup",
            classification_confidence=1.0,
            tags=["environment"],
        ),
        KnowledgeItem(
            id="document-2",
            source_type="document",
            source_id="2",
            project_key="DEMO",
            title="misc",
            url="https://example.backlog.com/document/2",
            updated="2026-07-01T00:00:00+09:00",
            category="unclassified",
            classification_confidence=0.0,
        ),
    ]

    summary = classification_summary(items)

    assert summary["total"] == 2
    assert summary["unclassified"] == 1
    assert summary["unclassifiedRate"] == 0.5
    assert summary["averageConfidence"] == 0.5
    assert summary["lowConfidence"] == 1
    assert summary["tagCounts"] == {"environment": 1}
    assert summary["unclassifiedItems"] == [
        {
            "sourceType": "document",
            "sourceId": "2",
            "title": "misc",
            "url": "https://example.backlog.com/document/2",
            "updated": "2026-07-01T00:00:00+09:00",
            "category": "unclassified",
            "classificationConfidence": 0.0,
            "matchedKeyword": None,
            "tags": [],
        }
    ]
    assert summary["lowConfidenceItems"] == summary["unclassifiedItems"]
