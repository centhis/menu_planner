---
name: m1-walking-skeleton
description: Use when building the Menu Planner M1 walking skeleton: app runtime, PostgreSQL, migrations, health checks, Makefile, tests, lint, and smoke checks, without business workflows.
---

# M1 walking skeleton workflow

## Scope

- Build only the empty reproducible application skeleton.
- Add PostgreSQL / Application DB plumbing.
- Add migrations, health/readiness checks, tests, lint/typecheck, and smoke.
- Do not implement profile, menu, recipes, shopping list, or production workflows.
- Do not create or modify a custom Hermes image.
- Build the application image when needed; never build the Hermes image.

## Required context

Read before acting:

- `AGENTS.md`
- `docs/implementation-plan.md`
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md`
- `docs/Stage 1.md`

## Work cycle

1. Restate the single task and acceptance criteria.
2. Identify files expected to change.
3. Inspect current implementation before editing.
4. Prefer the selected project toolchain and existing patterns.
5. Add the smallest testable change.
6. Run the narrowest relevant check.
7. Run `git diff --check`.
8. Report changed files, commands, passed checks, skipped checks, and
   remaining assumptions.

## Guardrails

- Keep Domain Core independent of Hermes and Telegram imports.
- Keep confirmed business state out of Hermes runtime state.
- Keep secrets out of Git and logs.
- Any Dockerfile must be for the application only and must not be named or
  used as a Hermes image.
- `docker compose build app` is allowed and expected when dependencies change.
- `docker compose build hermes` is forbidden.
