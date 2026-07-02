---
mode: agent
description: Review a PR number or diff against the design docs and project constraints
---

# review — Code review

Take a PR number (or a diff) and review it against the requirements, design docs, and project constraints.

> Requirements: [`docs/requirements.md`](../../docs/requirements.md) / Design: [`docs/design.md`](../../docs/design.md)

## Input

- **PR number given**: fetch the changes with `gh pr view <number>` / `gh pr diff <number>` and review
- **Diff pasted**: review it directly with the criteria below

## Cross-check against design docs by change type

Refer only to the documents relevant to the change.

| Change type | Reference |
|-------------|-----------|
| Collector / API access changes | `docs/design.md` §4 (endpoints), §3.1 |
| Data model changes | `docs/design.md` §5 (KnowledgeItem) |
| Classification changes | `docs/design.md` §6 (categories, match order) |
| Output format changes | `docs/design.md` §7 |
| CLI changes | `docs/design.md` §8 (args, exit codes) |
| Requirement compliance | `docs/requirements.md` (FR-XX / NFR-XX) |

## Review criteria

### 1. Design consistency

- [ ] Endpoints and parameters match `docs/design.md` §4
- [ ] Data structures match the KnowledgeItem definition (§5)
- [ ] The implementation maps to requirement IDs (FR-XX / NFR-XX)

### 2. Layer responsibilities

- [ ] Backlog API knowledge stays inside `collector/` (and `client.py`)
- [ ] `classifier` / `generator` depend only on `KnowledgeItem`, not on the API

### 3. Domain constraints (critical for this project)

- [ ] **No write methods on the Backlog client** — GET / download only (FR-11)
- [ ] Every output item carries a source URL and updated timestamp (NFR-04)
- [ ] `apiKey` never appears in logs, error messages, or outputs (NFR-01)
- [ ] No new dependencies without justification (NFR-07)

### 4. Types and style

- [ ] Type hints on functions and dataclasses
- [ ] Code follows the existing style of the module being changed

### 5. Tests

- [ ] Happy-path tests exist
- [ ] Error-path tests exist (invalid input, API errors, partial failure)
- [ ] classifier / normalizer tests run without API access

## Output format (findings in Japanese)

```
## PR #43 レビュー結果：feat: Collector のドキュメント取得を実装

[設計] ページング処理が offset 固定 → design.md §3.1 のループ仕様と不一致
[Layer] generator から client を直接呼んでいる → collector 経由に修正
[Domain] client に post() が追加されている → FR-11 違反、削除必須
[Test] レート制限 429 時のリトライがテスト不足
```

If there are no findings, output `指摘事項なし。`
