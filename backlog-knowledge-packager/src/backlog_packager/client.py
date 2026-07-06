"""Read-only Backlog API client."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


class BacklogApiError(RuntimeError):
    """Raised when Backlog returns an error or retry limit is exceeded."""


class ReadOnlyBacklogClient:
    """GET/download-only Backlog API client.

    Write methods are intentionally not defined, enforcing FR-11 structurally.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        session: requests.Session | None = None,
        max_retries: int = 3,
        retry_sleep_seconds: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.retry_sleep_seconds = retry_sleep_seconds

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        response = self._request(endpoint, params=params, stream=False)
        return response.json()

    def download(self, endpoint: str, dest: Path, params: dict[str, Any] | None = None) -> Path:
        response = self._request(endpoint, params=params, stream=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    file.write(chunk)
        return dest

    def _request(self, endpoint: str, params: dict[str, Any] | None, stream: bool) -> requests.Response:
        request_params = dict(params or {})
        request_params["apiKey"] = self.api_key
        url = self._url(endpoint)
        for attempt in range(self.max_retries + 1):
            response = self.session.get(url, params=request_params, stream=stream, timeout=30)
            if response.status_code == 429 and attempt < self.max_retries:
                time.sleep(self._retry_delay(response))
                continue
            if response.ok:
                return response
            raise BacklogApiError(f"GET {_mask_api_key(response.url)} failed with status {response.status_code}")
        raise BacklogApiError(f"GET {_mask_api_key(url)} failed after retries")

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _retry_delay(self, response: requests.Response) -> float:
        reset = response.headers.get("X-RateLimit-Reset")
        if reset and reset.isdigit():
            delay = int(reset) - int(time.time())
            if delay > 0:
                return float(delay)
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return float(retry_after)
        return self.retry_sleep_seconds


def _mask_api_key(url: str) -> str:
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        query.append((key, "***" if key == "apiKey" else value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
