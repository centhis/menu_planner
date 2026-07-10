---
name: m2-domain-skeleton
description: "Use when building or changing the Menu Planner M2 domain skeleton: versioned domain contracts, schema validation, machine-readable error catalog, workflow state machine, policy decisions, fixtures, and tests, without persistence/commit, LLM generation, Hermes plugin implementation, Telegram UX, or business workflows beyond deterministic M2 policy."
---

# M2 domain skeleton workflow

## Scope

- Build only the deterministic M2 domain skeleton.
- M2 includes M2A contracts and M2B workflow/policy, ending at M2 reflection.
- Add versioned contract models or schemas, fixtures, validation tests, stable
  machine-readable errors, state machine tables, operation classes, and policy
  decisions.
- Do not add PostgreSQL domain tables, repositories, transaction boundaries,
  confirmation commit, idempotency persistence, LLM generation, production
  Hermes plugin code, Telegram UX, recipes, menus, shopping lists, or profile
  workflows beyond contracts/policy needed for M2.

## Required context

Read before acting:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 1.md`
- `docs/Stage 2.md`
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md`
- `docs/decisions/ADR-0002-application-runtime.md`
- `docs/decisions/ADR-0003-post-m1-runtime-boundaries.md`

## Work cycle

1. Restate the single M2 task and acceptance criteria.
2. Identify expected files and confirm the change stays inside M2.
3. Inspect existing contracts, tests, and docs before editing.
4. Add one small contract, error set, state transition group, or policy rule.
5. Add fixtures and negative tests with the implementation.
6. Run the narrowest relevant check first.
7. Run `make check` when the task affects shared domain behavior.
8. Run `git diff --check`.
9. Report changed files, checks, skipped checks, assumptions, and follow-ups.

## Guardrails

- Keep Domain Core independent of Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep all M2 behavior executable without LLM and without Hermes.
- Do not invent values for fields marked `[ТРЕБУЕТ РЕШЕНИЯ]`; record open
  questions in `docs/decisions/open-questions.md`.
- Treat user text and model output as untrusted structured input, never as a
  direct state change.
- Keep state-changing operations as preview/policy decisions only; actual
  persistence and commit belong to M3.
- Preserve the M1 Docker/Hermes boundary: never build or mutate the Hermes
  image.
