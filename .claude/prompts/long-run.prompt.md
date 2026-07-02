---
mode: agent
description: Complete a long implementation task autonomously without interruptions
---

# long-run — Long autonomous implementation

Run a long implementation task continuously without unnecessary confirmation pauses.

## Ground rules

- Keep implementing, verifying, and fixing until an explicit stop instruction
- Share progress at each milestone, but do not ask "may I continue?" as a rule
- When a judgment call is needed, choose the lower-impact option and keep moving

## Branch workflow

```bash
# 1. Create a feature branch from main
git checkout main && git pull origin main
git checkout -b feature/<task-slug>

# 2. Repeat: implement, verify, fix

# 3. When done, push and create a PR
git push origin feature/<task-slug>
gh pr create ...
```

> Do not use an `autopilot/` prefix. Branch naming: `feature/` `fix/` `chore/` etc.

## Execution loop

1. Confirm the goal and completion criteria
1. Investigate the impact area and implement in the order that delivers value fastest
1. Verify after implementing
   ```bash
   cd backlog-knowledge-packager && uv run pytest
   ```
1. On failure, self-fix and re-run (repeat until green)
1. When the completion criteria are met, report results, open items, and recommended next actions

## When blocked

- If no progress for 10+ minutes, try an alternative approach first
- Only if still stuck, ask exactly one short question
