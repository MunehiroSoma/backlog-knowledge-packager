"""Project output writer and templates.zip assembly."""

from __future__ import annotations

import json
import shutil
import zipfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backlog_packager.classifier import classification_summary
from backlog_packager.models import KnowledgeItem, WarningItem

from .checklist import render_setup_checklist_markdown
from .common import generated_at
from .knowledge import render_knowledge_json, render_knowledge_markdown
from .onboarding import render_onboarding_markdown
from .references import render_references_markdown
from .source_indexes import render_document_index_markdown, render_wiki_index_markdown
from .warnings import detect_warnings, render_warnings_markdown


@dataclass(frozen=True, slots=True)
class ProjectOutput:
    """Paths written for one project material pack."""

    output_dir: Path
    knowledge_md: Path
    knowledge_json: Path
    references_md: Path
    setup_checklist_md: Path
    onboarding_md: Path
    document_index_md: Path
    wiki_index_md: Path
    warnings_md: Path
    source_map_json: Path
    templates_zip: Path


def write_project_outputs(
    project_key: str,
    items: Iterable[KnowledgeItem],
    output_dir: Path,
    raw_metadata: Mapping[str, object] | None = None,
    warnings: Iterable[WarningItem] | None = None,
    url_checker: Callable[[str], bool] | None = None,
    check_source_urls: bool = False,
    now: datetime | None = None,
) -> ProjectOutput:
    """Write MVP and Phase 2 artifacts for a classified item list."""

    item_list = list(items)
    warning_list = (
        list(warnings)
        if warnings is not None
        else detect_warnings(item_list, now=now, url_checker=url_checker, check_source_urls=check_source_urls)
    )
    metadata_dir = output_dir / "metadata"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    knowledge_md = output_dir / "knowledge.md"
    knowledge_json = output_dir / "knowledge.json"
    references_md = output_dir / "references.md"
    setup_checklist_md = output_dir / "setup-checklist.md"
    onboarding_md = output_dir / "onboarding.md"
    document_index_md = output_dir / "document-index.md"
    wiki_index_md = output_dir / "wiki-index.md"
    warnings_md = output_dir / "warnings.md"
    source_map_json = metadata_dir / "source-map.json"
    templates_zip = output_dir / "templates.zip"

    _write_text(knowledge_md, render_knowledge_markdown(project_key, item_list, now))
    _write_text(knowledge_json, render_knowledge_json(project_key, item_list, warning_list, now))
    _write_text(references_md, render_references_markdown(project_key, item_list, now))
    _write_text(setup_checklist_md, render_setup_checklist_markdown(project_key, item_list, now))
    _write_text(onboarding_md, render_onboarding_markdown(project_key, item_list, now))
    _write_text(document_index_md, render_document_index_markdown(project_key, item_list, raw_metadata, now))
    _write_text(wiki_index_md, render_wiki_index_markdown(project_key, item_list, now))
    _write_text(warnings_md, render_warnings_markdown(project_key, warning_list, now))
    _write_json(source_map_json, {"projectKey": project_key, "generated": generated_at(now), "items": [i.to_dict() for i in item_list]})
    _write_json(metadata_dir / "classification-summary.json", classification_summary(item_list))
    if not raw_metadata or "collection-summary" not in raw_metadata:
        _write_json(metadata_dir / "collection-summary.json", {})
    if not raw_metadata or "partial-failures" not in raw_metadata:
        _write_json(metadata_dir / "partial-failures.json", [])

    for name, payload in (raw_metadata or {}).items():
        _write_json(metadata_dir / f"{name}.json", payload)

    write_templates_zip(
        project_key=project_key,
        items=item_list,
        output_dir=output_dir,
        zip_path=templates_zip,
        now=now,
    )

    return ProjectOutput(
        output_dir=output_dir,
        knowledge_md=knowledge_md,
        knowledge_json=knowledge_json,
        references_md=references_md,
        setup_checklist_md=setup_checklist_md,
        onboarding_md=onboarding_md,
        document_index_md=document_index_md,
        wiki_index_md=wiki_index_md,
        warnings_md=warnings_md,
        source_map_json=source_map_json,
        templates_zip=templates_zip,
    )


def write_templates_zip(
    project_key: str,
    items: Iterable[KnowledgeItem],
    output_dir: Path,
    zip_path: Path,
    now: datetime | None = None,
) -> Path:
    """Create project-package zip with rules, templates, links, and guides."""

    item_list = [item for item in items if item.category in {"rule", "template"}]
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "project-package/README.md",
            _package_readme(project_key, item_list, now),
        )
        for filename in ("references.md", "setup-checklist.md", "onboarding.md", "warnings.md"):
            source = output_dir / filename
            if source.exists():
                archive.write(source, f"project-package/{filename}")

        original_links: list[dict[str, str]] = []
        used_names: set[str] = set()
        for item in item_list:
            archive_name = _archive_name(item, used_names)
            source_path = output_dir / item.content_path if item.content_path else None
            if source_path and source_path.exists() and source_path.is_file():
                archive.write(source_path, f"project-package/{archive_name}")
            else:
                archive.writestr(f"project-package/{archive_name}", item.content or "")
            original_links.append(
                {
                    "path": archive_name,
                    "title": item.title,
                    "url": item.url,
                    "updated": item.updated,
                    "sourceType": item.source_type,
                }
            )
        archive.writestr("project-package/original-links.json", json.dumps(original_links, ensure_ascii=False, indent=2) + "\n")
    return zip_path


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _archive_name(item: KnowledgeItem, used_names: set[str]) -> str:
    folder = "rules" if item.category == "rule" else "templates"
    if item.content_path:
        candidate = f"{folder}/{Path(item.content_path).name}"
    else:
        candidate = f"{folder}/{_safe_filename(item.title)}.md"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    path = Path(candidate)
    deduped = f"{path.parent.as_posix()}/{path.stem}-{item.source_type}-{item.source_id}{path.suffix}"
    used_names.add(deduped)
    return deduped


def _safe_filename(title: str) -> str:
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in title.strip())
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "item"


def _package_readme(project_key: str, items: list[KnowledgeItem], now: datetime | None) -> str:
    return "\n".join(
        [
            f"# {project_key} project package",
            "",
            f"Generated: {generated_at(now)}",
            "",
            "This package contains source-backed project rules, templates, onboarding guides, and original links.",
            f"Bundled source items: {len(items)}",
            "",
        ]
    )


def copy_existing_file(source: Path, destination: Path) -> Path:
    """Copy a generated or downloaded file while preserving parent creation."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination
