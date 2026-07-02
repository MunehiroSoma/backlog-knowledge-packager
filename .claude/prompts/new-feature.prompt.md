---
mode: agent
description: Create a new branch from main and start development
---

# new-feature — Create a branch

Create a new branch from main and start development.

## Usage

```
@new-feature feature/user-authentication
@new-feature fix/login-redirect-error
```

## Steps

1. Update main to the latest

   ```bash
   git checkout main && git pull origin main
   ```

1. Create the branch

   ```bash
   git checkout -b <prefix>/<branch-name>
   ```

## Branch naming convention

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New feature | `feature/user-authentication` |
| `fix/` | Bug fix | `fix/login-redirect-error` |
| `hotfix/` | Urgent production fix | `hotfix/token-null-pointer` |
| `chore/` | Config / build / dependencies | `chore/update-deps` |
| `refactor/` | Refactoring | `refactor/extract-service-layer` |

All kebab-case (lowercase letters and hyphens). No Japanese, spaces, or underscores.
