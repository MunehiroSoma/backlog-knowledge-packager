import json
import zipfile
from datetime import datetime

from backlog_packager.generator.packager import write_project_outputs
from backlog_packager.models import KnowledgeItem
from backlog_packager.verify import verify_project_output, write_acceptance_report


NOW = datetime.fromisoformat("2026-07-06T12:00:00+09:00")


def test_verify_project_output_accepts_valid_phase2_package(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )

    result = verify_project_output(str(tmp_path))

    assert result.ok
    assert result.errors == []


def test_verify_project_output_reports_missing_required_file(tmp_path) -> None:
    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "missing required output: knowledge.md" in result.errors


def test_verify_project_output_reports_source_map_items_without_source_context(tmp_path) -> None:
    for relative in (
        "knowledge.md",
        "references.md",
        "setup-checklist.md",
        "onboarding.md",
        "warnings.md",
    ):
        (tmp_path / relative).write_text("", encoding="utf-8")
    (tmp_path / "knowledge.json").write_text(json.dumps({"items": [], "warnings": []}), encoding="utf-8")
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "source-map.json").write_text(json.dumps({"items": [{"title": "missing url"}]}), encoding="utf-8")
    (metadata / "classification-summary.json").write_text(
        json.dumps(
            {
                "total": 1,
                "counts": {},
                "unclassified": 0,
                "unclassifiedRate": 0,
                "averageConfidence": 0,
                "lowConfidence": 0,
                "tagCounts": {},
                "unclassifiedItems": [],
                "lowConfidenceItems": [],
            }
        ),
        encoding="utf-8",
    )
    (metadata / "collection-summary.json").write_text(json.dumps({}), encoding="utf-8")
    (metadata / "partial-failures.json").write_text(json.dumps([]), encoding="utf-8")
    with zipfile.ZipFile(tmp_path / "templates.zip", "w") as archive:
        archive.writestr("project-package/README.md", "")
        archive.writestr("project-package/references.md", "")
        archive.writestr("project-package/setup-checklist.md", "")
        archive.writestr("project-package/onboarding.md", "")
        archive.writestr("project-package/warnings.md", "")
        archive.writestr("project-package/original-links.json", "[]")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "source-map item 0 is missing url" in result.errors


def test_verify_project_output_reports_invalid_partial_failures(tmp_path) -> None:
    write_project_outputs("DEMO", [], tmp_path, now=NOW)
    (tmp_path / "metadata" / "partial-failures.json").write_text(json.dumps(["ok", ""]), encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "partial-failures item 1 must be a non-empty string" in result.errors


def test_verify_project_output_can_require_no_partial_failures(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [],
        tmp_path,
        raw_metadata={"partial-failures": ["wiki skipped: unavailable"]},
        now=NOW,
    )

    result = verify_project_output(tmp_path, require_no_partial_failures=True)

    assert not result.ok
    assert "partial-failures contains 1 entries" in result.errors


def test_write_acceptance_report_summarizes_phase2_metadata(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="API template",
                url="https://example.backlog.com/document/1",
                updated="2024-01-01T00:00:00+09:00",
                category="template",
                classification_confidence=1.0,
                content="deprecated template",
            )
        ],
        tmp_path,
        raw_metadata={
            "collection-summary": {"documents": {"listed": 1, "detailFetched": 1, "skippedByCache": 0}},
            "partial-failures": ["wiki skipped: unavailable"],
        },
        now=NOW,
    )
    result = verify_project_output(tmp_path, max_unclassified_rate=0.2)

    report_path = write_acceptance_report(
        tmp_path,
        result,
        max_unclassified_rate=0.2,
        require_cache_skip=False,
        require_no_partial_failures=False,
    )

    report = report_path.read_text(encoding="utf-8")
    assert "# Phase 2 acceptance report" in report
    assert "- Verification: PASS" in report
    assert "- Max unclassified rate: 0.200" in report
    assert "- #14 / FR-15 Differential sync:" in report
    assert "- #19 / FR-20 Duplicates:" in report
    assert "- documents:" in report
    assert "- deprecated_term:" in report
    assert "- wiki skipped: unavailable" in report


def test_verify_project_output_reports_cross_file_item_mismatch(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "knowledge.json").write_text(json.dumps({"items": [], "warnings": []}), encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "knowledge.json is missing source-map items: document:1" in result.errors


def test_verify_project_output_reports_classification_mismatch_between_source_map_and_knowledge_json(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                classification_confidence=1.0,
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    payload = json.loads((tmp_path / "knowledge.json").read_text(encoding="utf-8"))
    payload["items"][0]["category"] = "setup"
    payload["items"][0]["classificationConfidence"] = 0.25
    (tmp_path / "knowledge.json").write_text(json.dumps(payload), encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "knowledge.json category does not match source-map for document:1" in result.errors
    assert "knowledge.json classificationConfidence does not match source-map for document:1" in result.errors


def test_verify_project_output_reports_missing_content_path_files(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content_path="files/documents/missing.md",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "source-map item 0 contentPath does not exist: files/documents/missing.md" in result.errors
    assert "knowledge.json item 0 contentPath does not exist: files/documents/missing.md" in result.errors


def test_verify_project_output_reports_content_path_that_escapes_output(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content_path="../outside.md",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "source-map item 0 contentPath must be relative inside output" in result.errors
    assert "knowledge.json item 0 contentPath must be relative inside output" in result.errors


def test_verify_project_output_reports_knowledge_json_items_without_source_context(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "knowledge.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "sourceType": "document",
                        "sourceId": "1",
                        "title": "coding rule",
                        "category": "rule",
                    }
                ],
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "knowledge.json item 0 is missing url" in result.errors
    assert "knowledge.json item 0 is missing updated" in result.errors


def test_verify_project_output_reports_warning_context_errors(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    payload = json.loads((tmp_path / "knowledge.json").read_text(encoding="utf-8"))
    payload["warnings"] = [
        {
            "type": "duplicate",
            "message": "Duplicate",
            "title": "coding rule",
            "url": "https://example.backlog.com/document/1",
            "updated": "2026-07-01T00:00:00+09:00",
            "sourceType": "document",
            "related": [{"title": "coding rule copy"}],
        }
    ]
    (tmp_path / "knowledge.json").write_text(json.dumps(payload), encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "knowledge.json warning 0 related item 0 is missing url" in result.errors
    assert "knowledge.json warning 0 related item 0 is missing updated" in result.errors


def test_verify_project_output_reports_knowledge_markdown_missing_source_traceability(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "knowledge.md").write_text("# Broken knowledge\n\ncoding rule\n", encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "knowledge.md is missing url for source-map item 0" in result.errors
    assert "knowledge.md is missing updated for source-map item 0" in result.errors


def test_verify_project_output_reports_onboarding_markdown_missing_source_traceability(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="onboarding guide",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="onboarding",
                content="Read this first.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "onboarding.md").write_text("# Broken onboarding\n\nonboarding guide\n", encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "onboarding.md is missing url for source-map item 0" in result.errors
    assert "onboarding.md is missing updated for source-map item 0" in result.errors


def test_verify_project_output_reports_setup_checklist_missing_source_traceability(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="setup guide",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="setup",
                content="- install docker",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "setup-checklist.md").write_text("# Broken checklist\n\nsetup guide\n", encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "setup-checklist.md is missing url for source-map item 0" in result.errors
    assert "setup-checklist.md is missing updated for source-map item 0" in result.errors


def test_verify_project_output_reports_warnings_markdown_missing_related_traceability(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="API template",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="template",
                content="",
            ),
            KnowledgeItem(
                id="wiki-2",
                source_type="wiki",
                source_id="2",
                project_key="DEMO",
                title="API template",
                url="https://example.backlog.com/wiki/2",
                updated="2026-07-02T00:00:00+09:00",
                category="template",
                content="",
            ),
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "warnings.md").write_text("# Broken warnings\n\nAPI template\n", encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert any(error.startswith("warnings.md is missing url for knowledge.json warning") for error in result.errors)
    assert any("related item" in error for error in result.errors)


def test_verify_project_output_reports_warnings_markdown_missing_warning_content(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="旧ルール",
                url="https://example.backlog.com/document/1",
                updated="2024-01-01T00:00:00+09:00",
                category="rule",
                content="old rule",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "warnings.md").write_text("# DEMO warnings\n\nNo warnings.\n", encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "warnings.md says no warnings despite knowledge.json warnings" in result.errors
    assert "warnings.md is missing type for knowledge.json warning 0" in result.errors
    assert "warnings.md is missing message for knowledge.json warning 0" in result.errors


def test_verify_project_output_reports_missing_no_warnings_marker(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "warnings.md").write_text("# DEMO warnings\n", encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "warnings.md is missing the no-warnings marker" in result.errors


def test_verify_project_output_reports_classification_summary_mismatch(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "metadata" / "classification-summary.json").write_text(
        json.dumps(
            {
                "total": 2,
                "counts": {"rule": 2},
                "unclassified": 0,
                "unclassifiedRate": 0,
                "averageConfidence": 1,
                "lowConfidence": 0,
                "tagCounts": {},
                "unclassifiedItems": [],
                "lowConfidenceItems": [],
            }
        ),
        encoding="utf-8",
    )

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "classification-summary total 2 does not match source-map item count 1" in result.errors
    assert "classification-summary counts total 2 does not match source-map item count 1" in result.errors


def test_verify_project_output_reports_classification_summary_metric_mismatch(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                classification_confidence=1.0,
                content="Use pull requests.",
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
                content="Misc.",
            ),
        ],
        tmp_path,
        now=NOW,
    )
    (tmp_path / "metadata" / "classification-summary.json").write_text(
        json.dumps(
            {
                "total": 2,
                "counts": {"rule": 1, "unclassified": 1},
                "unclassified": 0,
                "unclassifiedRate": 0.0,
                "averageConfidence": 1.0,
                "lowConfidence": 0,
                "tagCounts": {},
                "unclassifiedItems": [],
                "lowConfidenceItems": [],
            }
        ),
        encoding="utf-8",
    )

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "classification-summary unclassified does not match source-map" in result.errors
    assert "classification-summary unclassifiedRate does not match source-map" in result.errors
    assert "classification-summary averageConfidence does not match source-map" in result.errors
    assert "classification-summary lowConfidence does not match source-map" in result.errors


def test_verify_project_output_reports_classification_diagnostic_mismatch(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="misc",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="unclassified",
                classification_confidence=0.0,
            )
        ],
        tmp_path,
        now=NOW,
    )
    summary = json.loads((tmp_path / "metadata" / "classification-summary.json").read_text(encoding="utf-8"))
    summary["unclassifiedItems"] = [
        {
            "sourceType": "document",
            "sourceId": "missing",
            "title": "missing",
            "url": "https://example.backlog.com/document/missing",
            "updated": "2026-07-01T00:00:00+09:00",
            "category": "unclassified",
            "classificationConfidence": 0.0,
        }
    ]
    summary["lowConfidenceItems"] = "broken"
    (tmp_path / "metadata" / "classification-summary.json").write_text(json.dumps(summary), encoding="utf-8")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "classification-summary unclassifiedItems item 0 is not present in source-map" in result.errors
    assert "classification-summary lowConfidenceItems must be an array" in result.errors


def test_verify_project_output_reports_original_links_mismatch(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        now=NOW,
    )
    with zipfile.ZipFile(tmp_path / "templates.zip", "w") as archive:
        archive.writestr("project-package/README.md", "")
        archive.writestr("project-package/references.md", "")
        archive.writestr("project-package/setup-checklist.md", "")
        archive.writestr("project-package/onboarding.md", "")
        archive.writestr("project-package/warnings.md", "")
        archive.writestr("project-package/original-links.json", "[]")

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "original-links.json is empty despite bundled rule/template items" in result.errors
    assert "original-links.json item count 0 does not match bundled rule/template count 1" in result.errors


def test_verify_project_output_reports_collection_summary_errors(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        raw_metadata={
            "collection-summary": {
                "documents": {"listed": 1, "detailFetched": 1, "skippedByCache": 1},
                "shared-files": {"listed": 1, "files": 1, "downloaded": -1, "skippedByCache": 0},
            }
        },
        now=NOW,
    )

    result = verify_project_output(tmp_path)

    assert not result.ok
    assert "collection-summary documents fetched+skipped exceeds listed" in result.errors
    assert "collection-summary shared-files.downloaded must be a non-negative integer" in result.errors


def test_verify_project_output_can_require_cache_skip_for_second_run_acceptance(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        raw_metadata={"collection-summary": {"documents": {"listed": 1, "detailFetched": 1, "skippedByCache": 0}}},
        now=NOW,
    )

    result = verify_project_output(tmp_path, require_cache_skip=True)

    assert not result.ok
    assert "collection-summary has no skippedByCache items; differential sync was not exercised" in result.errors


def test_verify_project_output_accepts_required_cache_skip_when_reported(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="coding rule",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
                content="Use pull requests.",
            )
        ],
        tmp_path,
        raw_metadata={"collection-summary": {"documents": {"listed": 1, "detailFetched": 0, "skippedByCache": 1}}},
        now=NOW,
    )

    result = verify_project_output(tmp_path, require_cache_skip=True)

    assert result.ok


def test_verify_project_output_reports_unclassified_rate_above_threshold(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="misc memo",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="unclassified",
                content="Miscellaneous.",
            )
        ],
        tmp_path,
        now=NOW,
    )

    result = verify_project_output(tmp_path, max_unclassified_rate=0.2)

    assert not result.ok
    assert "unclassified rate 1.000 exceeds threshold 0.200" in result.errors
