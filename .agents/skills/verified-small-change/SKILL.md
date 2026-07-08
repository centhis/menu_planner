---
name: verified-small-change
description: Use for implementing one small, clearly bounded Menu Planner task with acceptance criteria, tests, diff review, and no unrelated refactoring.
---

# Verified small change workflow

1. Read AGENTS.md and relevant architecture documents.

2. Restate:
   - task goal;
   - files expected to change;
   - acceptance criteria;
   - commands expected to verify the result.

3. Inspect the current implementation before editing.

4. Do not change files outside the declared task scope unless required.
   If additional work is discovered, record it as a follow-up instead.

5. Make the smallest coherent change.

6. Run the narrowest relevant checks first.

7. Run:
   git diff --check

8. Review:
   git status --short
   git diff --stat
   git diff

9. Do not commit unless explicitly instructed.

10. Report:
    - files changed;
    - checks passed;
    - checks not run;
    - assumptions;
    - follow-up tasks.