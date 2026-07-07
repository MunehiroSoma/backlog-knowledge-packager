# TC_collect: MVP Real Project Acceptance

This checklist verifies the MVP collection flow against a real Backlog project without exposing API keys or real source bodies.

## Scope

| Issue | Requirement | Acceptance evidence |
|-------|-------------|---------------------|
| #3 | Read-only client | `ReadOnlyBacklogClient` can call `GET /api/v2/space` and has no write methods. |
| #4 | Documents | Document list and detail collection succeeds for the selected project. Document tree and document attachment download remain pending unless the selected run explicitly verifies them. |
| #5 | Wikis | Wiki list and detail collection succeeds or is gracefully skipped when the project has wiki disabled. Wiki attachment download remains pending unless the selected run explicitly verifies it. |
| #6 | Shared files | Shared-file metadata is listed recursively and file downloads are verified unless metadata-only collection is explicitly selected. |
| #7 | Normalization | Every emitted item has a source URL and updated timestamp. |
| #8 | Classification | Every emitted item has a category. |
| #9 | Knowledge outputs | `knowledge.md` and `knowledge.json` are generated. |
| #10 | Reference and checklist outputs | `references.md` and `setup-checklist.md` are generated. |
| #11 | Package and metadata outputs | `templates.zip` and `metadata/source-map.json` are generated. |
| #12 | CLI collect flow | Exit codes and partial failures follow the CLI contract. |
| #13 | End-to-end acceptance | The generated package passes `verify-output` and source traceability checks. |

## Preconditions

- Use a read-only Backlog API key.
- Keep `BACKLOG_API_KEY` in `.env`; never paste it into commands, logs, issues, PRs, or fixtures.
- Run commands from `backlog-knowledge-packager/`.
- Choose one real project that has at least documents, wiki pages, or shared files.
- Use an output directory under `./output/`; the directory is ignored by git.
- Do not attach generated source bodies, raw API payloads, or `knowledge.*` contents to GitHub.

## Commands

Run collection:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --output ./output/PROJECT_KEY
```

For very large shared-file trees, metadata-only collection is acceptable for a scoped acceptance run if it is recorded explicitly:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --skip-shared-file-downloads \
  --output ./output/PROJECT_KEY
```

To verify shared-file downloads without collecting a very large tree, choose a small directory and record the scoped path privately:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets shared-files \
  --shared-file-path /SMALL_DIRECTORY/ \
  --output ./output/PROJECT_KEY-shared-file-download
```

For projects with many document or wiki attachments, attachment metadata-only collection is acceptable for a scoped acceptance run if it is recorded explicitly:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --skip-attachment-downloads \
  --output ./output/PROJECT_KEY
```

Verify the generated package:

```bash
uv run backlog-packager verify-output \
  --output ./output/PROJECT_KEY \
  --require-no-partial-failures \
  --write-report
```

Run collection a second time against the same output directory, then verify cache reuse:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --output ./output/PROJECT_KEY

uv run backlog-packager verify-output \
  --output ./output/PROJECT_KEY \
  --require-cache-skip \
  --require-no-partial-failures \
  --write-report
```

Use `--check-source-urls` only when Backlog source URLs are reachable from the execution environment without browser-only authentication:

```bash
uv run backlog-packager collect \
  --project PROJECT_KEY \
  --targets documents,wiki,shared-files \
  --check-source-urls \
  --output ./output/PROJECT_KEY
```

## Evidence To Record

Record only sanitized facts:

- Commands run, with `PROJECT_KEY` if it is not confidential.
- Exit codes for each command.
- `verify-output` result.
- `metadata/acceptance-report.md` result summary, excluding source bodies.
- `metadata/collection-summary.json` counters.
- `metadata/classification-summary.json` aggregate metrics.
- Whether `metadata/partial-failures.json` is empty.
- Whether shared files were downloaded or metadata-only.
- Whether document/wiki attachments were downloaded or metadata-only.
- Whether document tree, document attachments, and wiki attachments were exercised.

Do not record:

- API keys or `.env` contents.
- Real Backlog page bodies.
- Raw API payloads containing internal text.
- Full generated `knowledge.md`, `knowledge.json`, or `source-map.json`.

## Current Acceptance Note

`PHASE2_STATUS.md` records a real Backlog acceptance run that generated and verified a package with metadata-only shared-file collection. That evidence supports the implemented collect/generate/verify flow, but it does not close the remaining document-tree and attachment-download gaps unless a later run explicitly exercises those items.
