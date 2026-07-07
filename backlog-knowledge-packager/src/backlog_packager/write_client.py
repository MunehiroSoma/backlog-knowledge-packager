"""Explicit write-capable Backlog API client for Phase 4 apply."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


class BacklogWriteError(RuntimeError):
    """Raised when a write API call fails."""


class ExplicitBacklogWriteClient:
    """PATCH-only client that cannot be created without explicit opt-in."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        enable_write: bool,
        session: requests.Session | None = None,
    ) -> None:
        if not enable_write:
            raise BacklogWriteError("write client requires explicit enable_write=True")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = session or requests.Session()

    def update_wiki(self, wiki_id: str, *, name: str, content: str, mail_notify: bool = False) -> Any:
        return self._patch(
            f"/api/v2/wikis/{wiki_id}",
            data={"name": name, "content": content, "mailNotify": str(mail_notify).lower()},
        )

    def _patch(self, endpoint: str, data: dict[str, Any]) -> Any:
        request_data = dict(data)
        request_data["apiKey"] = self.api_key
        url = self._url(endpoint)
        try:
            response = self.session.patch(url, data=request_data, timeout=30)
        except requests.RequestException as exc:
            safe_url = _mask_api_key(getattr(getattr(exc, "request", None), "url", None) or url)
            raise BacklogWriteError(f"PATCH {safe_url} failed: {exc.__class__.__name__}") from exc
        if not response.ok:
            raise BacklogWriteError(f"PATCH {_mask_api_key(response.url)} failed with status {response.status_code}")
        if response.content:
            return response.json()
        return {}

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"


def _mask_api_key(url: str) -> str:
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        query.append((key, "***" if key == "apiKey" else value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
