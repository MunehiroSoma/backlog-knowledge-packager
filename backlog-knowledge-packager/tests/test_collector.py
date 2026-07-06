from backlog_packager.client import BacklogApiError
from backlog_packager.collector.documents import collect_documents
from backlog_packager.collector.shared_files import collect_shared_files
from backlog_packager.collector.wikis import collect_wikis


class FakeClient:
    def __init__(self):
        self.calls = []
        self.downloads = []

    def get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        if endpoint == "/api/v2/documents":
            return [{"id": "1", "title": "doc", "updated": "2026-07-01T00:00:00Z"}]
        if endpoint == "/api/v2/documents/1":
            return {"id": "1", "title": "doc", "plain": "body", "updated": "2026-07-01T00:00:00Z"}
        if endpoint == "/api/v2/wikis":
            return [{"id": 2, "name": "wiki", "updated": "2026-07-01T00:00:00Z"}]
        if endpoint == "/api/v2/wikis/2":
            return {"id": 2, "name": "wiki", "content": "body", "updated": "2026-07-01T00:00:00Z"}
        if endpoint.startswith("/api/v2/projects/DEMO/files/metadata/"):
            return [{"id": 3, "type": "file", "dir": "/", "name": "template.md", "updated": "2026-07-01T00:00:00Z"}]
        return {}

    def download(self, endpoint, dest, params=None):
        self.downloads.append((endpoint, dest))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("file", encoding="utf-8")
        return dest


def test_collect_documents_fetches_list_and_changed_details() -> None:
    client = FakeClient()

    result = collect_documents(client, "DEMO")

    assert result.documents[0]["plain"] == "body"
    assert ("/api/v2/documents/1", None) in client.calls
    assert result.summary["documents"]["listed"] == 1
    assert result.summary["documents"]["detailFetched"] == 1


def test_collect_documents_records_detail_failure() -> None:
    class DetailFailureClient(FakeClient):
        def get(self, endpoint, params=None):
            if endpoint == "/api/v2/documents/1":
                raise BacklogApiError("GET https://space.backlog.com/api/v2/documents/1 failed with status 404")
            return super().get(endpoint, params)

    result = collect_documents(DetailFailureClient(), "DEMO")

    assert result.documents[0]["title"] == "doc"
    assert result.summary["documents"]["detailFetched"] == 0
    assert result.failures == [
        "document detail skipped: 1: GET https://space.backlog.com/api/v2/documents/1 failed with status 404"
    ]


def test_collect_documents_records_list_failure() -> None:
    class ListFailureClient(FakeClient):
        def get(self, endpoint, params=None):
            if endpoint == "/api/v2/documents":
                raise BacklogApiError("GET https://space.backlog.com/api/v2/documents failed with status 400")
            return super().get(endpoint, params)

    result = collect_documents(ListFailureClient(), "123")

    assert result.documents == []
    assert result.summary["documents"]["listed"] == 0
    assert result.failures == ["documents skipped: GET https://space.backlog.com/api/v2/documents failed with status 400"]


def test_collect_wikis_fetches_details() -> None:
    client = FakeClient()

    result = collect_wikis(client, "DEMO")

    assert result.wikis[0]["content"] == "body"
    assert ("/api/v2/wikis/2", None) in client.calls
    assert result.summary["wiki"]["listed"] == 1
    assert result.summary["wiki"]["detailFetched"] == 1


def test_collect_wikis_records_detail_failure() -> None:
    class DetailFailureClient(FakeClient):
        def get(self, endpoint, params=None):
            if endpoint == "/api/v2/wikis/2":
                raise BacklogApiError("GET https://space.backlog.com/api/v2/wikis/2 failed with status 404")
            return super().get(endpoint, params)

    result = collect_wikis(DetailFailureClient(), "DEMO")

    assert result.wikis[0]["name"] == "wiki"
    assert result.summary["wiki"]["detailFetched"] == 0
    assert result.failures == ["wiki detail skipped: 2: GET https://space.backlog.com/api/v2/wikis/2 failed with status 404"]


def test_collect_shared_files_downloads_changed_files(tmp_path) -> None:
    client = FakeClient()

    result = collect_shared_files(client, "DEMO", tmp_path)

    assert result.shared_files[0]["contentPath"] == "files/shared/template.md"
    assert client.downloads[0][0] == "/api/v2/projects/DEMO/files/3"
    assert result.summary["shared-files"]["downloaded"] == 1


def test_collect_shared_files_records_directory_failure(tmp_path) -> None:
    class DirectoryFailureClient(FakeClient):
        def get(self, endpoint, params=None):
            if endpoint.startswith("/api/v2/projects/DEMO/files/metadata/"):
                raise BacklogApiError("GET https://space.backlog.com/api/v2/files failed with status 403")
            return super().get(endpoint, params)

    result = collect_shared_files(DirectoryFailureClient(), "DEMO", tmp_path)

    assert result.shared_files == []
    assert result.summary["shared-files"]["listed"] == 0
    assert result.failures == ["shared file directory skipped: /: GET https://space.backlog.com/api/v2/files failed with status 403"]


def test_collect_shared_files_visits_each_directory_once(tmp_path) -> None:
    class DuplicateDirectoryClient(FakeClient):
        def get(self, endpoint, params=None):
            self.calls.append((endpoint, params))
            if endpoint.endswith("/files/metadata/"):
                return [{"id": 1, "type": "directory", "dir": "/", "name": "docs"}]
            if endpoint.endswith("/files/metadata/docs"):
                return [{"id": 2, "type": "directory", "dir": "/", "name": "docs"}]
            return []

    client = DuplicateDirectoryClient()

    result = collect_shared_files(client, "DEMO", tmp_path)

    assert result.summary["shared-files"]["listed"] == 2
    assert [call[0] for call in client.calls].count("/api/v2/projects/DEMO/files/metadata/docs") == 1


def test_collect_shared_files_records_download_failure(tmp_path) -> None:
    class DownloadFailureClient(FakeClient):
        def download(self, endpoint, dest, params=None):
            raise BacklogApiError("GET https://space.backlog.com/api/v2/files/3 failed with status 404")

    result = collect_shared_files(DownloadFailureClient(), "DEMO", tmp_path)

    assert "contentPath" not in result.shared_files[0]
    assert result.summary["shared-files"]["downloaded"] == 0
    assert result.failures == [
        "shared file download skipped: 3: GET https://space.backlog.com/api/v2/files/3 failed with status 404"
    ]
