# Phase 4 Operational Extension Decisions

This document records the Phase 4 decisions for the low-priority operational extensions after the CLI collect, suggest, review, and apply flows are available.

## Decision Summary

| Issue | Requirement | Decision |
|-------|-------------|----------|
| #23 | FR-26 Webhook sync | Do not add a built-in webhook receiver. Support an external webhook runner pattern that invokes the existing read-only `collect` workflow with cache. |
| #24 | FR-24 Web UI / FR-25 Chatbot | Do not add a Web UI or Slack / Teams bot to the standard package. Keep the CLI and local file workflow as the supported interface. |
| #25 | FR-27 Permission-aware answers / FR-28 Full RAG | Do not add vector DB or answer-serving features to the standard package. Treat any RAG integration as a separate application that consumes verified outputs. |

These decisions keep the package dependency-light, preserve Backlog read/write boundaries, and avoid introducing long-running services into the CLI project.

## #23 Webhook Sync Boundary

Backlog webhooks can notify external services when Backlog objects are added or updated. The package does not own an HTTP server, public endpoint, webhook secret store, retry queue, or deployment runtime.

Supported pattern:

1. An external webhook receiver validates the request, stores a local event log, and decides which project output to refresh.
2. The receiver invokes `uv run backlog-packager collect` with the same output directory.
3. Existing source-map cache logic skips unchanged items and re-fetches changed items by `updated` timestamp.
4. The receiver runs `uv run backlog-packager verify-output --require-no-partial-failures --write-report` before using the refreshed package.

Target handling:

- Wiki create/update events map to the `wiki` target.
- Shared file create/update events map to the `shared-files` target.
- Document events map to the `documents` target when the external receiver can identify the project scope.
- Unknown, delete, permission, or shape-changing events should trigger a full selected-target refresh rather than a single-item shortcut.

Out of scope for this package:

- Creating, updating, or deleting Backlog webhook settings.
- Running an inbound HTTP server.
- Maintaining a durable retry queue.
- Mutating Backlog in response to webhook events.

## #24 Web UI and Chatbot Boundary

The supported Phase 4 user interface remains:

- `collect` for local packaging.
- `suggest` for local proposal generation.
- `review-list` for approved review discovery.
- `apply` for dry-run and explicit confirmed Wiki apply.

A Web UI or chat bot may be built as a separate application only if it follows these rules:

- It consumes generated files from `output/` and `suggestions/`; it does not bypass source URL and `updated` traceability.
- It never stores or prints `BACKLOG_API_KEY`.
- It does not create a second write path. Confirmed writes must go through the same approved-only apply rules.
- It preserves local review state fields: `status`, `reviewer`, `reviewedAt`, and `note`.
- It uses the CLI package as a library or subprocess, not a forked implementation of the Backlog API rules.

No additional runtime dependencies are added for #24.

## #25 Permission-Aware Answers and RAG Boundary

The package generates portable knowledge files; it is not an answer-serving or authorization service.

Any future RAG or AI answer application must enforce these rules:

- Index only verified outputs that include Backlog source URL and `updated`.
- Keep source authorization outside this package and aligned with the requesting user's Backlog permissions.
- Filter retrieval results before generation, not only after answer generation.
- Include source URLs and updated timestamps in every answer.
- Avoid indexing hidden local artifacts such as `.env`, cache internals, audit logs, or unapproved suggestions.
- Treat vector DB selection as an application decision, not a dependency of this package.

No vector DB, embedding dependency, chat model SDK, or bot framework is added for #25.

## Reopen Criteria

Reopen or create new implementation issues only when all of the following are available:

- A deployment owner for a webhook receiver, Web UI, bot, or RAG service.
- A secret-management plan for API keys and bot credentials.
- A permission model that maps request users to Backlog-readable sources.
- Acceptance tests that use sanitized fixtures only.
- A reason why the existing CLI workflow is insufficient.
