"""Apply approved local suggestions to Backlog with explicit confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .client import ReadOnlyBacklogClient
from .suggester import ReviewEntry, SuggestionError, list_reviews
from .write_client import ExplicitBacklogWriteClient


class ApplyError(ValueError):
    """Raised when approved suggestions cannot be safely applied."""


@dataclass(frozen=True, slots=True)
class ApplyAction:
    source_type: str
    source_id: str
    title: str
    url: str
    updated: str
    proposal_path: Path
    content: str


@dataclass(frozen=True, slots=True)
class ApplyResult:
    action: ApplyAction
    applied: bool
    message: str


def plan_apply(suggestions_dir: Path | str) -> list[ApplyAction]:
    suggestion_path = Path(suggestions_dir)
    entries = list_reviews(suggestion_path, "approved")
    actions: list[ApplyAction] = []
    for entry in entries:
        _validate_supported_entry(entry)
        proposal_path = _resolve_local_path(suggestion_path, entry.proposal_path)
        content = _extract_proposed_content(proposal_path)
        actions.append(
            ApplyAction(
                source_type=entry.source_type,
                source_id=entry.source_id,
                title=entry.title,
                url=entry.url,
                updated=entry.updated,
                proposal_path=proposal_path,
                content=content,
            )
        )
    return actions


def apply_approved(
    suggestions_dir: Path | str,
    *,
    confirm_apply: bool,
    read_client: ReadOnlyBacklogClient | None = None,
    write_client: ExplicitBacklogWriteClient | None = None,
    audit_log: Path | str | None = None,
) -> list[ApplyResult]:
    actions = plan_apply(suggestions_dir)
    if not confirm_apply:
        return [ApplyResult(action, False, "dry-run") for action in actions]
    if read_client is None or write_client is None:
        raise ApplyError("confirm apply requires read_client and write_client")
    results: list[ApplyResult] = []
    for action in actions:
        current = read_client.get(f"/api/v2/wikis/{action.source_id}")
        current_updated = str(current.get("updated") or "")
        if current_updated != action.updated:
            raise ApplyError(f"wiki:{action.source_id} updated mismatch; review the latest Backlog content first")
    for action in actions:
        write_client.update_wiki(action.source_id, name=action.title, content=action.content, mail_notify=False)
        results.append(ApplyResult(action, True, "applied"))
    if audit_log is not None:
        _write_audit_log(Path(audit_log), results)
    return results


def _validate_supported_entry(entry: ReviewEntry) -> None:
    if entry.status != "approved":
        raise ApplyError(f"{entry.source_type}:{entry.source_id} is not approved")
    if entry.source_type != "wiki":
        raise ApplyError(f"{entry.source_type}:{entry.source_id} cannot be applied automatically in Phase 4")
    if not entry.source_id or not entry.title or not entry.updated or not entry.proposal_path:
        raise ApplyError(f"{entry.source_type}:{entry.source_id} is missing required review fields")


def _resolve_local_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ApplyError(f"proposal path must stay inside suggestions: {value}")
    resolved = base_dir / path
    try:
        resolved.resolve().relative_to(base_dir.resolve())
    except ValueError as exc:
        raise ApplyError(f"proposal path must stay inside suggestions: {value}") from exc
    if not resolved.is_file():
        raise ApplyError(f"missing proposal file: {resolved}")
    return resolved


def _extract_proposed_content(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = "## Proposed content"
    if marker not in text:
        raise ApplyError(f"{path} is missing proposed content section")
    body = text.split(marker, 1)[1]
    if "## Note" in body:
        body = body.split("## Note", 1)[0]
    content = body.strip()
    if not content:
        raise ApplyError(f"{path} has empty proposed content")
    return content + "\n"


def _write_audit_log(path: Path, results: list[ApplyResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Apply audit {datetime.now(timezone.utc).isoformat()}", ""]
    for result in results:
        lines.append(f"- {result.message}: {result.action.source_type}:{result.action.source_id} {result.action.url}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
