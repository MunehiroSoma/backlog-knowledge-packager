"""argparse entry point for the backlog-packager CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .client import BacklogApiError, ReadOnlyBacklogClient
from .classifier import classify_items, load_classification_rules
from .collector import CollectionResult
from .collector.documents import collect_documents
from .collector.shared_files import collect_shared_files
from .collector.wikis import collect_wikis
from .config import ConfigError, load_collect_config
from .generator import build_requests_url_checker, write_project_outputs
from .normalizer import normalize_collection
from .sync import load_cached_items
from .verify import verify_project_output, write_acceptance_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backlog-packager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="collect Backlog knowledge into a local project package")
    collect.add_argument("--space", help="Backlog space key. Defaults to BACKLOG_SPACE_KEY.")
    collect.add_argument("--domain", help="Backlog domain. Defaults to BACKLOG_DOMAIN or backlog.com.")
    collect.add_argument("--project", help="Backlog project key. Defaults to BACKLOG_PROJECT_KEY.")
    collect.add_argument("--targets", help="Comma-separated targets: documents,wiki,shared-files.")
    collect.add_argument("--output", help="Output directory. Defaults to ./output/{PROJECT_KEY}.")
    collect.add_argument(
        "--classification-rules",
        help="Optional JSON file with project-specific classification category and tag keywords.",
    )
    collect.add_argument("--check-urls", action="store_true", help="Check linked URLs in item bodies and include broken links in warnings.md.")
    collect.add_argument(
        "--check-source-urls",
        action="store_true",
        help="Also check Backlog source URLs. May report false positives for private spaces without browser authentication.",
    )
    collect.set_defaults(handler=run_collect)

    verify = subparsers.add_parser("verify-output", help="verify generated project package outputs")
    verify.add_argument("--output", required=True, help="Output directory to verify.")
    verify.add_argument(
        "--max-unclassified-rate",
        type=float,
        help="Fail when classification-summary.json unclassifiedRate exceeds this 0.0-1.0 threshold.",
    )
    verify.add_argument(
        "--require-cache-skip",
        action="store_true",
        help="Fail unless collection-summary.json reports at least one skippedByCache item. Use after a second collect run.",
    )
    verify.add_argument(
        "--require-no-partial-failures",
        action="store_true",
        help="Fail when metadata/partial-failures.json contains any non-fatal collection failure.",
    )
    verify.add_argument(
        "--write-report",
        action="store_true",
        help="Write metadata/acceptance-report.md with Phase 2 verification evidence.",
    )
    verify.set_defaults(handler=run_verify_output)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def run_collect(args: argparse.Namespace) -> int:
    try:
        config = load_collect_config(
            project=args.project,
            space=args.space,
            domain=args.domain,
            targets=args.targets,
            output=args.output,
        )
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 1

    try:
        category_keywords, tag_keywords = (
            load_classification_rules(args.classification_rules) if args.classification_rules else (None, None)
        )
    except (OSError, ValueError) as exc:
        print(f"classification rules error: {exc}", file=sys.stderr)
        return 1

    client = ReadOnlyBacklogClient(config.base_url, config.api_key)
    try:
        client.get("/api/v2/space")
        client.get(f"/api/v2/projects/{config.project}")
    except BacklogApiError as exc:
        print(f"api error: {exc}", file=sys.stderr)
        return 2

    cache = load_cached_items(config.output / "metadata" / "source-map.json")
    collection = _collect_targets(client, config.project, config.targets, config.output, cache)
    items = classify_items(
        normalize_collection(
            collection=collection,
            project_key=config.project,
            base_url=config.base_url,
            output_dir=config.output,
        ),
        category_keywords=category_keywords,
        tag_keywords=tag_keywords,
    )
    write_project_outputs(
        project_key=config.project,
        items=items,
        output_dir=config.output,
        raw_metadata={
            **collection.metadata,
            "collection-summary": collection.summary,
            "partial-failures": collection.failures,
        },
        url_checker=build_requests_url_checker() if args.check_urls or args.check_source_urls else None,
        check_source_urls=args.check_source_urls,
    )
    for failure in collection.failures:
        print(f"partial failure: {failure}", file=sys.stderr)
    print(f"generated project package: {config.output}", file=sys.stderr)
    return 3 if collection.failures else 0


def run_verify_output(args: argparse.Namespace) -> int:
    result = verify_project_output(
        args.output,
        max_unclassified_rate=args.max_unclassified_rate,
        require_cache_skip=args.require_cache_skip,
        require_no_partial_failures=args.require_no_partial_failures,
    )
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"error: {error}", file=sys.stderr)
    if args.write_report:
        report_path = write_acceptance_report(
            args.output,
            result,
            max_unclassified_rate=args.max_unclassified_rate,
            require_cache_skip=args.require_cache_skip,
            require_no_partial_failures=args.require_no_partial_failures,
        )
        print(f"wrote acceptance report: {report_path}", file=sys.stderr)
    if result.ok:
        print(f"verified project package: {result.output_dir}", file=sys.stderr)
        return 0
    return 1


def _collect_targets(
    client: ReadOnlyBacklogClient,
    project_key: str,
    targets: tuple[str, ...],
    output_dir,
    cache,
) -> CollectionResult:
    collection = CollectionResult()
    if "documents" in targets:
        collection.extend(collect_documents(client, project_key, cache=cache))
    if "wiki" in targets:
        collection.extend(collect_wikis(client, project_key, cache=cache))
    if "shared-files" in targets:
        collection.extend(collect_shared_files(client, project_key, output_dir=output_dir, cache=cache))
    return collection


if __name__ == "__main__":
    sys.exit(main())
