---
name: m9-telegram-alpha
description: "Use when building the Menu Planner M9 Telegram Alpha slice: one authorized Telegram ID, Telegram user/session binding to user_id and WorkflowRun, message size and rate limits, timezone normalization, presentation layer for clarification/preview/warnings/status/errors/cancel/recipe view/shopping checklist, inline button and callback capability checks, confirmation_id-bound callbacks, repeated callback protection, parallel-message policy, restart recovery, Telegram E2E alpha scenarios, and M9 report, without public registration, multi-user production auth, real store integration, production hardening, direct Telegram commits, full payload callback data, or production model rollout."
---

# M9 Telegram Alpha workflow

## Scope

- Build only one-user Telegram Alpha up to Gate M9.
- Add or refine allowlist, session binding, message/rate limits, timezone
  normalization, presentation layer, callbacks, repeated callback protection,
  parallel-message policy, restart recovery, E2E alpha scenarios, and M9
  report.
- Use Hermes Telegram Gateway and existing Hermes plugin/Application API
  boundary.
- Do not implement public registration, multi-user production auth, real store
  integration, production hardening, direct Telegram commits, full payload
  callback data, or production model rollout.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m10-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
Telegram/Hermes boundary, Docker/runtime configuration, or when the brief is
insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 10.md`
- `docs/experiments/m8-hermes-plugin-integration.md`
- `docs/experiments/m8-hermes-runtime-api-discovery.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0011-hermes-plugin-integration.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation and actual Hermes/Telegram capability before
   editing Telegram integration code.
3. If allowlist source, Telegram ID handling, callback support, callback data
   shape, confirmation binding, parallel-message policy, timezone policy,
   restart recovery or E2E test surface is blocking, ask the user during that
   step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and verified Hermes image behavior.
6. Add the smallest testable change.
7. Run targeted presentation/session/callback tests first.
8. Run Telegram E2E alpha checks when the task changes gateway, callback,
   workflow recovery or user-facing flow behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine presentation, callback,
  fixture, or E2E-test changes when the brief and affected files are
  sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Free text never commits state directly.
- Meaningful changes require preview and confirmation tied to version and
  `confirmation_id`.
- Callback data must carry stable ids only, not full operation payloads.
- Repeated and stale callbacks must not duplicate state changes.
- Ambiguous text requires clarification or disambiguation.
- Telegram adapter does not import Domain Core or write Application DB.
- Keep public registration, multi-user production auth, real store integration
  and hardening out of M9.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
