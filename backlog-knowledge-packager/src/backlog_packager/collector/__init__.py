"""Collectors: the only layer that talks to the Backlog API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CollectionResult:
    """Raw source responses plus non-fatal collection failures."""

    documents: list[dict[str, Any]] = field(default_factory=list)
    wikis: list[dict[str, Any]] = field(default_factory=list)
    shared_files: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def extend(self, other: "CollectionResult") -> None:
        self.documents.extend(other.documents)
        self.wikis.extend(other.wikis)
        self.shared_files.extend(other.shared_files)
        self.metadata.update(other.metadata)
        self.summary.update(other.summary)
        self.failures.extend(other.failures)
