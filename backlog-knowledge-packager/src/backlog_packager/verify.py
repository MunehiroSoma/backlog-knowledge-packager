"""Verify generated project package outputs."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "knowledge.md",
    "knowledge.json",
    "references.md",
    "setup-checklist.md",
    "onboarding.md",
    "warnings.md",
    "templates.zip",
    "metadata/source-map.json",
    "metadata/classification-summary.json",
    "metadata/collection-summary.json",
    "metadata/partial-failures.json",
)


@dataclass(slots=True)
class VerificationResult:
    output_dir: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def verify_project_output(
    output_dir: Path | str,
    max_unclassified_rate: float | None = None,
    require_cache_skip: bool = False,
    require_no_partial_failures: bool = False,
) -> VerificationResult:
    output_path = Path(output_dir)
    result = VerificationResult(output_dir=output_path)
    _check_required_files(output_path, result)
    source_items = _check_source_map(output_path, result)
    knowledge_items, knowledge_warnings = _check_knowledge_json(output_path, result)
    summary = _check_classification_summary(output_path, result)
    _check_unclassified_rate(summary, max_unclassified_rate, result)
    _check_collection_summary(output_path, result, require_cache_skip=require_cache_skip)
    _check_partial_failures(output_path, result, require_no_partial_failures=require_no_partial_failures)
    _check_item_consistency(source_items, knowledge_items, summary, result)
    _check_classification_diagnostics(source_items, summary, result)
    _check_content_paths(output_path, source_items, knowledge_items, result)
    _check_markdown_traceability(output_path, source_items, knowledge_warnings, result)
    _check_templates_zip(output_path, source_items, result)
    return result


def write_acceptance_report(
    output_dir: Path | str,
    result: VerificationResult,
    max_unclassified_rate: float | None = None,
    require_cache_skip: bool = False,
    require_no_partial_failures: bool = False,
) -> Path:
    """Write a concise Phase 2 acceptance evidence report from generated metadata."""

    output_path = Path(output_dir)
    metadata_dir = output_path / "metadata"
    report_path = metadata_dir / "acceptance-report.md"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    source_map = _load_json(output_path / "metadata" / "source-map.json", {})
    classification = _load_json(output_path / "metadata" / "classification-summary.json", {})
    collection = _load_json(output_path / "metadata" / "collection-summary.json", {})
    partial_failures = _load_json(output_path / "metadata" / "partial-failures.json", [])
    knowledge = _load_json(output_path / "knowledge.json", {})
    warnings = knowledge.get("warnings", []) if isinstance(knowledge, dict) else []
    source_items = source_map.get("items", []) if isinstance(source_map, dict) else []

    lines = [
        "# Phase 2 acceptance report",
        "",
        f"- Output: `{output_path}`",
        f"- Verification: {'PASS' if result.ok else 'FAIL'}",
        f"- Source items: {len(source_items) if isinstance(source_items, list) else 0}",
        f"- Warnings: {len(warnings) if isinstance(warnings, list) else 0}",
        f"- Partial failures: {len(partial_failures) if isinstance(partial_failures, list) else 'invalid'}",
        f"- Max unclassified rate: {_format_threshold(max_unclassified_rate)}",
        f"- Require cache skip: {require_cache_skip}",
        f"- Require no partial failures: {require_no_partial_failures}",
        "",
        "## Verification messages",
        "",
    ]
    if result.errors:
        lines.extend(f"- ERROR: {error}" for error in result.errors)
    if result.warnings:
        lines.extend(f"- WARNING: {warning}" for warning in result.warnings)
    if not result.errors and not result.warnings:
        lines.append("- No verifier errors or warnings.")

    lines.extend(
        [
            "",
            "## Phase 2 issue checklist",
            "",
            "- #14 / FR-15 Differential sync: review collection-summary skippedByCache and detail/download counters.",
            "- #15 / FR-16 Advanced classification: review classification-summary unclassifiedRate and diagnostics.",
            "- #16 / FR-17 Onboarding: review onboarding.md source-linked reading order, team rules, and past knowledge.",
            "- #17 / FR-18 Checklist: review setup-checklist.md source-linked content-derived tasks.",
            "- #18 / FR-19 Stale or broken information: review warnings.md stale, deprecated_term, and broken_url entries.",
            "- #19 / FR-20 Duplicates: review warnings.md duplicate entries.",
        ]
    )

    lines.extend(["", "## Classification", ""])
    if isinstance(classification, dict):
        lines.extend(
            [
                f"- Total: {classification.get('total', 'n/a')}",
                f"- Counts: `{json.dumps(classification.get('counts', {}), ensure_ascii=False, sort_keys=True)}`",
                f"- Unclassified rate: {classification.get('unclassifiedRate', 'n/a')}",
                f"- Average confidence: {classification.get('averageConfidence', 'n/a')}",
                f"- Low confidence: {classification.get('lowConfidence', 'n/a')}",
                f"- Unclassified diagnostics: {len(classification.get('unclassifiedItems', [])) if isinstance(classification.get('unclassifiedItems', []), list) else 'invalid'}",
                f"- Low-confidence diagnostics: {len(classification.get('lowConfidenceItems', [])) if isinstance(classification.get('lowConfidenceItems', []), list) else 'invalid'}",
            ]
        )
    else:
        lines.append("- classification-summary.json could not be read.")

    lines.extend(["", "## Collection", ""])
    if isinstance(collection, dict) and collection:
        for section, values in sorted(collection.items()):
            lines.append(f"- {section}: `{json.dumps(values, ensure_ascii=False, sort_keys=True)}`")
    else:
        lines.append("- No collection-summary entries.")

    lines.extend(["", "## Warning types", ""])
    warning_counts = _warning_type_counts(warnings)
    if warning_counts:
        for warning_type, count in sorted(warning_counts.items()):
            lines.append(f"- {warning_type}: {count}")
    else:
        lines.append("- No warning entries.")

    lines.extend(["", "## Partial failures", ""])
    if isinstance(partial_failures, list) and partial_failures:
        lines.extend(f"- {failure}" for failure in partial_failures)
    elif isinstance(partial_failures, list):
        lines.append("- None.")
    else:
        lines.append("- partial-failures.json could not be read as an array.")

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path


def _check_required_files(output_dir: Path, result: VerificationResult) -> None:
    for relative in REQUIRED_FILES:
        path = output_dir / relative
        if not path.exists():
            result.errors.append(f"missing required output: {relative}")


def _check_source_map(output_dir: Path, result: VerificationResult) -> list[dict[str, Any]]:
    payload = _read_json(output_dir / "metadata" / "source-map.json", result)
    if not isinstance(payload, dict):
        result.errors.append("metadata/source-map.json must be a JSON object")
        return []
    items = payload.get("items")
    if not isinstance(items, list):
        result.errors.append("metadata/source-map.json must contain an items array")
        return []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            result.errors.append(f"source-map item {index} must be an object")
            continue
        for key in ("url", "updated", "sourceType", "sourceId", "title", "category"):
            if not item.get(key):
                result.errors.append(f"source-map item {index} is missing {key}")
        confidence = item.get("classificationConfidence")
        if not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
            result.errors.append(f"source-map item {index} classificationConfidence must be between 0 and 1")
    if not items:
        result.warnings.append("source-map contains no items")
    return [item for item in items if isinstance(item, dict)]


def _check_knowledge_json(output_dir: Path, result: VerificationResult) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = _read_json(output_dir / "knowledge.json", result)
    if not isinstance(payload, dict):
        result.errors.append("knowledge.json must be a JSON object")
        return [], []
    items = payload.get("items")
    if not isinstance(items, list):
        result.errors.append("knowledge.json must contain an items array")
        items = []
    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        result.errors.append("knowledge.json must contain a warnings array")
        warnings = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            result.errors.append(f"knowledge.json item {index} must be an object")
            continue
        for key in ("url", "updated", "sourceType", "sourceId", "title", "category"):
            if not item.get(key):
                result.errors.append(f"knowledge.json item {index} is missing {key}")
        confidence = item.get("classificationConfidence")
        if not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
            result.errors.append(f"knowledge.json item {index} classificationConfidence must be between 0 and 1")
    for index, warning in enumerate(warnings):
        if not isinstance(warning, dict):
            result.errors.append(f"knowledge.json warning {index} must be an object")
            continue
        for key in ("type", "message", "title", "url", "updated", "sourceType"):
            if not warning.get(key):
                result.errors.append(f"knowledge.json warning {index} is missing {key}")
        related = warning.get("related", [])
        if not isinstance(related, list):
            result.errors.append(f"knowledge.json warning {index} related must be an array")
            continue
        for related_index, candidate in enumerate(related):
            if not isinstance(candidate, dict):
                result.errors.append(f"knowledge.json warning {index} related item {related_index} must be an object")
                continue
            for key in ("title", "url", "updated", "sourceType"):
                if not candidate.get(key):
                    result.errors.append(f"knowledge.json warning {index} related item {related_index} is missing {key}")
    return [item for item in items if isinstance(item, dict)], [warning for warning in warnings if isinstance(warning, dict)]


def _check_classification_summary(output_dir: Path, result: VerificationResult) -> dict[str, Any]:
    payload = _read_json(output_dir / "metadata" / "classification-summary.json", result)
    if not isinstance(payload, dict):
        result.errors.append("metadata/classification-summary.json must be a JSON object")
        return {}
    for key in (
        "total",
        "counts",
        "unclassified",
        "unclassifiedRate",
        "averageConfidence",
        "lowConfidence",
        "tagCounts",
        "unclassifiedItems",
        "lowConfidenceItems",
    ):
        if key not in payload:
            result.errors.append(f"classification-summary.json is missing {key}")
    average_confidence = payload.get("averageConfidence")
    if "averageConfidence" in payload and (not isinstance(average_confidence, int | float) or not 0 <= average_confidence <= 1):
        result.errors.append("classification-summary averageConfidence must be between 0 and 1")
    low_confidence = payload.get("lowConfidence")
    if "lowConfidence" in payload and (not isinstance(low_confidence, int) or low_confidence < 0):
        result.errors.append("classification-summary lowConfidence must be a non-negative integer")
    return payload


def _check_unclassified_rate(
    summary: dict[str, Any],
    max_unclassified_rate: float | None,
    result: VerificationResult,
) -> None:
    if max_unclassified_rate is None:
        return
    if not 0 <= max_unclassified_rate <= 1:
        result.errors.append("max unclassified rate must be between 0 and 1")
        return
    rate = summary.get("unclassifiedRate")
    if not isinstance(rate, int | float):
        result.errors.append("classification-summary unclassifiedRate must be numeric")
        return
    if float(rate) > max_unclassified_rate:
        result.errors.append(f"unclassified rate {rate:.3f} exceeds threshold {max_unclassified_rate:.3f}")


def _check_collection_summary(output_dir: Path, result: VerificationResult, require_cache_skip: bool = False) -> None:
    payload = _read_json(output_dir / "metadata" / "collection-summary.json", result)
    if not isinstance(payload, dict):
        result.errors.append("metadata/collection-summary.json must be a JSON object")
        return
    total_skipped = 0
    expected = {
        "documents": ("listed", "detailFetched", "skippedByCache"),
        "wiki": ("listed", "detailFetched", "skippedByCache"),
        "shared-files": ("listed", "files", "downloaded", "skippedByCache"),
    }
    for section, keys in expected.items():
        if section not in payload:
            continue
        section_value = payload[section]
        if not isinstance(section_value, dict):
            result.errors.append(f"collection-summary {section} must be an object")
            continue
        for key in keys:
            value = section_value.get(key)
            if not isinstance(value, int) or value < 0:
                result.errors.append(f"collection-summary {section}.{key} must be a non-negative integer")
        if isinstance(section_value.get("skippedByCache"), int):
            total_skipped += section_value["skippedByCache"]
        if section in {"documents", "wiki"} and _has_ints(section_value, "detailFetched", "skippedByCache", "listed"):
            if section_value["detailFetched"] + section_value["skippedByCache"] > section_value["listed"]:
                result.errors.append(f"collection-summary {section} fetched+skipped exceeds listed")
        if section == "shared-files" and _has_ints(section_value, "downloaded", "skippedByCache", "files"):
            if section_value["downloaded"] + section_value["skippedByCache"] > section_value["files"]:
                result.errors.append("collection-summary shared-files downloaded+skipped exceeds files")
    if require_cache_skip and total_skipped == 0:
        result.errors.append("collection-summary has no skippedByCache items; differential sync was not exercised")


def _check_partial_failures(
    output_dir: Path,
    result: VerificationResult,
    require_no_partial_failures: bool = False,
) -> None:
    payload = _read_json(output_dir / "metadata" / "partial-failures.json", result)
    if not isinstance(payload, list):
        result.errors.append("metadata/partial-failures.json must be an array")
        return
    for index, failure in enumerate(payload):
        if not isinstance(failure, str) or not failure.strip():
            result.errors.append(f"partial-failures item {index} must be a non-empty string")
    if require_no_partial_failures and payload:
        result.errors.append(f"partial-failures contains {len(payload)} entries")


def _check_item_consistency(
    source_items: list[dict[str, Any]],
    knowledge_items: list[dict[str, Any]],
    summary: dict[str, Any],
    result: VerificationResult,
) -> None:
    source_ids = {_item_key(item) for item in source_items}
    knowledge_ids = {_item_key(item) for item in knowledge_items}
    if source_ids != knowledge_ids:
        missing_in_knowledge = sorted(source_ids - knowledge_ids)
        missing_in_source_map = sorted(knowledge_ids - source_ids)
        if missing_in_knowledge:
            result.errors.append(f"knowledge.json is missing source-map items: {', '.join(missing_in_knowledge)}")
        if missing_in_source_map:
            result.errors.append(f"source-map is missing knowledge.json items: {', '.join(missing_in_source_map)}")
    source_by_id = {_item_key(item): item for item in source_items}
    for item in knowledge_items:
        source_item = source_by_id.get(_item_key(item))
        if not source_item:
            continue
        if item.get("category") != source_item.get("category"):
            result.errors.append(f"knowledge.json category does not match source-map for {_item_key(item)}")
        source_confidence = source_item.get("classificationConfidence")
        knowledge_confidence = item.get("classificationConfidence")
        if isinstance(source_confidence, int | float) and isinstance(knowledge_confidence, int | float):
            if not _nearly_equal(float(source_confidence), float(knowledge_confidence)):
                result.errors.append(f"knowledge.json classificationConfidence does not match source-map for {_item_key(item)}")

    total = summary.get("total")
    if isinstance(total, int) and total != len(source_items):
        result.errors.append(f"classification-summary total {total} does not match source-map item count {len(source_items)}")
    counts = summary.get("counts")
    source_counts: dict[str, int] = {}
    if isinstance(counts, dict):
        counted_total = sum(value for value in counts.values() if isinstance(value, int))
        if counted_total != len(source_items):
            result.errors.append(f"classification-summary counts total {counted_total} does not match source-map item count {len(source_items)}")
        for item in source_items:
            category = str(item.get("category") or "unclassified")
            source_counts[category] = source_counts.get(category, 0) + 1
        for category, count in source_counts.items():
            if counts.get(category) != count:
                result.errors.append(f"classification-summary count for {category} does not match source-map")

    unclassified = summary.get("unclassified")
    source_unclassified = source_counts.get("unclassified", 0)
    if isinstance(unclassified, int) and unclassified != source_unclassified:
        result.errors.append("classification-summary unclassified does not match source-map")
    unclassified_rate = summary.get("unclassifiedRate")
    expected_unclassified_rate = (source_unclassified / len(source_items)) if source_items else 0.0
    if isinstance(unclassified_rate, int | float) and not _nearly_equal(float(unclassified_rate), expected_unclassified_rate):
        result.errors.append("classification-summary unclassifiedRate does not match source-map")

    confidences = [float(item.get("classificationConfidence", 0.0)) for item in source_items if isinstance(item.get("classificationConfidence"), int | float)]
    expected_average = (sum(confidences) / len(source_items)) if source_items else 0.0
    average_confidence = summary.get("averageConfidence")
    if isinstance(average_confidence, int | float) and not _nearly_equal(float(average_confidence), expected_average):
        result.errors.append("classification-summary averageConfidence does not match source-map")
    low_confidence = summary.get("lowConfidence")
    expected_low_confidence = sum(1 for confidence in confidences if confidence < 0.5)
    if isinstance(low_confidence, int) and low_confidence != expected_low_confidence:
        result.errors.append("classification-summary lowConfidence does not match source-map")


def _check_classification_diagnostics(
    source_items: list[dict[str, Any]],
    summary: dict[str, Any],
    result: VerificationResult,
) -> None:
    source_keys = {_item_key(item) for item in source_items}
    for field in ("unclassifiedItems", "lowConfidenceItems"):
        diagnostics = summary.get(field, [])
        if not isinstance(diagnostics, list):
            result.errors.append(f"classification-summary {field} must be an array")
            continue
        for index, item in enumerate(diagnostics):
            if not isinstance(item, dict):
                result.errors.append(f"classification-summary {field} item {index} must be an object")
                continue
            for key in ("sourceType", "sourceId", "title", "url", "updated", "category", "classificationConfidence"):
                if key not in item or item.get(key) in (None, ""):
                    result.errors.append(f"classification-summary {field} item {index} is missing {key}")
            confidence = item.get("classificationConfidence")
            if isinstance(confidence, int | float) and not 0 <= confidence <= 1:
                result.errors.append(f"classification-summary {field} item {index} classificationConfidence must be between 0 and 1")
            if _item_key(item) not in source_keys:
                result.errors.append(f"classification-summary {field} item {index} is not present in source-map")


def _item_key(item: dict[str, Any]) -> str:
    return f"{item.get('sourceType')}:{item.get('sourceId')}"


def _nearly_equal(left: float, right: float) -> bool:
    return abs(left - right) < 0.000001


def _check_content_paths(
    output_dir: Path,
    source_items: list[dict[str, Any]],
    knowledge_items: list[dict[str, Any]],
    result: VerificationResult,
) -> None:
    for collection_name, items in (("source-map", source_items), ("knowledge.json", knowledge_items)):
        for index, item in enumerate(items):
            content_path = item.get("contentPath")
            if not content_path:
                continue
            if not isinstance(content_path, str):
                result.errors.append(f"{collection_name} item {index} contentPath must be a string")
                continue
            path = Path(content_path)
            if path.is_absolute() or ".." in path.parts:
                result.errors.append(f"{collection_name} item {index} contentPath must be relative inside output")
                continue
            resolved = (output_dir / path).resolve()
            try:
                resolved.relative_to(output_dir.resolve())
            except ValueError:
                result.errors.append(f"{collection_name} item {index} contentPath escapes output")
                continue
            if not resolved.is_file():
                result.errors.append(f"{collection_name} item {index} contentPath does not exist: {content_path}")


def _check_markdown_traceability(
    output_dir: Path,
    source_items: list[dict[str, Any]],
    knowledge_warnings: list[dict[str, Any]],
    result: VerificationResult,
) -> None:
    knowledge_md = _read_text(output_dir / "knowledge.md", result)
    if knowledge_md is not None:
        for index, item in enumerate(source_items):
            for key in ("url", "updated"):
                value = item.get(key)
                if value and str(value) not in knowledge_md:
                    result.errors.append(f"knowledge.md is missing {key} for source-map item {index}")

    onboarding_md = _read_text(output_dir / "onboarding.md", result)
    if onboarding_md is not None:
        _check_markdown_sources(
            onboarding_md,
            source_items,
            result,
            filename="onboarding.md",
            categories={"onboarding", "rule", "setup", "operation", "knowledge", "reference"},
        )

    setup_checklist_md = _read_text(output_dir / "setup-checklist.md", result)
    if setup_checklist_md is not None:
        _check_markdown_sources(
            setup_checklist_md,
            source_items,
            result,
            filename="setup-checklist.md",
            categories={"rule", "template", "setup", "operation"},
        )

    warnings_md = _read_text(output_dir / "warnings.md", result)
    if warnings_md is not None:
        if knowledge_warnings and "No warnings." in warnings_md:
            result.errors.append("warnings.md says no warnings despite knowledge.json warnings")
        if not knowledge_warnings and "No warnings." not in warnings_md:
            result.errors.append("warnings.md is missing the no-warnings marker")
        for index, warning in enumerate(knowledge_warnings):
            for key in ("type", "message", "title", "url", "updated"):
                value = warning.get(key)
                if value and str(value) not in warnings_md:
                    result.errors.append(f"warnings.md is missing {key} for knowledge.json warning {index}")
            related = warning.get("related", [])
            if not isinstance(related, list):
                continue
            for related_index, candidate in enumerate(related):
                if not isinstance(candidate, dict):
                    continue
                for key in ("title", "url", "updated"):
                    value = candidate.get(key)
                    if value and str(value) not in warnings_md:
                        result.errors.append(
                            f"warnings.md is missing {key} for knowledge.json warning {index} related item {related_index}"
                        )


def _check_markdown_sources(
    content: str,
    source_items: list[dict[str, Any]],
    result: VerificationResult,
    filename: str,
    categories: set[str],
) -> None:
    for index, item in enumerate(source_items):
        if item.get("category") not in categories:
            continue
        for key in ("url", "updated"):
            value = item.get(key)
            if value and str(value) not in content:
                result.errors.append(f"{filename} is missing {key} for source-map item {index}")


def _has_ints(value: dict[str, Any], *keys: str) -> bool:
    return all(isinstance(value.get(key), int) for key in keys)


def _check_templates_zip(output_dir: Path, source_items: list[dict[str, Any]], result: VerificationResult) -> None:
    zip_path = output_dir / "templates.zip"
    if not zip_path.exists():
        return
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            for required in (
                "project-package/README.md",
                "project-package/references.md",
                "project-package/setup-checklist.md",
                "project-package/onboarding.md",
                "project-package/warnings.md",
                "project-package/original-links.json",
            ):
                if required not in names:
                    result.errors.append(f"templates.zip is missing {required}")
            original_links = json.loads(archive.read("project-package/original-links.json").decode("utf-8"))
            if not isinstance(original_links, list):
                result.errors.append("original-links.json must be an array")
                original_links = []
            expected_bundled = [item for item in source_items if item.get("category") in {"rule", "template"}]
            if expected_bundled and not original_links:
                result.errors.append("original-links.json is empty despite bundled rule/template items")
            if isinstance(original_links, list) and len(original_links) != len(expected_bundled):
                result.errors.append(
                    f"original-links.json item count {len(original_links)} does not match bundled rule/template count {len(expected_bundled)}"
                )
            for index, link in enumerate(original_links if isinstance(original_links, list) else []):
                if not isinstance(link, dict):
                    result.errors.append(f"original-links item {index} must be an object")
                    continue
                for key in ("path", "title", "url", "updated", "sourceType"):
                    if not link.get(key):
                        result.errors.append(f"original-links item {index} is missing {key}")
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        result.errors.append(f"templates.zip is invalid: {exc}")


def _read_json(path: Path, result: VerificationResult) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"{path.relative_to(result.output_dir)} is invalid JSON: {exc}")
        return None


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _warning_type_counts(warnings: Any) -> dict[str, int]:
    if not isinstance(warnings, list):
        return {}
    counts: dict[str, int] = {}
    for warning in warnings:
        if isinstance(warning, dict) and warning.get("type"):
            warning_type = str(warning["type"])
            counts[warning_type] = counts.get(warning_type, 0) + 1
    return counts


def _format_threshold(value: float | None) -> str:
    return "not set" if value is None else f"{value:.3f}"


def _read_text(path: Path, result: VerificationResult) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"{path.relative_to(result.output_dir)} could not be read: {exc}")
        return None
