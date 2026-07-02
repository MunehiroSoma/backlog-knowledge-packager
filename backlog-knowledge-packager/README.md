# Backlog Knowledge Packager

Collects conventions, templates, past knowledge, and reference URLs scattered across Backlog (documents / wikis / shared files / attachments) in a **read-only** manner, and generates AI-readable Markdown, an onboarding reference list, a setup checklist, and a template zip.

- Requirements: [`../docs/requirements.md`](../docs/requirements.md)
- Design: [`../docs/design.md`](../docs/design.md)

## Core constraints

- **Read-only against Backlog** (FR-11): the API client has no write methods
- **Source URLs are mandatory** on every output (NFR-04)
- **API keys live in `.env` only** (NFR-01) — never committed, never logged

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env   # then fill in BACKLOG_SPACE_KEY / BACKLOG_API_KEY
```

## Usage

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --output ./output/PROJECT_KEY
```

> **Status**: skeleton only — the `collect` command is not implemented yet.
> Implementation is tracked in the [v0.1 (MVP) milestone](https://github.com/MunehiroSoma/backlog-knowledge-packager/milestone/1).

See [`../docs/design.md`](../docs/design.md) §8 for the full CLI specification (arguments, environment variables, exit codes).

## Development

```bash
uv run pytest
```

Module layout follows the design document §10. Each stub module carries a `TODO` pointing to the issue that implements it.
