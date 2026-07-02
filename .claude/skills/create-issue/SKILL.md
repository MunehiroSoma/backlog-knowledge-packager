---
name: create-issue
description: Register GitHub Issues with correct granularity and structure. Use when the user wants to create a Task or Bug issue on the repository.
---

# create-issue — Create an Issue

Register GitHub Issues with correct granularity and structure. Issue titles and bodies are written in Japanese.

## Issue types

| Type | When to use |
|------|-------------|
| **Task** | One implementation task (completable in 1–3 days) |
| **Bug** | A defect found in the code |

## Always present for review before registering

1. Planned title
1. Planned labels and milestone
1. Draft body (including checklist and completion criteria)

Run `gh issue create` only after approval.

## Task issue template (body in Japanese)

```markdown
## 概要
<実装内容の概要>

**対応要件**: FR-XX / NFR-XX（docs/requirements.md） | **設計**: docs/design.md §X | **優先度**: 高/低

## 完了条件
<具体的な動作確認方法>

## 作業チェックリスト
- [ ] タスク1
- [ ] タスク2

## ビジネスルール（該当時）
- <制約・バリデーション仕様>
```

## Bug issue template (body in Japanese)

```markdown
## 概要
<何が問題か・影響範囲>

## 再現手順
1. ...

## 期待する動作
...

## 問題箇所
`<file path>` L<line number>
```

## gh command

```bash
gh issue create \
  --title "<タイトル>" \
  --label "<label>" \
  --milestone "<milestone>" \
  --body "..."
```
