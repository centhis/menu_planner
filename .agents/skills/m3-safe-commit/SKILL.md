---
name: m3-safe-commit
description: "Use when building the Menu Planner M3 safe commit layer: persistence primitives, versioning, OperationPreview hashing, persistent Confirmation, idempotency, transactional commit, audit, and tests, without profile/menu workflows, LLM, Hermes plugin, or Telegram UX."
---

# M3 safe commit workflow

## Scope

- Build only deterministic persistence and safe commit mechanisms.
- Use M2 contracts, state machine, policy, and error catalog as inputs.
- Add migrations, repository/application ports, SQL adapters, confirmation
  lifecycle, idempotency, transaction orchestration, and audit.
- Do not implement production profile, menu, recipe, shopping list, store,
  Intent Router, LLM generation, Hermes plugin, or Telegram business UX.
- Do not create or modify a custom Hermes image.

## Required context

Read before acting:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 3.md`
- `docs/experiments/m2-domain-skeleton.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If a product or safety decision is missing, ask the user during that step.
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
- Hermes and Telegram callbacks must never commit application state directly.
- State-changing commands require preview, confirmation, version check,
  idempotency handling, transaction, and audit.
- Do not choose business rollback policy without explicit user decision.
- Keep secrets out of Git, logs, reports, and diffs.
