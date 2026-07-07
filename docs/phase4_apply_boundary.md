# Phase 4 Apply Boundary

Phase 4 adds an explicit apply flow, but it must not weaken the read-only MVP and Phase 3 boundary.

## Non-Negotiable Boundary

- `ReadOnlyBacklogClient` remains read-only and keeps only `get()` and `download()`.
- Write methods such as `post()`, `put()`, `patch()`, and `delete()` must not be added to `ReadOnlyBacklogClient`.
- Any write-capable client must live in a separate module and use a separate class.
- The write-capable client must not be constructible from the default collect/suggest/review-list configuration.
- No command before Phase 4 may write to Backlog.

## Implemented Apply Rules

- Explicit opt-in configuration is required before any write client can be created.
- Apply accepts only local `*.review.json` entries whose `status` is exactly `approved`.
- `pending` and `rejected` review files are ignored by the approved-only selection and cannot reach the write client.
- Missing required fields, malformed JSON, unsafe proposal paths, and unsupported approved source types are rejected before any API call.
- Dry-run is mandatory and must be the default.
- A separate confirmation flag is required for a real write.
- The command prints planned target IDs and source URLs, but never prints API keys or full source bodies.
- The command refuses to apply when the source `updated` timestamp no longer matches the reviewed proposal context.
- The command validates all selected `updated` timestamps before the first write call.
- The command writes an audit log locally, defaulting to the ignored `suggestions/` directory.
- Tests must prove that non-approved review states cannot reach the write client.

## Supported Source Types

Automatic apply is intentionally limited to Wiki pages:

- Wiki: supported through `PATCH /api/v2/wikis/:wikiId`.
- Documents, shared files, and attachments: rejected. They remain manual-apply targets until a safe public update API and conflict model are defined.

## Suggested Command Shape

The dry-run command is:

```bash
uv run backlog-packager apply \
  --suggestions ./output/PROJECT_KEY/suggestions
```

Real writes require a second explicit flag:

```bash
uv run backlog-packager apply \
  --suggestions ./output/PROJECT_KEY/suggestions \
  --confirm-apply
```

`--confirm-apply` must fail unless the write-client configuration is present.

Confirmed apply requires:

- `BACKLOG_ENABLE_WRITE=1`
- `BACKLOG_API_KEY`
- `BACKLOG_SPACE_KEY` or `--space`
- Optional `BACKLOG_DOMAIN` or `--domain`

## Phase 4 Start Order

1. #22: approved-only Wiki apply with dry-run first.
2. #23: design webhook sync after apply has clear audit and conflict rules.
3. #24: decide whether a Web UI or chat integration is needed after the CLI apply workflow is understood.
4. #25: design permission-aware answers and RAG only after source authorization and output access boundaries are explicit.
