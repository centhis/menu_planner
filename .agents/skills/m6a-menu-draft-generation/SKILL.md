---
name: m6a-menu-draft-generation
description: "Use when building the Menu Planner M6A menu draft generation and validation slice: PlanningContext, MealSlot, MenuDraft, deterministic fake generator, validators, bounded repair loop, golden fixtures, safe preview, and M6A report, without recipes, substitutions, shopping list, Hermes plugin, Telegram UX, direct menu activation, or production model dependency."
---

# M6A menu draft generation workflow

## Scope

- Build only validated menu draft generation up to Gate M6A.
- Use confirmed profile data and explicit planning request parameters to build
  `PlanningContext`.
- Add or refine `PlanningContext`, `MealSlot`, `MenuDraft`, generator port,
  fake generator, validators, bounded repair loop, golden fixtures, and safe
  preview.
- Do not implement recipes, substitutions, shopping list, store catalog,
  production Hermes plugin/tools, Telegram UX, or direct menu activation.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m6-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
or when the brief is insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 6.md`
- `docs/experiments/m5-intent-router.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0006-profile-vertical-slice.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If profile-field semantics, menu shape, model/provider choice, prompt
   logging, repair limit, or activation policy is blocking, ask the user during
   that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run targeted contract/unit/golden checks first.
8. Run M6A eval/golden checks when the task changes generator, validators, or
   repair behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine fixture, validator, or fake
  generator changes when the brief and affected files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Generator output is untrusted until validated.
- Model/fake output must never activate menu or write confirmed state.
- Invalid drafts must not become commit previews.
- Repair loop must be bounded and use structured validation errors.
- Keep Domain Core independent from Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
