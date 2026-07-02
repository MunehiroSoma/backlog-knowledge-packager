---
name: start
description: Check open GitHub Issues, pick one to work on, and create a branch. Use when starting a new work session or when the user asks what to work on next.
---

# start — Begin work

Before starting new work, check GitHub Issues, pick one to work on, and create a branch.

## Steps

0. Pre-check

   ```bash
   gh auth status
   ```

1. List open issues

   ```bash
   gh issue list --repo MunehiroSoma/backlog-knowledge-packager --state open
   ```

1. Review labels and milestones, present work candidates, and let the user choose

1. Inspect the chosen issue

   ```bash
   gh issue view <number> --repo MunehiroSoma/backlog-knowledge-packager
   ```

1. Create a branch matching the issue type

   ```bash
   git checkout main && git pull origin main
   git checkout -b <prefix>/<issue-slug>
   ```

1. Leave a start-of-work comment on the issue (optional; comment text in Japanese)

   ```bash
   gh issue comment <number> --body "作業開始します。ブランチ: <branch-name>"
   ```

## Branch naming convention

| Prefix | Purpose |
|--------|---------|
| `feature/` | New feature |
| `fix/` | Bug fix |
| `hotfix/` | Urgent production fix |
| `chore/` | Config / dependencies |
| `refactor/` | Refactoring |

All kebab-case (lowercase letters and hyphens).
