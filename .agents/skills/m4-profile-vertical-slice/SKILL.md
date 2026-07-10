---
name: m4-profile-vertical-slice
description: "Use when building the Menu Planner M4 profile vertical slice: ProfileDraft validation, preview, persistent confirmation, safe commit, ProfileVersion read-back, audit, CLI/test API, and tests, without LLM, Intent Router, Hermes plugin, Telegram UX, menu, recipes, or shopping list."
---

# M4 profile vertical slice workflow

## Scope

- Build only the first deterministic business vertical slice for profile.
- Reuse M2 contracts/policy and M3 safe commit primitives.
- Add profile-specific validation, application commands/queries,
  persistence mapping, preview, commit, audit, and tests.
- Connect profile workflow to the M2 state machine/policy and cover disallowed
  actions in the current workflow state.
- Provide a temporary CLI or test API for the scenario.
- Do not implement Intent Router, LLM generation, Hermes plugin, Telegram UX,
  menu, recipes, shopping list, store catalog, or substitutions.
- Do not create or modify a custom Hermes image.

## Required context

Read before acting:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 4.md`
- `docs/experiments/m3-safe-commit.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If a product or safety decision is blocking, ask the user during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run the narrowest relevant checks first.
8. Run `git diff --check`.
9. Report changed files, commands, passed checks, skipped checks, assumptions,
   and follow-up tasks.

## Guardrails

- Domain Core must not import Hermes, Telegram, ORM, HTTP clients, or model SDK.
- Application service owns transaction boundary and PostgreSQL writes.
- Profile workflow/policy must block profile actions outside the current
  state.
- Profile commit must reuse preview, confirmation, version check,
  idempotency handling, transaction, and audit.
- User text, LLM output, Hermes callbacks, and Telegram callbacks are outside
  M4 and must not commit application state.
- Do not choose final product profile fields without explicit user decision.
- Keep secrets out of Git, logs, reports, and diffs.
