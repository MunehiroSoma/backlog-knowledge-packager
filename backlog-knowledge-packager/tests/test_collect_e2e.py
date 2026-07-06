import json
import zipfile

from backlog_packager import cli
from backlog_packager.verify import verify_project_output


def test_collect_all_targets_then_verify_output(monkeypatch, tmp_path) -> None:
    class FakeBacklog:
        def __init__(self, base_url, api_key):
            self.base_url = base_url
            self.api_key = api_key

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "doc-1",
                        "title": "Coding rule",
                        "plain": "- Use feature branches",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                        "tags": [{"name": "development"}],
                    },
                    {
                        "id": "doc-2",
                        "title": "Environment setup",
                        "plain": "- install docker\n- run pytest",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-03T00:00:00Z",
                    },
                ]
            if endpoint == "/api/v2/documents/doc-1":
                return {
                    "id": "doc-1",
                    "title": "Coding rule",
                    "plain": "- Use feature branches",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                    "tags": [{"name": "development"}],
                }
            if endpoint == "/api/v2/documents/doc-2":
                return {
                    "id": "doc-2",
                    "title": "Environment setup",
                    "plain": "- install docker\n- run pytest",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-03T00:00:00Z",
                }
            if endpoint == "/api/v2/wikis":
                return [
                    {
                        "id": "wiki-1",
                        "name": "Onboarding reading order",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-04T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/wikis/wiki-1":
                return {
                    "id": "wiki-1",
                    "name": "Onboarding reading order",
                    "content": "Start with Coding rule, then Environment setup.",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-04T00:00:00Z",
                }
            if endpoint.startswith("/api/v2/projects/DEMO/files/metadata/"):
                return [
                    {
                        "id": "file-1",
                        "type": "file",
                        "dir": "/templates/",
                        "name": "issue-template.md",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-05T00:00:00Z",
                    }
                ]
            return []

        def download(self, endpoint, dest, params=None):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("# Issue template", encoding="utf-8")
            return dest

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "demo-space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeBacklog)

    exit_code = cli.main(
        [
            "collect",
            "--project",
            "DEMO",
            "--targets",
            "documents,wiki,shared-files",
            "--output",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert verify_project_output(tmp_path).ok
    assert "install docker" in (tmp_path / "setup-checklist.md").read_text(encoding="utf-8")
    assert "Onboarding reading order" in (tmp_path / "onboarding.md").read_text(encoding="utf-8")
    summary = json.loads((tmp_path / "metadata" / "classification-summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 4
    assert summary["counts"]["rule"] == 1
    assert summary["counts"]["setup"] == 1
    assert summary["counts"]["onboarding"] == 1
    assert summary["counts"]["template"] == 1
    collection_summary = json.loads((tmp_path / "metadata" / "collection-summary.json").read_text(encoding="utf-8"))
    assert collection_summary["documents"]["detailFetched"] == 2
    assert collection_summary["wiki"]["detailFetched"] == 1
    assert collection_summary["shared-files"]["downloaded"] == 1
    with zipfile.ZipFile(tmp_path / "templates.zip") as archive:
        names = set(archive.namelist())
        assert "project-package/templates/issue-template.md" in names
        assert "project-package/rules/Coding-rule.md" in names


def test_phase2_acceptance_flow_exercises_all_phase2_requirements(monkeypatch, tmp_path) -> None:
    created_clients = []

    class Phase2Backlog:
        def __init__(self, base_url, api_key):
            self.document_detail_calls = 0
            self.wiki_detail_calls = 0
            self.download_calls = 0
            created_clients.append(self)

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "rule-1",
                        "title": "Coding rule",
                        "plain": "- Configure branch protection",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                        "tags": [{"name": "development"}],
                    },
                    {
                        "id": "setup-1",
                        "title": "Environment setup",
                        "plain": "- install docker\n- run pytest",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-03T00:00:00Z",
                    },
                    {
                        "id": "knowledge-1",
                        "title": "Trouble FAQ",
                        "plain": "Past knowledge: restart the worker after config changes.",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-04T00:00:00Z",
                    },
                    {
                        "id": "template-1",
                        "title": "API template",
                        "plain": "deprecated old template",
                        "created": "2024-01-01T00:00:00Z",
                        "updated": "2024-01-01T00:00:00Z",
                    },
                ]
            if endpoint.startswith("/api/v2/documents/"):
                self.document_detail_calls += 1
                document_id = endpoint.rsplit("/", 1)[-1]
                return next(item for item in self.get("/api/v2/documents") if item["id"] == document_id)
            if endpoint == "/api/v2/wikis":
                return [
                    {
                        "id": "wiki-1",
                        "name": "Onboarding reading order",
                        "content": "Read Coding rule, Environment setup, then Trouble FAQ.",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-05T00:00:00Z",
                    },
                    {
                        "id": "wiki-2",
                        "name": "API template",
                        "content": "Template copy for duplicate detection.",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-06T00:00:00Z",
                    },
                ]
            if endpoint.startswith("/api/v2/wikis/"):
                self.wiki_detail_calls += 1
                wiki_id = endpoint.rsplit("/", 1)[-1]
                return next(item for item in self.get("/api/v2/wikis") if item["id"] == wiki_id)
            if endpoint.startswith("/api/v2/projects/DEMO/files/metadata/"):
                return [
                    {
                        "id": "file-1",
                        "type": "file",
                        "dir": "/templates/",
                        "name": "api-template.md",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-06T00:00:00Z",
                    }
                ]
            return []

        def download(self, endpoint, dest, params=None):
            self.download_calls += 1
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("# API template", encoding="utf-8")
            return dest

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "demo-space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", Phase2Backlog)

    args = [
        "collect",
        "--project",
        "DEMO",
        "--targets",
        "documents,wiki,shared-files",
        "--output",
        str(tmp_path),
    ]
    assert cli.main(args) == 0
    assert (
        cli.main(
            [
                "verify-output",
                "--output",
                str(tmp_path),
                "--max-unclassified-rate",
                "0.2",
                "--require-no-partial-failures",
                "--write-report",
            ]
        )
        == 0
    )
    assert cli.main(args) == 0
    assert (
        cli.main(
            [
                "verify-output",
                "--output",
                str(tmp_path),
                "--max-unclassified-rate",
                "0.2",
                "--require-cache-skip",
                "--require-no-partial-failures",
                "--write-report",
            ]
        )
        == 0
    )

    first_client, second_client = created_clients
    assert first_client.document_detail_calls == 4
    assert first_client.wiki_detail_calls == 2
    assert first_client.download_calls == 1
    assert second_client.document_detail_calls == 0
    assert second_client.wiki_detail_calls == 0
    assert second_client.download_calls == 0

    classification = json.loads((tmp_path / "metadata" / "classification-summary.json").read_text(encoding="utf-8"))
    assert classification["unclassifiedRate"] == 0
    assert classification["unclassifiedItems"] == []
    assert classification["counts"]["onboarding"] == 1
    assert classification["counts"]["knowledge"] == 1
    assert classification["counts"]["template"] == 3

    collection = json.loads((tmp_path / "metadata" / "collection-summary.json").read_text(encoding="utf-8"))
    assert collection["documents"]["skippedByCache"] == 4
    assert collection["wiki"]["skippedByCache"] == 2
    assert collection["shared-files"]["skippedByCache"] == 1
    assert json.loads((tmp_path / "metadata" / "partial-failures.json").read_text(encoding="utf-8")) == []
    report = (tmp_path / "metadata" / "acceptance-report.md").read_text(encoding="utf-8")
    assert "- Verification: PASS" in report
    assert "- Require cache skip: True" in report
    assert "- Require no partial failures: True" in report
    assert "- duplicate:" in report
    assert "- deprecated_term:" in report
    assert "- stale:" in report

    warnings_md = (tmp_path / "warnings.md").read_text(encoding="utf-8")
    assert "stale" in warnings_md
    assert "deprecated_term" in warnings_md
    assert "duplicate" in warnings_md
    assert "https://demo-space.backlog.com/document/template-1" in warnings_md

    onboarding_md = (tmp_path / "onboarding.md").read_text(encoding="utf-8")
    assert "## Reading order" in onboarding_md
    assert "## Team rules" in onboarding_md
    assert "## Past knowledge" in onboarding_md
    assert "https://demo-space.backlog.com/document/knowledge-1" in onboarding_md

    checklist_md = (tmp_path / "setup-checklist.md").read_text(encoding="utf-8")
    assert "Configure branch protection" in checklist_md
    assert "install docker" in checklist_md
    assert "(updated: 2026-07-03T00:00:00Z)" in checklist_md
