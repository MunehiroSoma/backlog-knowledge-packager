# TC_phase2: Phase 2 Acceptance

This checklist verifies the Phase 2 scope from FR-15 through FR-20 against a real Backlog project package.
See [`PHASE2_STATUS.md`](./PHASE2_STATUS.md) for the current implementation and acceptance status.

## Scope

| Issue | Requirement | Acceptance evidence |
|-------|-------------|---------------------|
| #14 | FR-15 Differential sync | A second `collect` run skips unchanged item detail fetches or downloads while still producing a complete package. |
| #15 | FR-16 Advanced classification | `metadata/classification-summary.json` reports an acceptable unclassified rate for the project. |
| #16 | FR-17 Onboarding material generation | `onboarding.md` contains source-linked team rules, reading order, and past-knowledge sections. |
| #17 | FR-18 Content-derived checklist generation | `setup-checklist.md` contains checklist entries extracted from convention or procedure content. |
| #18 | FR-19 Stale information detection | `warnings.md` lists stale, deprecated-marker, or broken-link warnings when matching inputs exist. |
| #19 | FR-20 Duplicate detection | `warnings.md` lists same-name or similar-title duplicate candidates with updated dates and source URLs. |

## Preconditions

- Use a read-only Backlog API key.
- Keep the API key in `.env`; do not paste it into commands, logs, issues, or PR comments.
- Set `BACKLOG_SPACE_KEY`, `BACKLOG_API_KEY`, and `BACKLOG_PROJECT_KEY` in `.env`, or pass the project key with `--project`.
- Run commands from `backlog-knowledge-packager/`.
- Choose one real project that has at least documents, wiki pages, or shared files.

## Commands

Set a project-specific output directory and run the first collection:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --output ./output/PROJECT_KEY
```

Verify the generated package:

```bash
uv run backlog-packager verify-output \
  --output ./output/PROJECT_KEY \
  --max-unclassified-rate 0.2 \
  --require-no-partial-failures \
  --write-report
```

Run collection a second time against the same output directory:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --output ./output/PROJECT_KEY
```

Verify the package again:

```bash
uv run backlog-packager verify-output \
  --output ./output/PROJECT_KEY \
  --max-unclassified-rate 0.2 \
  --require-cache-skip \
  --require-no-partial-failures \
  --write-report
```

Optional broken-link checks:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --output ./output/PROJECT_KEY \
  --check-urls
```

Use `--check-source-urls` only when the Backlog source URLs are reachable from the execution environment without browser-only authentication.

## Partial Failure Handling

`collect` exits with code `3` when at least one target or item has a non-fatal collection failure after the package is generated. The command prints each failure as `partial failure: ...` on stderr.

Treat exit code `3` as generated-but-incomplete evidence:

- Run `verify-output` against the generated directory to check structural consistency.
- Run `verify-output --require-no-partial-failures` only after the non-fatal failures are resolved or explicitly excluded from the selected project scope.
- Record every `partial failure:` line in the issue or PR evidence.
- Inspect `metadata/partial-failures.json`; it should contain the same non-fatal failure reasons.
- Do not mark the affected target's FR as accepted until the target is reachable or the project owner explicitly confirms it is out of scope for that project.
- Acceptance for unaffected targets can still be reviewed from the generated files if source URLs and updated timestamps are present.

## Expected Files

The output directory must contain:

- `knowledge.md`
- `knowledge.json`
- `references.md`
- `setup-checklist.md`
- `onboarding.md`
- `warnings.md`
- `templates.zip`
- `metadata/source-map.json`
- `metadata/classification-summary.json`
- `metadata/collection-summary.json`
- `metadata/partial-failures.json`
- `metadata/acceptance-report.md` when `verify-output --write-report` is used

## Evidence Checks

### FR-15 Differential sync

Inspect `metadata/collection-summary.json` after the second run.

Pass criteria:

- The package still passes `verify-output`.
- The package passes `verify-output --require-no-partial-failures` for final acceptance.
- `verify-output --require-cache-skip` succeeds after the second run.
- Unchanged documents, wiki pages, or shared files are represented in the final outputs.
- Relevant `skippedByCache` counters increase when unchanged items exist.
- Relevant detail fetch or download counters are lower than the listed item counts when unchanged items exist.

If the project has no unchanged items between runs, record that the scenario was not exercised and rerun against a stable project snapshot.

### FR-16 Advanced classification

Inspect `metadata/classification-summary.json` and the `verify-output --max-unclassified-rate` result.

Pass criteria:

- The verifier exits successfully under the selected threshold.
- Each generated knowledge item has a classification and a source URL.
- Each generated knowledge item includes classification confidence metadata.
- `metadata/classification-summary.json` includes `averageConfidence` and `lowConfidence` for tuning.
- `metadata/classification-summary.json` includes source-linked `unclassifiedItems` and `lowConfidenceItems` diagnostics for tuning.
- Representative tags match the item content well enough for AI handoff.

Record the threshold used. `0.2` is the recommended starting threshold, but the project owner may set a stricter value after reviewing real data.

If the unclassified rate is too high, inspect `unclassifiedItems` and `lowConfidenceItems`, add a local `classification-rules.json` with project-specific category and tag keywords, rerun `collect --classification-rules ./classification-rules.json`, and record both the rules file path and the before/after unclassified rate. Do not include confidential source content or API keys in the rules file.

### FR-17 Onboarding material generation

Inspect `onboarding.md`.

Pass criteria:

- It includes source-linked team rules when matching content exists.
- It includes a reading order with Backlog source URLs and updated timestamps.
- It includes past-knowledge references when matching content exists.
- Missing sections are explicit only when no matching source content was collected.

### FR-18 Content-derived setup checklist

Inspect `setup-checklist.md`.

Pass criteria:

- Checklist entries are derived from collected convention or procedure content, not only fixed headings.
- Each actionable entry keeps its source URL and updated timestamp.
- Project-specific setup, convention, template, or procedure items are grouped in a readable order.
- Rule, setup, and operation source bodies can contribute actionable checklist entries when they contain task-like lines.

### FR-19 Stale information detection

Inspect `warnings.md`.

Pass criteria:

- Items older than one year are reported when present.
- Titles or bodies containing stale markers such as `old`, `deprecated`, `obsolete`, or Japanese equivalents are reported when present.
- Body URLs are checked only when `--check-urls` is used.
- Source URL checks are performed only when `--check-source-urls` is used.

### FR-20 Duplicate detection

Inspect `warnings.md`.

Pass criteria:

- Same normalized titles are reported as duplicate candidates.
- Similar template titles are reported as duplicate candidates.
- Same-name wiki and document pages are reported when present.
- Each duplicate candidate includes source URLs and updated timestamps so a human can choose the authoritative item.

## Completion Notes

Attach or summarize the following in the related issue or PR:

- Exact commands run.
- `verify-output` result and unclassified threshold.
- `metadata/acceptance-report.md` when generated.
- Relevant `metadata/collection-summary.json` counters from the second run.
- Any warnings that require human review.
- Any entries in `metadata/partial-failures.json`.
- Any acceptance items that could not be exercised because the real project lacked matching data.
