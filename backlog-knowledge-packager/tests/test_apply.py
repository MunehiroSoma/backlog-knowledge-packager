import json

import pytest

from backlog_packager import cli
from backlog_packager.apply import ApplyError, apply_approved, plan_apply
from backlog_packager.write_client import BacklogWriteError, ExplicitBacklogWriteClient


def write_review(
    suggestions,
    *,
    source_type="wiki",
    source_id="123",
    status="approved",
    updated="2026-07-01T00:00:00Z",
):
    suggestions.mkdir(exist_ok=True)
    proposal = suggestions / f"{source_type}-{source_id}.update.md"
    proposal.write_text(
        "\n".join(
            [
                "# Update proposal",
                "",
                "## Proposed content",
                "",
                "new body",
                "",
                "## Note",
                "",
                "not applied",
                "",
            ]
        ),
        encoding="utf-8",
    )
    review = {
        "sourceType": source_type,
        "sourceId": source_id,
        "title": "Team wiki",
        "url": f"https://example.backlog.com/alias/wiki/{source_id}",
        "updated": updated,
        "proposalPath": proposal.name,
        "diffPath": f"{source_type}-{source_id}.diff.md",
        "status": status,
        "reviewer": "reviewer@example.test",
        "reviewedAt": "2026-07-02T00:00:00Z",
        "note": "approved",
    }
    (suggestions / f"{source_type}-{source_id}.review.json").write_text(json.dumps(review), encoding="utf-8")
    return review


class FakeReadClient:
    def __init__(self, updated="2026-07-01T00:00:00Z", updates=None):
        self.updated = updated
        self.updates = updates or {}
        self.calls = []

    def get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        source_id = endpoint.rsplit("/", 1)[-1]
        return {"id": source_id, "updated": self.updates.get(source_id, self.updated)}


class FakeWriteClient:
    def __init__(self):
        self.calls = []

    def update_wiki(self, wiki_id, *, name, content, mail_notify=False):
        self.calls.append((wiki_id, name, content, mail_notify))
        return {"id": wiki_id}


def test_plan_apply_uses_only_approved_wiki_entries(tmp_path):
    write_review(tmp_path / "suggestions")
    write_review(tmp_path / "suggestions", source_id="456", status="pending")

    actions = plan_apply(tmp_path / "suggestions")

    assert len(actions) == 1
    assert actions[0].source_type == "wiki"
    assert actions[0].content == "new body\n"


def test_plan_apply_rejects_non_wiki_entries(tmp_path):
    write_review(tmp_path / "suggestions", source_type="document")

    with pytest.raises(ApplyError, match="cannot be applied automatically"):
        plan_apply(tmp_path / "suggestions")


def test_apply_approved_dry_run_does_not_write(tmp_path):
    write_review(tmp_path / "suggestions")

    results = apply_approved(tmp_path / "suggestions", confirm_apply=False)

    assert not results[0].applied


def test_apply_approved_writes_after_updated_check(tmp_path):
    write_review(tmp_path / "suggestions")
    read_client = FakeReadClient()
    write_client = FakeWriteClient()

    results = apply_approved(
        tmp_path / "suggestions",
        confirm_apply=True,
        read_client=read_client,
        write_client=write_client,
        audit_log=tmp_path / "audit.md",
    )

    assert results[0].applied
    assert read_client.calls == [("/api/v2/wikis/123", None)]
    assert write_client.calls == [("123", "Team wiki", "new body\n", False)]
    assert "applied: wiki:123" in (tmp_path / "audit.md").read_text(encoding="utf-8")


def test_apply_approved_rejects_updated_mismatch(tmp_path):
    write_review(tmp_path / "suggestions")

    with pytest.raises(ApplyError, match="updated mismatch"):
        apply_approved(
            tmp_path / "suggestions",
            confirm_apply=True,
            read_client=FakeReadClient(updated="2026-07-03T00:00:00Z"),
            write_client=FakeWriteClient(),
        )


def test_apply_approved_checks_all_updated_values_before_writing(tmp_path):
    write_review(tmp_path / "suggestions", source_id="123")
    write_review(tmp_path / "suggestions", source_id="456")
    write_client = FakeWriteClient()

    with pytest.raises(ApplyError, match="updated mismatch"):
        apply_approved(
            tmp_path / "suggestions",
            confirm_apply=True,
            read_client=FakeReadClient(updates={"456": "2026-07-03T00:00:00Z"}),
            write_client=write_client,
        )

    assert write_client.calls == []


def test_write_client_requires_explicit_enable():
    with pytest.raises(BacklogWriteError, match="explicit"):
        ExplicitBacklogWriteClient("https://example.backlog.com", "secret", enable_write=False)


def test_apply_cli_dry_run(capsys, tmp_path):
    write_review(tmp_path / "suggestions")

    assert cli.main(["apply", "--suggestions", str(tmp_path / "suggestions")]) == 0

    captured = capsys.readouterr()
    assert "dry-run: wiki:123" in captured.out
    assert "planned 1 approved review entries" in captured.err


def test_apply_cli_confirm_requires_explicit_write_enable(monkeypatch, capsys, tmp_path):
    write_review(tmp_path / "suggestions")
    monkeypatch.delenv("BACKLOG_ENABLE_WRITE", raising=False)

    assert cli.main(["apply", "--suggestions", str(tmp_path / "suggestions"), "--confirm-apply"]) == 1

    assert "BACKLOG_ENABLE_WRITE=1" in capsys.readouterr().err
