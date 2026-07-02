---
name: sync-main
description: Sync main to the latest and rebase the current working branch. Use when the working branch has fallen behind main or before creating a PR.
---

# sync-main — Sync main & rebase

Sync main to the latest and rebase the current working branch.

## Steps

1. Check the current branch

   ```bash
   git branch --show-current
   ```

1. Update main to the latest

   ```bash
   git fetch origin
   git checkout main && git pull origin main
   ```

1. Return to the original branch and rebase

   ```bash
   git checkout <original-branch>
   git rebase main
   ```

1. If there are conflicts, inspect them and report to the user

## Notes

- If a push is needed after rebasing, use `git push --force-with-lease`
- For complex conflicts, confirm with the user before proceeding
