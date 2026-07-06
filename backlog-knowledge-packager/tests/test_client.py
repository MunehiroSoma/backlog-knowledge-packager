from __future__ import annotations

import pytest
import requests

from backlog_packager.client import BacklogApiError, ReadOnlyBacklogClient, _mask_api_key


class FakeResponse:
    def __init__(self, status_code: int, payload=None, url="https://example/api?apiKey=secret", chunks=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.url = url
        self.headers = {}
        self._chunks = chunks or [b"data"]

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload

    def iter_content(self, chunk_size: int):
        yield from self._chunks


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, stream=False, timeout=None):
        self.calls.append({"url": url, "params": params, "stream": stream, "timeout": timeout})
        return self.responses.pop(0)


class FailingSession:
    def get(self, url, params=None, stream=False, timeout=None):
        request = requests.Request("GET", url, params=params).prepare()
        raise requests.exceptions.SSLError("certificate failed", request=request)


def test_get_adds_api_key_and_returns_json() -> None:
    session = FakeSession([FakeResponse(200, {"ok": True})])
    client = ReadOnlyBacklogClient("https://space.backlog.com", "secret", session=session)

    assert client.get("/api/v2/space") == {"ok": True}
    assert session.calls[0]["url"] == "https://space.backlog.com/api/v2/space"
    assert session.calls[0]["params"]["apiKey"] == "secret"


def test_download_writes_file(tmp_path) -> None:
    session = FakeSession([FakeResponse(200, chunks=[b"a", b"b"])])
    client = ReadOnlyBacklogClient("https://space.backlog.com", "secret", session=session)

    dest = client.download("/api/v2/file", tmp_path / "file.bin")

    assert dest.read_bytes() == b"ab"
    assert session.calls[0]["stream"] is True


def test_error_masks_api_key() -> None:
    session = FakeSession([FakeResponse(403, url="https://space.backlog.com/api?apiKey=secret&x=1")])
    client = ReadOnlyBacklogClient("https://space.backlog.com", "secret", session=session)

    with pytest.raises(BacklogApiError) as exc_info:
        client.get("/api")

    assert "secret" not in str(exc_info.value)
    assert "apiKey=%2A%2A%2A" in str(exc_info.value)


def test_request_exception_masks_api_key() -> None:
    client = ReadOnlyBacklogClient("https://space.backlog.com", "secret", session=FailingSession())

    with pytest.raises(BacklogApiError) as exc_info:
        client.get("/api")

    assert "secret" not in str(exc_info.value)
    assert "apiKey=%2A%2A%2A" in str(exc_info.value)
    assert "SSLError" in str(exc_info.value)


def test_client_has_no_write_methods() -> None:
    client = ReadOnlyBacklogClient("https://space.backlog.com", "secret", session=FakeSession([]))

    for method in ("post", "put", "patch", "delete"):
        assert not hasattr(client, method)


def test_mask_api_key_preserves_other_query_params() -> None:
    assert _mask_api_key("https://example.test/api?apiKey=secret&foo=bar") == "https://example.test/api?apiKey=%2A%2A%2A&foo=bar"
