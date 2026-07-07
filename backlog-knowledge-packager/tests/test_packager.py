import json
import zipfile
from datetime import datetime

from backlog_packager.generator.packager import write_project_outputs
from backlog_packager.models import KnowledgeItem
from backlog_packager.sync import load_cached_items, should_fetch


NOW = datetime.fromisoformat("2026-07-06T12:00:00+09:00")


def test_write_project_outputs_creates_phase2_artifacts_and_zip(tmp_path) -> None:
    items = [
        KnowledgeItem(
            id="document-1",
            source_type="document",
            source_id="1",
            project_key="DEMO",
            title="命名規約",
            url="https://example.backlog.com/document/1",
            updated="2026-07-01T00:00:00+09:00",
            category="rule",
            content="命名規約の本文",
        ),
        KnowledgeItem(
            id="document-2",
            source_type="document",
            source_id="2",
            project_key="DEMO",
            title="環境構築",
            url="https://example.backlog.com/document/2",
            updated="2026-07-02T00:00:00+09:00",
            category="setup",
            content="- Docker をインストールする",
        ),
        KnowledgeItem(
            id="wiki-3",
            source_type="wiki",
            source_id="3",
            project_key="DEMO",
            title="命名規約",
            url="https://example.backlog.com/wiki/3",
            updated="2026-07-03T00:00:00+09:00",
            category="rule",
            content="Wiki側の命名規約",
        ),
    ]

    output = write_project_outputs(
        "DEMO",
        items,
        tmp_path,
        raw_metadata={"documents": {"count": 2}},
        now=NOW,
    )

    for path in (
        output.knowledge_md,
        output.knowledge_json,
        output.references_md,
        output.setup_checklist_md,
        output.onboarding_md,
        output.document_index_md,
        output.wiki_index_md,
        output.warnings_md,
        output.source_map_json,
        output.templates_zip,
    ):
        assert path.exists()

    assert "Docker をインストールする" in output.setup_checklist_md.read_text(encoding="utf-8")
    assert "duplicate" in output.warnings_md.read_text(encoding="utf-8")
    assert json.loads((tmp_path / "metadata" / "documents.json").read_text(encoding="utf-8")) == {"count": 2}
    assert json.loads((tmp_path / "metadata" / "partial-failures.json").read_text(encoding="utf-8")) == []
    summary = json.loads((tmp_path / "metadata" / "classification-summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["rule"] == 2

    with zipfile.ZipFile(output.templates_zip) as archive:
        names = set(archive.namelist())
        assert "project-package/onboarding.md" in names
        assert "project-package/warnings.md" in names
        assert "project-package/original-links.json" in names
        assert any(name.startswith("project-package/rules/") for name in names)


def test_source_map_can_drive_differential_sync(tmp_path) -> None:
    write_project_outputs(
        "DEMO",
        [
            KnowledgeItem(
                id="document-1",
                source_type="document",
                source_id="1",
                project_key="DEMO",
                title="命名規約",
                url="https://example.backlog.com/document/1",
                updated="2026-07-01T00:00:00+09:00",
                category="rule",
            )
        ],
        tmp_path,
        now=NOW,
    )

    cache = load_cached_items(tmp_path / "metadata" / "source-map.json")

    assert not should_fetch("document", "1", "2026-07-01T00:00:00+09:00", cache)
    assert should_fetch("document", "1", "2026-07-02T00:00:00+09:00", cache)
