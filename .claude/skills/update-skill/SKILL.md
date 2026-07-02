---
name: update-skill
description: Reflect on how a skill performed and improve the files in .claude/skills/. Use after a skill produced a confusing or suboptimal result.
---

# update-skill — Improve skills

Reflect on the most recently used skill and improve the contents of `.claude/skills/`.

## Reflection points

- Were any steps ambiguous enough to cause hesitation?
- Were there too many / too few steps?
- Did errors or unexpected behavior occur?
- Was there a simpler or more effective approach?
- Are any command examples outdated?

## Steps

1. Read the target skill file

   ```
   .claude/skills/<name>/SKILL.md
   ```

1. Propose improvements (show before / after explicitly)

1. After approval, update the file and commit

   ```bash
   git add .claude/skills/<name>/SKILL.md
   git commit -m "chore: <name> スキルを改善"
   ```

## Criteria for changes

| Situation | Action |
|-----------|--------|
| A step is ambiguous every time | Add a concrete example |
| Steps are too long | Remove non-essential steps |
| A command errored | Fix to the correct command |
| A step is never used | Delete it |

Never rewrite a file without approval.
