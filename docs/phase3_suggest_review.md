# Phase 3 Suggest / Review Operations

Phase 3 is local-only. It reads generated package files and writes proposal files under `suggestions/`; it never writes to Backlog.

## Inputs

- `knowledge.json`
- `metadata/source-map.json`

Both files must come from a verified `collect` output. Each item must retain its source URL and updated timestamp.

## Commands

Generate local suggestions:

```bash
uv run backlog-packager suggest \
  --output ./output/PROJECT_KEY
```

List only approved reviews:

```bash
uv run backlog-packager review-list \
  --suggestions ./output/PROJECT_KEY/suggestions
```

List another local review state when needed:

```bash
uv run backlog-packager review-list \
  --suggestions ./output/PROJECT_KEY/suggestions \
  --status pending
```

## Generated Files

Each source item creates:

- `*.update.md`: proposed full replacement text.
- `*.diff.md`: title, source type, Backlog URL, updated timestamp, proposal reason, before/after diff, and an unapplied warning.
- `*.review.json`: local review state.

`review.json` fields stay local:

- `status`: `pending`, `approved`, or `rejected`.
- `reviewer`: reviewer name or identifier, maintained by the reviewer.
- `reviewedAt`: review timestamp, maintained by the reviewer.
- `note`: local review note.

## Boundaries

- `suggest` and `review-list` must not instantiate a Backlog client.
- `suggest` and `review-list` must not call POST, PUT, PATCH, or DELETE.
- `review-list` defaults to approved items only.
- `suggestions/` is ignored by git because proposal files may contain source-derived content.
- Applying a proposal remains manual through Phase 3.
