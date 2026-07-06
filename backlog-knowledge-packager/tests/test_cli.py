import json
import zipfile

from backlog_packager import cli


def test_collect_returns_config_error_for_missing_env(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BACKLOG_SPACE_KEY", raising=False)
    monkeypatch.delenv("BACKLOG_API_KEY", raising=False)

    exit_code = cli.main(["collect", "--project", "DEMO"])

    assert exit_code == 1
    assert "configuration error" in capsys.readouterr().err


def test_collect_generates_outputs_from_documents(monkeypatch, capsys, tmp_path) -> None:
    calls = []

    class FakeClient:
        def __init__(self, base_url, api_key):
            assert base_url == "https://space.backlog.com"
            assert api_key == "secret"

        def get(self, endpoint, params=None):
            calls.append((endpoint, params))
            if endpoint == "/api/v2/projects/DEMO":
                return {"id": 123}
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "1",
                        "title": "setup guide",
                        "plain": "- install docker",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/documents/1":
                return {
                    "id": "1",
                    "title": "setup guide",
                    "plain": "- install docker",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                }
            return {}

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.delenv("BACKLOG_DOMAIN", raising=False)
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    exit_code = cli.main(["collect", "--project", "DEMO", "--targets", "documents", "--output", str(tmp_path)])

    assert exit_code == 0
    assert calls[0] == ("/api/v2/space", None)
    assert calls[1] == ("/api/v2/projects/DEMO", None)
    assert calls[2] == ("/api/v2/documents", {"projectId[]": "123", "offset": 0, "count": 100})
    assert (tmp_path / "knowledge.md").exists()
    assert (tmp_path / "onboarding.md").exists()
    assert (tmp_path / "warnings.md").exists()
    assert "generated project package" in capsys.readouterr().err


def test_collect_returns_partial_failure_when_optional_target_fails(monkeypatch, capsys, tmp_path) -> None:
    class FakeClient:
        def __init__(self, base_url, api_key):
            pass

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "1",
                        "title": "setup guide",
                        "plain": "- install docker",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/documents/1":
                return {
                    "id": "1",
                    "title": "setup guide",
                    "plain": "- install docker",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                }
            if endpoint == "/api/v2/wikis":
                raise cli.BacklogApiError("GET https://space.backlog.com/api/v2/wikis failed with status 403")
            return {}

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    exit_code = cli.main(["collect", "--project", "DEMO", "--targets", "documents,wiki", "--output", str(tmp_path)])

    assert exit_code == 3
    assert (tmp_path / "knowledge.md").exists()
    assert (tmp_path / "metadata" / "collection-summary.json").exists()
    failures = json.loads((tmp_path / "metadata" / "partial-failures.json").read_text(encoding="utf-8"))
    assert failures and failures[0].startswith("wiki skipped:")
    stderr = capsys.readouterr().err
    assert "partial failure: wiki skipped" in stderr
    assert "generated project package" in stderr


def test_verify_output_can_fail_on_partial_failures(monkeypatch, capsys, tmp_path) -> None:
    class FakeClient:
        def __init__(self, base_url, api_key):
            pass

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint == "/api/v2/wikis":
                raise cli.BacklogApiError("GET https://space.backlog.com/api/v2/wikis failed with status 403")
            return {}

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    assert cli.main(["collect", "--project", "DEMO", "--targets", "wiki", "--output", str(tmp_path)]) == 3
    exit_code = cli.main(["verify-output", "--output", str(tmp_path), "--require-no-partial-failures"])

    assert exit_code == 1
    assert "error: partial-failures contains 1 entries" in capsys.readouterr().err


def test_collect_applies_custom_classification_rules(monkeypatch, tmp_path) -> None:
    class FakeClient:
        def __init__(self, base_url, api_key):
            pass

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "1",
                        "title": "ADR-001 logging decision",
                        "plain": "decision record",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/documents/1":
                return {
                    "id": "1",
                    "title": "ADR-001 logging decision",
                    "plain": "decision record",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                }
            return {}

    rules = tmp_path / "classification-rules.json"
    rules.write_text(
        '{"categories": {"rule": ["ADR"]}, "tags": {"architecture": ["decision record"]}}',
        encoding="utf-8",
    )

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    exit_code = cli.main(
        [
            "collect",
            "--project",
            "DEMO",
            "--targets",
            "documents",
            "--classification-rules",
            str(rules),
            "--output",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 0
    source_map = json.loads((tmp_path / "out" / "metadata" / "source-map.json").read_text(encoding="utf-8"))
    assert source_map["items"][0]["category"] == "rule"
    assert source_map["items"][0]["matchedKeyword"] == "ADR"
    assert source_map["items"][0]["tags"] == ["architecture"]
    summary = json.loads((tmp_path / "out" / "metadata" / "classification-summary.json").read_text(encoding="utf-8"))
    assert summary["unclassifiedRate"] == 0.0


def test_collect_reports_invalid_classification_rules_before_api_access(monkeypatch, capsys, tmp_path) -> None:
    class FakeClient:
        def __init__(self, base_url, api_key):
            raise AssertionError("client should not be constructed when classification rules are invalid")

    rules = tmp_path / "classification-rules.json"
    rules.write_text('{"categories": {"unknown": ["ADR"]}}', encoding="utf-8")

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    exit_code = cli.main(
        [
            "collect",
            "--project",
            "DEMO",
            "--classification-rules",
            str(rules),
            "--output",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 1
    assert "classification rules error: unknown classification category" in capsys.readouterr().err


def test_collect_uses_project_key_from_env_when_project_arg_is_omitted(monkeypatch, tmp_path) -> None:
    calls = []

    class FakeClient:
        def __init__(self, base_url, api_key):
            assert base_url == "https://space.backlog.com"
            assert api_key == "secret"

        def get(self, endpoint, params=None):
            calls.append((endpoint, params))
            if endpoint == "/api/v2/documents":
                return []
            return {}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setenv("BACKLOG_PROJECT_KEY", "ENVPRJ")
    monkeypatch.delenv("BACKLOG_DOMAIN", raising=False)
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    exit_code = cli.main(["collect", "--targets", "documents"])

    assert exit_code == 0
    assert calls[1] == ("/api/v2/projects/ENVPRJ", None)
    assert calls[2] == ("/api/v2/documents", {"projectId[]": "ENVPRJ", "offset": 0, "count": 100})
    assert (tmp_path / "output" / "ENVPRJ" / "knowledge.md").exists()


def test_collect_uses_numeric_project_id_for_document_list(monkeypatch, tmp_path) -> None:
    calls = []

    class FakeClient:
        def __init__(self, base_url, api_key):
            pass

        def get(self, endpoint, params=None):
            calls.append((endpoint, params))
            if endpoint == "/api/v2/projects/DEMO":
                return {"id": 987}
            if endpoint == "/api/v2/documents":
                return []
            return {}

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    exit_code = cli.main(["collect", "--project", "DEMO", "--targets", "documents", "--output", str(tmp_path)])

    assert exit_code == 0
    assert calls[2] == ("/api/v2/documents", {"projectId[]": "987", "offset": 0, "count": 100})


def test_collect_second_run_skips_unchanged_detail_fetch_and_download(monkeypatch, tmp_path) -> None:
    created_clients = []

    class FakeClient:
        def __init__(self, base_url, api_key):
            self.detail_calls = 0
            self.download_calls = 0
            created_clients.append(self)

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "1",
                        "title": "setup guide",
                        "plain": "- install docker",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/documents/1":
                self.detail_calls += 1
                return {
                    "id": "1",
                    "title": "setup guide",
                    "plain": "- install docker",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                }
            if endpoint.startswith("/api/v2/projects/DEMO/files/metadata/"):
                return [
                    {
                        "id": "2",
                        "type": "file",
                        "dir": "/templates/",
                        "name": "issue-template.md",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            return []

        def download(self, endpoint, dest, params=None):
            self.download_calls += 1
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("template", encoding="utf-8")
            return dest

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    args = ["collect", "--project", "DEMO", "--targets", "documents,shared-files", "--output", str(tmp_path)]
    assert cli.main(args) == 0
    assert cli.main(args) == 0

    first_client, second_client = created_clients
    assert first_client.detail_calls == 1
    assert first_client.download_calls == 1
    assert second_client.detail_calls == 0
    assert second_client.download_calls == 0
    summary = json.loads((tmp_path / "metadata" / "collection-summary.json").read_text(encoding="utf-8"))
    assert summary["documents"]["detailFetched"] == 0
    assert summary["documents"]["skippedByCache"] == 1
    assert summary["shared-files"]["downloaded"] == 0
    assert summary["shared-files"]["skippedByCache"] == 1
    assert cli.main(["verify-output", "--output", str(tmp_path), "--require-cache-skip"]) == 0
    with zipfile.ZipFile(tmp_path / "templates.zip") as archive:
        template_names = [name for name in archive.namelist() if name.startswith("project-package/templates/")]
        assert template_names
        assert archive.read(template_names[0]) == b"template"


def test_collect_can_skip_shared_file_downloads(monkeypatch, tmp_path) -> None:
    created_clients = []

    class FakeClient:
        def __init__(self, base_url, api_key):
            self.download_calls = 0
            created_clients.append(self)

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint.startswith("/api/v2/projects/DEMO/files/metadata/"):
                return [
                    {
                        "id": "2",
                        "type": "file",
                        "dir": "/templates/",
                        "name": "issue-template.md",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            return []

        def download(self, endpoint, dest, params=None):
            self.download_calls += 1
            return dest

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    exit_code = cli.main(
        [
            "collect",
            "--project",
            "DEMO",
            "--targets",
            "shared-files",
            "--skip-shared-file-downloads",
            "--output",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert created_clients[0].download_calls == 0
    summary = json.loads((tmp_path / "metadata" / "collection-summary.json").read_text(encoding="utf-8"))
    assert summary["shared-files"]["files"] == 1
    assert summary["shared-files"]["downloaded"] == 0


def test_collect_check_urls_writes_broken_link_warning(monkeypatch, tmp_path) -> None:
    class FakeClient:
        def __init__(self, base_url, api_key):
            pass

        def get(self, endpoint, params=None):
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "1",
                        "title": "reference links",
                        "plain": "See https://broken.example.test",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/documents/1":
                return {
                    "id": "1",
                    "title": "reference links",
                    "plain": "See https://broken.example.test",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                }
            return {}

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)
    monkeypatch.setattr(cli, "build_requests_url_checker", lambda: lambda url: "broken" not in url)

    exit_code = cli.main(["collect", "--project", "DEMO", "--targets", "documents", "--check-urls", "--output", str(tmp_path)])

    assert exit_code == 0
    warnings = (tmp_path / "warnings.md").read_text(encoding="utf-8")
    assert "Linked URL could not be reached: https://broken.example.test" in warnings


def test_collect_check_source_urls_writes_source_warning(monkeypatch, tmp_path) -> None:
    class FakeClient:
        def __init__(self, base_url, api_key):
            pass

        def get(self, endpoint, params=None):
            if endpoint == "/api/v2/documents":
                return [
                    {
                        "id": "1",
                        "title": "reference links",
                        "plain": "No external links",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/documents/1":
                return {
                    "id": "1",
                    "title": "reference links",
                    "plain": "No external links",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                }
            return {}

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)
    monkeypatch.setattr(cli, "build_requests_url_checker", lambda: lambda url: False)

    exit_code = cli.main(
        ["collect", "--project", "DEMO", "--targets", "documents", "--check-source-urls", "--output", str(tmp_path)]
    )

    assert exit_code == 0
    warnings = (tmp_path / "warnings.md").read_text(encoding="utf-8")
    assert "Source URL could not be reached." in warnings


def test_collect_second_run_reuses_cached_wiki_content(monkeypatch, tmp_path) -> None:
    created_clients = []

    class FakeClient:
        def __init__(self, base_url, api_key):
            self.wiki_detail_calls = 0
            created_clients.append(self)

        def get(self, endpoint, params=None):
            if endpoint in {"/api/v2/space", "/api/v2/projects/DEMO"}:
                return {}
            if endpoint == "/api/v2/wikis":
                return [
                    {
                        "id": "10",
                        "name": "team rule",
                        "created": "2026-07-01T00:00:00Z",
                        "updated": "2026-07-02T00:00:00Z",
                    }
                ]
            if endpoint == "/api/v2/wikis/10":
                self.wiki_detail_calls += 1
                return {
                    "id": "10",
                    "name": "team rule",
                    "content": "Review every pull request before merge.",
                    "created": "2026-07-01T00:00:00Z",
                    "updated": "2026-07-02T00:00:00Z",
                }
            return {}

    monkeypatch.setenv("BACKLOG_SPACE_KEY", "space")
    monkeypatch.setenv("BACKLOG_API_KEY", "secret")
    monkeypatch.setattr(cli, "ReadOnlyBacklogClient", FakeClient)

    args = ["collect", "--project", "DEMO", "--targets", "wiki", "--output", str(tmp_path)]
    assert cli.main(args) == 0
    assert cli.main(args) == 0

    first_client, second_client = created_clients
    assert first_client.wiki_detail_calls == 1
    assert second_client.wiki_detail_calls == 0
    assert "Review every pull request before merge." in (tmp_path / "knowledge.md").read_text(encoding="utf-8")


def test_verify_output_command_reports_success(monkeypatch, capsys, tmp_path) -> None:
    def fake_verify(output, max_unclassified_rate=None, require_cache_skip=False, require_no_partial_failures=False):
        assert max_unclassified_rate is None
        assert require_cache_skip
        assert require_no_partial_failures
        return type("Result", (), {"ok": True, "warnings": [], "errors": [], "output_dir": output})()

    monkeypatch.setattr(cli, "verify_project_output", fake_verify)

    exit_code = cli.main(
        ["verify-output", "--output", str(tmp_path), "--require-cache-skip", "--require-no-partial-failures"]
    )

    assert exit_code == 0
    assert "verified project package" in capsys.readouterr().err


def test_verify_output_command_writes_acceptance_report(monkeypatch, capsys, tmp_path) -> None:
    def fake_verify(output, max_unclassified_rate=None, require_cache_skip=False, require_no_partial_failures=False):
        return type("Result", (), {"ok": True, "warnings": [], "errors": [], "output_dir": output})()

    def fake_report(output, result, max_unclassified_rate=None, require_cache_skip=False, require_no_partial_failures=False):
        assert max_unclassified_rate == 0.2
        assert require_cache_skip
        assert require_no_partial_failures
        path = tmp_path / "metadata" / "acceptance-report.md"
        path.parent.mkdir(parents=True)
        path.write_text("report", encoding="utf-8")
        return path

    monkeypatch.setattr(cli, "verify_project_output", fake_verify)
    monkeypatch.setattr(cli, "write_acceptance_report", fake_report)

    exit_code = cli.main(
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

    assert exit_code == 0
    assert "wrote acceptance report:" in capsys.readouterr().err


def test_verify_output_command_reports_errors(monkeypatch, capsys, tmp_path) -> None:
    def fake_verify(output, max_unclassified_rate=None, require_cache_skip=False, require_no_partial_failures=False):
        assert max_unclassified_rate == 0.25
        assert not require_cache_skip
        assert not require_no_partial_failures
        return type("Result", (), {"ok": False, "warnings": ["empty"], "errors": ["missing"], "output_dir": output})()

    monkeypatch.setattr(cli, "verify_project_output", fake_verify)

    exit_code = cli.main(["verify-output", "--output", str(tmp_path), "--max-unclassified-rate", "0.25"])

    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "warning: empty" in stderr
    assert "error: missing" in stderr
