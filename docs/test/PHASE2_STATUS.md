# Phase 2 Status

This status note summarizes current implementation and verification evidence for Phase 2 issues #14 through #19.

## Summary

| Issue | Requirement | Local status | Real Backlog status |
|-------|-------------|--------------|---------------------|
| #14 | FR-15 Differential sync | Implemented and covered by CLI tests, including second-run `verify-output --require-cache-skip`. | Pending `.env` and real project execution. |
| #15 | FR-16 Advanced classification | Implemented as rule-based plus content fallback, project-specific classification rules, tags, matched keyword, confidence, source-linked diagnostics, summary metrics, and verifier checks. | Pending real project unclassified-rate review. |
| #16 | FR-17 Onboarding material generation | Implemented with reading order, team rules, and past knowledge sections with source context. | Pending real project output review. |
| #17 | FR-18 Content-derived checklist generation | Implemented for rule, setup, and operation source bodies with source-linked tasks. | Pending real project output review. |
| #18 | FR-19 Stale information detection | Implemented for stale updated dates, title/body deprecated markers, optional body URL checks, and optional source URL checks. | Pending real project warning review. |
| #19 | FR-20 Duplicate detection | Implemented for same normalized titles and similar titles with related candidates, updated timestamps, and source URLs. | Pending real project warning review. |

## Local Evidence

Latest local verification:

```bash
uv run pytest
uv build
git diff --check
```

Current result:

- `uv run pytest`: 87 passed.
- `uv build`: source distribution and wheel built successfully.
- `git diff --check`: no whitespace errors. Git reported Windows CRLF conversion warnings only.
- `metadata/acceptance-report.md`: includes a Phase 2 issue checklist for #14 through #19.

Current passing coverage includes:

- `tests/test_cli.py`: collect command wiring, project-specific classification rules, second-run differential sync, URL-check warning toggles, `verify-output` CLI options.
- `tests/test_collector.py`: non-fatal detail, directory, and download failures are recorded for partial-failure evidence.
- `tests/test_collect_e2e.py`: collect across documents, wiki, and shared files, verify generated outputs, and run a local Phase 2 acceptance flow covering differential sync, classification diagnostics, onboarding, content-derived checklist entries, stale/deprecated warnings, duplicate warnings, and acceptance-report generation.
- `tests/test_phase2_generators.py`: onboarding, content-derived checklist generation, stale/deprecated/broken-link warnings, duplicate detection, warnings in `knowledge.json`.
- `tests/test_sync.py`: source-map cache loading and updated-item filtering.
- `tests/test_verify.py`: required files, source traceability, onboarding/checklist/warnings markdown traceability, classification metrics, templates zip, collection summary, unclassified threshold, and required cache-skip acceptance.

## Real Backlog Acceptance Blocker

Real project acceptance has not been executed because neither `backlog-knowledge-packager/.env` nor a repository-root `.env` is present for this package. A separate `backlog-api-poc/.env` may exist, but it is not used for this Phase 2 acceptance flow.

Required local-only configuration:

```bash
BACKLOG_SPACE_KEY=...
BACKLOG_API_KEY=...
BACKLOG_PROJECT_KEY=...
```

`BACKLOG_DOMAIN` is optional and defaults to `backlog.com`; set it only for spaces such as `backlog.jp`.

The API key must remain in `.env` and must not be pasted into issues, PRs, logs, or generated evidence.

## Real Backlog Acceptance Command Sequence

Run from `backlog-knowledge-packager/` after `.env` is configured:

```bash
uv run backlog-packager collect --project PROJECT_KEY --targets documents,wiki,shared-files --output ./output/PROJECT_KEY
uv run backlog-packager verify-output --output ./output/PROJECT_KEY --max-unclassified-rate 0.2 --require-no-partial-failures --write-report
uv run backlog-packager collect --project PROJECT_KEY --targets documents,wiki,shared-files --output ./output/PROJECT_KEY
uv run backlog-packager verify-output --output ./output/PROJECT_KEY --max-unclassified-rate 0.2 --require-cache-skip --require-no-partial-failures --write-report
```

Use `--check-urls` only when body-link reachability checks are desired. Use `--check-source-urls` only when Backlog source URLs are reachable from this environment without browser-only authentication.

If `collect` exits with code `3`, the package was generated with partial failures. Run `verify-output` to inspect structural validity, but keep the affected target's acceptance pending until the `partial failure:` lines are reviewed and either resolved or explicitly excluded from the selected project scope.
The same non-fatal failure reasons are written to `metadata/partial-failures.json` for later evidence review.
Use `verify-output --require-no-partial-failures` for final acceptance once the selected target scope is expected to collect cleanly.

## Evidence To Attach To Issues Or PR

- Exact commands run.
- `verify-output` results and selected unclassified threshold.
- `metadata/acceptance-report.md` generated by `verify-output --write-report`.
- The Phase 2 issue checklist in `metadata/acceptance-report.md`.
- Any `partial failure:` lines from `collect` stderr.
- `metadata/partial-failures.json` when it contains entries.
- `metadata/collection-summary.json` from the second run, especially `skippedByCache`, `detailFetched`, and `downloaded`.
- `metadata/classification-summary.json`, especially `unclassifiedRate`, `averageConfidence`, `lowConfidence`, `unclassifiedItems`, and `lowConfidenceItems`.
- Relevant excerpts from `onboarding.md`, `setup-checklist.md`, and `warnings.md`.
- Any acceptance criteria that could not be exercised because the selected real project lacks matching data.
