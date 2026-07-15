---
name: m9-live-telegram-ux-sandbox
description: "Use when building the Menu Planner Stage 10.5 live Telegram UX sandbox slice: real Telegram round-trip, one authorized Telegram ID, user-visible Telegram screens, clickable inline buttons, live callback smoke, demo/synthetic data labeling, UX co-design loop, UX guidance during corrections, Mini App decision checkpoint, user review checklists, sanitized evidence, and Stage 10.5 report, without new product features, MVP hardening, production auth, observability, backup/restore, real store integration, live prices/availability, production model rollout, secrets in logs, full payload callback data, or direct Telegram commits."
---

# Stage 10.5 live Telegram UX sandbox workflow

## Scope

- Build only the live Telegram UX sandbox up to Gate Stage 10.5.
- Make screens visible in Telegram before treating UX as accepted.
- Allow demo/synthetic data only when clearly labeled as demo and not active
  state.
- Add or refine sandbox entry, visible states, inline buttons, callback smoke,
  UX co-design loop, UX guidance, Mini App decision checkpoint, user review
  checklists, sanitized evidence, and Stage 10.5 report.
- Do not add new product features outside the UX sandbox.
- Do not implement MVP hardening, public registration, multi-user production
  auth, observability, backup/restore, real store integration, live
  prices/availability, or production model rollout.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m10-5-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
Telegram/Hermes boundary, Docker/runtime configuration, or when the brief is
insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 10.5.md`
- `docs/Stage 10.md`
- `docs/experiments/m9-telegram-alpha.md`
- `docs/experiments/m9-telegram-capability-discovery.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0011-hermes-plugin-integration.md`
- `docs/decisions/ADR-0012-telegram-alpha.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation and actual Telegram/Hermes runtime when the
   task touches live behavior.
3. If Telegram token, Telegram ID, Docker socket, screenshot policy, callback
   support, UX preference, or Mini App decision is blocking, ask the user
   during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and verified Hermes image behavior.
6. Add the smallest testable change.
7. For UX-visible work, show the current screen in Telegram, explain UX logic,
   suggest 1-3 improvements, ask for feedback, apply or defer feedback, and
   show the updated screen.
8. Run targeted presentation/callback/sandbox tests first.
9. Run live Telegram smoke/callback checks only with user approval and without
   printing secrets.
10. Run `git diff --check`.
11. Report changed files, commands, passed checks, skipped checks,
    assumptions, user feedback, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine screen, callback, checklist,
  or report edits when the brief and affected files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## UX guardrails

- The user must see and click the UX in Telegram before Stage 10.5 closes.
- Draft and active state must be visually distinct.
- State-changing actions require preview and confirmation.
- Confirmation buttons link to stable `confirmation_id`; callback data must not
  contain full operation payloads.
- Checklist updates use stable item ids.
- Ambiguous text routes to disambiguation, not guessing.
- Long previews and diffs should be summarized or split across messages.
- Give short UX advice during corrections, including when a Mini App may help
  and when it is premature for Alpha.

## Safety guardrails

- Live Telegram token, `.env`, `auth.json`, credentials, private keys and
  private user data must not be printed or written to reports.
- Repeated and stale callbacks must not duplicate state changes.
- Telegram adapter must not import Domain Core or write Application DB.
- Keep real store integration, live prices/availability and production
  hardening out of Stage 10.5.
- Keep sanitized evidence in reports: screenshots or textual descriptions must
  not expose secrets or private identifiers.
