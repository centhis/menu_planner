# M9.5 Agent Brief

Use this brief before routine Stage 10.5 tasks. Open full source documents only
when changing an ADR/stage plan, Telegram/Hermes boundary, component boundary,
or unresolved UX/security decision.

## Goal

Stage 10.5 turns synthetic Telegram Alpha into a live, visible Telegram UX
sandbox:

```text
real Telegram message/callback
-> Hermes Telegram Gateway
-> Menu Planner plugin or UX sandbox adapter
-> visible Telegram screen/state
-> user feedback
-> UX correction
-> sanitized evidence and decisions
```

The user must be able to see screens in Telegram, click inline buttons, request
changes, receive UX advice during corrections, and approve or defer the first
UI/UX decisions.

## Scope

Allowed:

- Stage 10.5 Codex skill and report.
- Live Telegram UX sandbox for one authorized Telegram ID.
- Demo/synthetic data for UI states when production backend flow is not ready,
  clearly labeled as demo and not active state.
- Clickable prototypes for all key Telegram states.
- UX co-design loop: show screen in Telegram, explain UX logic, suggest 1-3
  improvements, ask user, revise, show again.
- UX guidance on free text, inline buttons, button-only actions, preview,
  confirmation, disambiguation, long text splitting, and Mini App tradeoffs.
- User review checklists for manual Telegram verification.
- Sanitized report with shown states, user feedback, accepted decisions, and
  open questions.

Forbidden:

- New product features outside the UX sandbox.
- MVP hardening, public registration, multi-user production auth, observability,
  backup/restore, real store integration, live prices/availability, or
  production model rollout.
- Reading or printing `.env`, `auth.json`, bot tokens, credentials, private
  keys, or private user data.
- Full operation payloads or secrets in callback data.
- Direct Telegram commits without preview/confirmation and Application checks.

## Checks

- Documentation/skill-only: `git diff --check` plus relevant validation.
- UX sandbox changes: targeted presentation/callback tests.
- Live checks: user-visible Telegram smoke, inline-button smoke, callback
  smoke, and manual checklist confirmation with sanitized evidence.

## Message Economy

- For small scoped tasks, use one short update before edits and one final
  report.
- Read only files directly affected by the task plus this brief.
- Ask the user when live Telegram token, Docker socket, Telegram ID, or UX
  approval is needed.
