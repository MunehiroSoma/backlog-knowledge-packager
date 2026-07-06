from datetime import datetime

from backlog_packager.generator.checklist import extract_checklist_tasks, render_setup_checklist_markdown
from backlog_packager.generator.knowledge import render_knowledge_json
from backlog_packager.generator.onboarding import render_onboarding_markdown
from backlog_packager.generator.warnings import detect_warnings, render_warnings_markdown
from backlog_packager.models import KnowledgeItem


NOW = datetime.fromisoformat("2026-07-06T12:00:00+09:00")


def item(
    source_id: str,
    title: str,
    category: str,
    updated: str = "2026-07-01T00:00:00+09:00",
    source_type: str = "document",
    content: str = "",
) -> KnowledgeItem:
    return KnowledgeItem(
        id=f"{source_type}-{source_id}",
        source_type=source_type,
        source_id=source_id,
        project_key="DEMO",
        title=title,
        url=f"https://example.backlog.com/{source_type}/{source_id}",
        updated=updated,
        category=category,
        content=content,
    )


def test_extract_checklist_tasks_from_content() -> None:
    tasks = extract_checklist_tasks(
        """
        ## Setup
        - Docker をインストールする
        - [ ] .env を作成する
        1. ローカルサーバーを起動する
        """
    )

    assert tasks == ["Docker をインストールする", ".env を作成する", "ローカルサーバーを起動する"]


def test_setup_checklist_includes_content_derived_tasks_with_sources() -> None:
    setup = item("1", "環境構築", "setup", content="- Docker をインストールする")
    rule = item("2", "命名規約", "rule")
    rendered = render_setup_checklist_markdown("DEMO", [setup, rule], NOW)

    assert "- [ ] Docker をインストールする - [環境構築]" in rendered
    assert "(updated: 2026-07-01T00:00:00+09:00)" in rendered
    assert "https://example.backlog.com/document/1" in rendered
    assert "- [ ] Read [命名規約]" in rendered


def test_setup_checklist_extracts_tasks_from_rule_content() -> None:
    rule = item(
        "1",
        "レビュー規約",
        "rule",
        content="- レビュー担当者を設定する\n- [ ] リリース前に差分を確認する",
    )

    rendered = render_setup_checklist_markdown("DEMO", [rule], NOW)

    assert "- [ ] レビュー担当者を設定する - [レビュー規約]" in rendered
    assert "- [ ] リリース前に差分を確認する - [レビュー規約]" in rendered
    assert "(updated: 2026-07-01T00:00:00+09:00)" in rendered
    assert rendered.count("- [ ] Read [レビュー規約]") == 1


def test_onboarding_contains_reading_order_and_source_context() -> None:
    rendered = render_onboarding_markdown(
        "DEMO",
        [
            item("1", "新人向け資料", "onboarding", content="最初に読む資料です。"),
            item("2", "命名規約", "rule", content="命名規約の要約。"),
        ],
        NOW,
    )

    assert "## Reading order" in rendered
    assert "1. 新人向け資料" in rendered
    assert "- Source: https://example.backlog.com/document/2" in rendered


def test_warning_detection_covers_stale_terms_broken_urls_and_duplicates() -> None:
    warnings = detect_warnings(
        [
            item("1", "旧 API テンプレート", "template", "2024-01-01T00:00:00+09:00"),
            item("2", "API", "template", "2026-07-01T00:00:00+09:00"),
            item("3", "API テンプレート", "template", "2026-07-02T00:00:00+09:00", source_type="wiki"),
        ],
        now=NOW,
        url_checker=lambda url: not url.endswith("/2"),
        check_source_urls=True,
    )

    warning_types = [warning.type for warning in warnings]
    assert "stale" in warning_types
    assert "deprecated_term" in warning_types
    assert "broken_url" in warning_types
    assert "duplicate" in warning_types

    rendered = render_warnings_markdown("DEMO", warnings, NOW)
    assert "Related candidates" in rendered
    assert "Updated more than 1 year ago" in rendered


def test_warning_detection_checks_urls_inside_content() -> None:
    source = item(
        "1",
        "Reference links",
        "reference",
        content="See https://ok.example.test and https://broken.example.test for details.",
    )

    warnings = detect_warnings([source], now=NOW, url_checker=lambda url: "broken" not in url)

    assert len(warnings) == 1
    assert warnings[0].type == "broken_url"
    assert "https://broken.example.test" in warnings[0].message


def test_warning_detection_flags_deprecated_terms_inside_content() -> None:
    source = item(
        "1",
        "API guide",
        "rule",
        content="This procedure is deprecated. Use the new API guide instead.",
    )

    warnings = detect_warnings([source], now=NOW)

    assert [warning.type for warning in warnings] == ["deprecated_term"]
    assert "Title or content" in warnings[0].message


def test_warning_detection_does_not_check_source_urls_by_default() -> None:
    source = item("1", "Source-backed item", "reference")

    warnings = detect_warnings([source], now=NOW, url_checker=lambda url: False)

    assert not [warning for warning in warnings if warning.type == "broken_url"]


def test_warning_detection_flags_similar_template_titles() -> None:
    warnings = detect_warnings(
        [
            item("1", "Issue template", "template", source_type="document"),
            item("2", "Issues template", "template", source_type="wiki"),
        ],
        now=NOW,
    )

    duplicate_warnings = [warning for warning in warnings if warning.type == "duplicate"]
    assert len(duplicate_warnings) == 2
    assert all("Similar title" in warning.message for warning in duplicate_warnings)
    assert duplicate_warnings[0].related[0]["title"] == "Issues template"


def test_knowledge_json_contains_warnings_array() -> None:
    source = item("1", "旧ルール", "rule", "2024-01-01T00:00:00+09:00")
    warnings = detect_warnings([source], now=NOW)

    rendered = render_knowledge_json("DEMO", [source], warnings, NOW)

    assert '"warnings"' in rendered
    assert '"sourceType": "document"' in rendered
