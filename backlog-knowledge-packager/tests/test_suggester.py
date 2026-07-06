import json

from backlog_packager import cli
from backlog_packager.generator.packager import write_project_outputs
from backlog_packager.models import KnowledgeItem, WarningItem
from backlog_packager.suggester import generate_suggestions, list_reviews


def source_item() -> KnowledgeItem:
    return KnowledgeItem(
        id="document-123",
        source_type="document",
        source_id="123",
        project_key="DEMO",
        title="Coding conventions",
        url="https://example.backlog.com/document/123",
        updated="2026-07-01T00:00:00+09:00",
        category="rule",
        content="Use small pull requests.\n",
    )


def test_generate_suggestions_writes_update_diff_and_review_files(tmp_path) -> None:
    item = source_item()
    write_project_outputs(
        "DEMO",
        [item],
        tmp_path / "out",
        warnings=[
            WarningItem(
                type="stale",
                message="Updated more than 1 year ago.",
                title=item.title,
                url=item.url,
                updated=item.updated,
                source_type=item.source_type,
            )
        ],
    )

    written = generate_suggestions(tmp_path / "out", tmp_path / "suggestions")

    assert len(written) == 1
    update_path = tmp_path / "suggestions" / "document-123.update.md"
    diff_path = tmp_path / "suggestions" / "document-123.diff.md"
    review_path = tmp_path / "suggestions" / "document-123.review.json"
    assert update_path.exists()
    assert diff_path.exists()
    assert review_path.exists()

    diff = diff_path.read_text(encoding="utf-8")
    assert "Coding conventions" in diff
    assert "Source type: document" in diff
    assert "Backlog source URL: https://example.backlog.com/document/123" in diff
    assert "Last updated: 2026-07-01T00:00:00+09:00" in diff
    assert "Updated more than 1 year ago." in diff
    assert "--- before" in diff
    assert "+++ after" in diff
    assert "\u0042acklog\u306b\u306f\u672a\u53cd\u6620" in diff

    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review == {
        "sourceType": "document",
        "sourceId": "123",
        "title": "Coding conventions",
        "url": "https://example.backlog.com/document/123",
        "updated": "2026-07-01T00:00:00+09:00",
        "proposalPath": "document-123.update.md",
        "diffPath": "document-123.diff.md",
        "status": "pending",
        "reviewer": None,
        "reviewedAt": None,
        "note": None,
    }


def test_list_reviews_returns_only_requested_status(tmp_path) -> None:
    write_project_outputs("DEMO", [source_item()], tmp_path / "out")
    generate_suggestions(tmp_path / "out", tmp_path / "suggestions")
    review_path = tmp_path / "suggestions" / "document-123.review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["status"] = "approved"
    review["reviewer"] = "reviewer@example.test"
    review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")

    approved = list_reviews(tmp_path / "suggestions")
    pending = list_reviews(tmp_path / "suggestions", "pending")

    assert [entry.source_id for entry in approved] == ["123"]
    assert approved[0].reviewer == "reviewer@example.test"
    assert pending == []


def test_suggest_cli_and_review_list_cli(capsys, tmp_path) -> None:
    write_project_outputs("DEMO", [source_item()], tmp_path / "out")

    assert (
        cli.main(["suggest", "--output", str(tmp_path / "out"), "--suggestions", str(tmp_path / "suggestions")])
        == 0
    )
    review_path = tmp_path / "suggestions" / "document-123.review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["status"] = "approved"
    review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")

    assert cli.main(["review-list", "--suggestions", str(tmp_path / "suggestions")]) == 0

    captured = capsys.readouterr()
    assert "generated 1 local suggestions" in captured.err
    assert "document:123\tCoding conventions\tdocument-123.update.md\tdocument-123.diff.md" in captured.out
    assert "listed 1 approved review entries" in captured.err
