# Phase 2 Status

This status note summarizes current implementation and verification evidence for Phase 2 issues #14 through #19.

## Summary

| Issue | Requirement | Local status | Real Backlog status |
|-------|-------------|--------------|---------------------|
| #14 | FR-15 Differential sync | Implemented and covered by CLI tests, including second-run `verify-output --require-cache-skip`. | Accepted against `sus` / `IT_INFRA_CONTRACT`; second run passed `--require-cache-skip`. |
| #15 | FR-16 Advanced classification | Implemented as rule-based plus content fallback, project-specific classification rules, tags, matched keyword, confidence, source-linked diagnostics, summary metrics, and verifier checks. | Accepted against `sus` / `IT_INFRA_CONTRACT`; unclassified rate `0.052` passed threshold `0.2`. |
| #16 | FR-17 Onboarding material generation | Implemented with reading order, team rules, and past knowledge sections with source context. | Accepted by generated `onboarding.md` verifier checks. |
| #17 | FR-18 Content-derived checklist generation | Implemented for rule, setup, and operation source bodies with source-linked tasks. | Accepted by generated `setup-checklist.md` verifier checks. |
| #18 | FR-19 Stale information detection | Implemented for stale updated dates, title/body deprecated markers, optional body URL checks, and optional source URL checks. | Accepted by generated `warnings.md`; real run produced stale and deprecated-term warnings. |
| #19 | FR-20 Duplicate detection | Implemented for same normalized titles and similar titles with related candidates, updated timestamps, and source URLs. | Accepted by generated `warnings.md`; real run produced duplicate warnings. |

## Local Evidence

Latest local verification:

```bash
uv run pytest
uv build
git diff --check
```

Current result:

- `uv run pytest`: 94 passed.
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

## Real Backlog Acceptance Evidence

Real project acceptance was executed against:

```bash
BACKLOG_SPACE_KEY=sus
BACKLOG_PROJECT_KEY=IT_INFRA_CONTRACT
BACKLOG_DOMAIN=backlog.com
```

The API key remained in `backlog-knowledge-packager/.env` and was not committed.

Because the project shared-file tree is very large, real acceptance used metadata-only shared-file collection with `--skip-shared-file-downloads`. Shared-file source URLs and updated timestamps were still included, but file bodies were not downloaded or bundled.

Commands run from `backlog-knowledge-packager/`:

```bash
uv run backlog-packager collect --targets documents,wiki,shared-files --skip-shared-file-downloads --output ./output/phase2-e2e-sus-meta2
uv run backlog-packager verify-output --output ./output/phase2-e2e-sus-meta2 --max-unclassified-rate 0.2 --require-no-partial-failures --write-report
uv run backlog-packager collect --targets documents,wiki,shared-files --skip-shared-file-downloads --output ./output/phase2-e2e-sus-meta2
uv run backlog-packager verify-output --output ./output/phase2-e2e-sus-meta2 --max-unclassified-rate 0.2 --require-cache-skip --require-no-partial-failures --write-report
```

Results:

- First `collect`: exit code `0`.
- First `verify-output`: exit code `0`.
- Second `collect`: exit code `0`.
- Second `verify-output`: exit code `0`.
- Source items: `4909`.
- Classification counts: `reference=4253`, `unclassified=256`, `operation=141`, `template=90`, `setup=72`, `rule=59`, `knowledge=35`, `onboarding=3`.
- Unclassified rate: `0.05214911387247912`.
- Average confidence: `0.5103075982888572`.
- Partial failures: `0`.
- Collection summary after second run: documents `listed=290`, `detailFetched=11`, `skippedByCache=279`; wiki `listed=119`, `detailFetched=0`, `skippedByCache=119`; shared files `listed=5725`, `files=4511`, `downloaded=0`.
- Warning counts: `stale=1987`, `duplicate=410`, `deprecated_term=48`.

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
