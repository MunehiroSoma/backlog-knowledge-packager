# Backlog Knowledge Packager

Collects conventions, templates, past knowledge, and reference URLs scattered across Backlog (documents / wikis / shared files / attachments) in a **read-only** manner, and generates AI-readable Markdown, an onboarding reference list, a setup checklist, and a template zip.

- Requirements: [`../docs/requirements.md`](../docs/requirements.md)
- Design: [`../docs/design.md`](../docs/design.md)

## Core constraints

- **Read-only against Backlog** (FR-11): the API client has no write methods
- **Source URLs are mandatory** on every output (NFR-04)
- **API keys live in `.env` only** (NFR-01): never committed, never logged

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env   # then fill in BACKLOG_SPACE_KEY / BACKLOG_API_KEY / BACKLOG_PROJECT_KEY
```

`BACKLOG_SPACE_KEY` is the subdomain part of the Backlog URL. For example,
`https://your-space.backlog.com/` uses `BACKLOG_SPACE_KEY=your-space` and
`BACKLOG_DOMAIN=backlog.com`. Use only letters, numbers, and hyphens in the
space key.

## Usage

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --output ./output/PROJECT_KEY
```

`--project` may be omitted when `BACKLOG_PROJECT_KEY` is set in `.env`.

`collect` writes `knowledge.md`, `knowledge.json`, `references.md`, `setup-checklist.md`, `onboarding.md`, `warnings.md`, `templates.zip`, `metadata/source-map.json`, `metadata/classification-summary.json`, `metadata/collection-summary.json`, and `metadata/partial-failures.json`.
On later runs, unchanged items are skipped by comparing source IDs and updated timestamps in the previous source map.
`warnings.md` includes stale items, deprecated/old markers, same-name or similar-title duplicates, and optional broken-link checks.

Use `--check-urls` when you want `warnings.md` to include unreachable URLs found inside item bodies. This performs additional network requests and is disabled by default.
Use `--check-source-urls` only when Backlog source URLs are publicly reachable from this environment; private Backlog spaces may fail unauthenticated URL checks even when the source is valid.

For project-specific classification tuning, pass a JSON keyword file:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --classification-rules ./classification-rules.json \
  --output ./output/PROJECT_KEY
```

```json
{
  "categories": {
    "rule": ["ADR", "architecture decision record"]
  },
  "tags": {
    "architecture": ["ADR", "decision record"]
  }
}
```

Verify a generated package before handing it to a new member or AI:

```bash
uv run backlog-packager verify-output --output ./output/PROJECT_KEY
```

The verifier checks required files, source URL / updated traceability in generated Markdown, `metadata/source-map.json`, `knowledge.json` structure, classification summary consistency, collection summary counters, cross-file item consistency, and `templates.zip` / `original-links.json` contents.
Use `--max-unclassified-rate 0.2` or another 0.0-1.0 threshold to fail verification when classification quality is below the acceptable level for the project.
Use `--require-no-partial-failures` for final acceptance when every selected target must be collected without non-fatal failures.
Use `--write-report` to write `metadata/acceptance-report.md` with the key Phase 2 evidence for issue or PR updates.
`metadata/classification-summary.json` also reports average classification confidence, low-confidence item counts, and source-linked `unclassifiedItems` / `lowConfidenceItems` diagnostics for Phase 2 tuning.

Recommended Phase 2 acceptance flow against a real Backlog project:

```bash
uv run backlog-packager collect --project PROJECT_KEY --output ./output/PROJECT_KEY
uv run backlog-packager verify-output --output ./output/PROJECT_KEY --max-unclassified-rate 0.2 --require-no-partial-failures --write-report
uv run backlog-packager collect --project PROJECT_KEY --output ./output/PROJECT_KEY
uv run backlog-packager verify-output --output ./output/PROJECT_KEY --max-unclassified-rate 0.2 --require-cache-skip --require-no-partial-failures --write-report
```

The second `collect` confirms differential sync still produces a complete package while skipping unchanged item detail fetches/downloads.
`--require-cache-skip` confirms `metadata/collection-summary.json` reports at least one skipped item after the second run.
Use [`../docs/test/TC_phase2.md`](../docs/test/TC_phase2.md) to record the FR-15 through FR-20 acceptance evidence, and [`../docs/test/PHASE2_STATUS.md`](../docs/test/PHASE2_STATUS.md) for current implementation status.

See [`../docs/design.md`](../docs/design.md) section 8 for the full CLI specification (arguments, environment variables, exit codes).

## Development

```bash
uv run pytest
```

Module layout follows the design document section 10. Generator modules are API-independent and covered by unit tests.
