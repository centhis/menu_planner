# M9 Agent Brief

Use this brief before routine Stage 10 / M9 tasks. Open full source documents
only when changing an ADR/stage plan, Telegram/Hermes boundary, component
boundary, or unresolved UX/security decision.

## Goal

M9 proves one authorized user can complete the main scenario through Telegram
without any meaningful state change happening without linked preview and
confirmation:

```text
Telegram message/callback
-> Hermes Telegram Gateway
-> user/session/workflow binding
-> presentation layer
-> Hermes plugin/application tools
-> preview/confirmation
-> structured response
```

M9 does not implement public registration, multi-user production auth, real
store integration, production hardening, or broad admin UX.

## Scope

Allowed:

- M9 Codex skill and stage report.
- ADR for Telegram Alpha UX, allowlist, session binding, callbacks,
  confirmation binding, parallel-message policy, restart recovery, and E2E
  scenarios.
- One authorized Telegram ID.
- Telegram user/session binding to `user_id` and `WorkflowRun`.
- Message size/rate limits and timezone normalization.
- Presentation layer for clarification, preview, validation warnings, status,
  errors, cancel, recipe view and shopping checklist.
- Inline button/callback capability probe for the installed Hermes version.
- Callback data linked to `confirmation_id` or stable item/action ids, not full
  payloads.
- E2E alpha scenario through Telegram.

Forbidden:

- Public registration, multi-user production auth, payment/real store flows,
  real prices/availability, or production store integration.
- Letting Telegram callback text or free text commit without Application
  confirmation/version checks.
- Full payloads, secrets, credentials, `.env`, `auth.json`, private keys or
  tokens in callback data, logs, reports or diffs.
- Direct Telegram adapter imports of Domain Core or direct DB writes.
- Production observability, backup/restore, deployment hardening or dashboard
  auth replacement.

## Current Decisions

- M8 proved narrow Hermes plugin boundary and stops before Telegram Alpha.
- Hermes plugin/tools call Application HTTP API and do not import Domain Core.
- User-facing toolsets remain restricted by workflow state and role.
- Read-only actions may be shown without confirmation.
- Meaningful state changes require preview and confirmation tied to version
  and `confirmation_id`.
- Checklist status mutation requires exact item identity or disambiguation.

## Checks

- Documentation/skill-only: `git diff --check` plus relevant validation.
- Telegram capability discovery: record exact Hermes version/commands and
  failures.
- Presentation/callback/session changes: targeted unit/contract tests.
- Stage gate: Telegram E2E alpha command plus lint/typecheck/smoke as needed.

## Message Economy

- For small scoped tasks, use one short update before edits and one final
  report.
- Read only files directly affected by the task plus this brief.
- Open full docs/ADRs only when the task requires their exact content.
- For Telegram/Hermes details, inspect exact installed version instead of
  relying on assumptions.
