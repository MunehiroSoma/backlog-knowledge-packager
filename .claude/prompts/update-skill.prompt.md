---
mode: agent
description: Reflect on how a prompt performed and improve the files in .claude/prompts/
---

# update-skill — Improve prompts

Reflect on the most recently used prompt and improve the contents of `.claude/prompts/`.

## Reflection points

- Were any steps ambiguous enough to cause hesitation?
- Were there too many / too few steps?
- Did errors or unexpected behavior occur?
- Was there a simpler or more effective approach?
- Are any command examples outdated?

## Steps

1. Read the target prompt file

   ```
   .claude/prompts/<name>.prompt.md
   ```

1. Propose improvements (show before / after explicitly)

1. After approval, update the file and commit

   ```bash
   git add .claude/prompts/<name>.prompt.md
   git commit -m "chore: <name> プロンプトを改善"
   ```

## Criteria for changes

| Situation | Action |
|-----------|--------|
| A step is ambiguous every time | Add a concrete example |
| Steps are too long | Remove non-essential steps |
| A command errored | Fix to the correct command |
| A step is never used | Delete it |

Never rewrite a file without approval.
