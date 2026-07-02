# AGENTS.md

Instructions for AI agents working in this repository.

## Project

**Backlog Knowledge Packager** — collects conventions, templates, knowledge, and reference URLs scattered across Backlog (documents / wikis / shared files / attachments) in a **read-only** manner, and generates AI-readable Markdown, onboarding reference lists, setup checklists, and template zips.

- Requirements: [`docs/requirements.md`](docs/requirements.md) (FR-XX / NFR-XX IDs)
- Design: [`docs/design.md`](docs/design.md) (architecture, modules, directory layout)

## Language policy

| Audience | Language |
|----------|----------|
| Agent-facing files: `AGENTS.md`, `docs/`, `.claude/prompts/`, code comments | **English** |
| User-facing text: answers to the user, Issue titles/bodies, PR titles/bodies, commit summaries, issue comments | **Japanese** |

## Core constraints (never violate)

1. **Read-only against Backlog** (FR-11): never call write APIs (POST/PUT/PATCH/DELETE). The client must not even have write methods (`ReadOnlyBacklogClient`, design §9).
2. **Source URLs are mandatory** (NFR-04): every generated knowledge item carries its Backlog URL and updated timestamp.
3. **Never expose the API key** (NFR-01): `.env` only; never in code, logs, or outputs. `.env` is gitignored.
4. **Minimal dependencies** (NFR-07): requests / python-dotenv / stdlib. Justify any addition.

## Repository layout

```
docs/                       # Requirements & design (English)
backlog-api-poc/            # Reference POC — do NOT modify
backlog-knowledge-packager/ # Implementation (created in MVP Issue #1)
.claude/prompts/            # Workflow prompts (start / ship / review / ...)
```

## Workflow (GitHub Flow)

- Work is driven by GitHub Issues (milestones: `v0.1 (MVP)` → `Phase 2` → `Phase 3` → `Phase 4`).
- Never push directly to `main`; branch (`feature/` `fix/` `chore/` ...) → PR → merge. Branch protection is enabled on `main`.
- Commit format: `<type>: <summary in Japanese>` (feat / fix / docs / refactor / chore / test / style).
- See `.claude/prompts/` for step-by-step workflows: `start`, `new-feature`, `ship`, `review`, `test-check`, `sync-main`, `long-run`, `create-issue`, `update-skill`.

## Tech stack

Python 3.12+ / uv / requests / python-dotenv / argparse / pytest. Run tests with `uv run pytest` inside `backlog-knowledge-packager/`.
