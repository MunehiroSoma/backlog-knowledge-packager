---
mode: agent
description: Commit the current branch's changes, push, and create a PR in one flow
---

# ship — Commit, push, PR

Commit the current branch's changes, push, and create a PR in one flow.

> Follows **GitHub Flow**. Never push directly to `main`; always merge via PR.

## Steps

1. Review the changes

   ```bash
   git status --short && git diff --stat
   ```

1. Run checks (once the implementation project exists)

   ```bash
   cd backlog-knowledge-packager && uv run pytest
   ```

1. Stage and commit

   ```bash
   git add <related-files>
   git commit -m "<type>: <summary in Japanese>"
   ```

1. Push

   ```bash
   git push origin <current-branch>
   ```

1. Create the PR (PR title/body in Japanese)

   ```bash
   gh pr create \
     --title "<type>: <summary>" \
     --body "## 概要
   <変更内容>

   ## 関連 Issue
   Closes #<number>

   ## 確認事項
   - [ ] 正常系確認
   - [ ] 異常系確認
   - [ ] テスト通過"
   ```

## Commit message convention

Format: `<type>: <summary in Japanese>`

| type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `refactor` | Refactoring |
| `chore` | Config / dependency updates |
| `test` | Add / fix tests |
| `style` | Formatting only (no behavior change) |
