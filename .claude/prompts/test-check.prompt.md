---
mode: agent
description: Run the implementation-complete checklist and provide the test record template
---

# test-check — Implementation-complete check

Run the implementation-complete checklist. Do not declare "done" until all items pass.

## Completion checklist

### Code quality

- [ ] `cd backlog-knowledge-packager && uv run pytest` passes
- [ ] Type hints are present on changed functions/dataclasses
- [ ] No new dependencies without justification (NFR-07)

### Happy path

- [ ] `collect` produces the expected outputs (knowledge.md / knowledge.json / references.md / setup-checklist.md / templates.zip / metadata/)
- [ ] Every output item carries a source URL and updated timestamp (NFR-04)

### Error path

- [ ] Missing env vars / invalid arguments exit with code 1
- [ ] API errors (auth failure, project not found) exit with code 2
- [ ] Partial fetch failure exits with code 3 and logs the failed items

### Domain constraints

- [ ] The Backlog client has no write methods (FR-11)
- [ ] `apiKey` does not appear in logs or outputs (NFR-01)

## Test record template

Record in `docs/test/TC_<feature>.md` in the following format (content may be in Japanese).

```markdown
# TC_<feature>

## Session
- Date: YYYY-MM-DD
- Tester: <name>

## Happy path
| Case | Steps | Expected | Result |
|---|---|---|---|
| | | | Pass/Fail |

## Error path
| Case | Steps | Expected error | Result |
|---|---|---|---|
| | | | Pass/Fail |

## Notes
```
