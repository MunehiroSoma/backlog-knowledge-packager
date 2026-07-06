"""KnowledgeItem and related dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


SourceType = Literal["document", "wiki", "sharedFile", "attachment"]
Category = Literal[
    "rule",
    "template",
    "setup",
    "onboarding",
    "knowledge",
    "operation",
    "reference",
    "unclassified",
]
WarningType = Literal["stale", "deprecated_term", "broken_url", "duplicate"]


@dataclass(slots=True)
class ClassificationResult:
    """Classification metadata used by Phase 2 tuning and reporting."""

    category: Category
    matched_keyword: str | None = None
    confidence: float = 0.0
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class KnowledgeItem:
    """One source-backed unit of project knowledge."""

    id: str
    source_type: SourceType
    source_id: str
    project_key: str
    title: str
    url: str
    updated: str
    created: str | None = None
    created_user: str | None = None
    updated_user: str | None = None
    category: Category = "unclassified"
    matched_keyword: str | None = None
    classification_confidence: float = 0.0
    content_path: str | None = None
    content: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.url:
            raise ValueError("KnowledgeItem.url is required")
        if not self.updated:
            raise ValueError("KnowledgeItem.updated is required")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sourceType"] = data.pop("source_type")
        data["sourceId"] = data.pop("source_id")
        data["projectKey"] = data.pop("project_key")
        data["createdUser"] = data.pop("created_user")
        data["updatedUser"] = data.pop("updated_user")
        data["matchedKeyword"] = data.pop("matched_keyword")
        data["classificationConfidence"] = data.pop("classification_confidence")
        data["contentPath"] = data.pop("content_path")
        return data


@dataclass(slots=True)
class WarningItem:
    """A Phase 2 warning with source context for judging the canonical item."""

    type: WarningType
    message: str
    title: str
    url: str
    updated: str
    source_type: SourceType
    related: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sourceType"] = data.pop("source_type")
        return data
