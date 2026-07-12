# M8 Agent Brief

Use this brief before routine Stage 9 / M8 tasks. Open full source documents
only when changing an ADR/stage plan, Hermes boundary, component boundary, or
unresolved runtime/model decision.

## Goal

M8 proves a narrow Hermes plugin boundary without handing Domain Core
authority to Hermes:

```text
Hermes message/runtime context
-> pre-message policy
-> structured intent / clarification
-> restricted toolset
-> pre-tool policy
-> Hermes tool adapter
-> Application HTTP API
-> Domain/Application checks
-> structured tool result
```

M8 does not implement Telegram Alpha, real store integration, production model
rollout, or custom Hermes image work.

## Scope

Allowed:

- M8 Codex skill and stage report.
- ADR for Hermes plugin packaging, tool boundary, hooks, toolsets, runtime
  skills, context sourcing, guided/agentic modes, fake model tests, and
  prompt-injection tests.
- Inspect actual Hermes version, CLI help, plugin API and local image behavior
  before implementing. Do not invent Hermes APIs by analogy.
- Adapter between Hermes plugin tools and Application HTTP API.
- Narrow tools with strict input/output schemas and structured results.
- Toolsets split by workflow state and role.
- Pre-message and pre-tool policy hooks.
- Versioned Hermes runtime skills for local model tasks, with no business
  rules stored only in prompts.
- Fake model/provider integration tests and one bounded agent workflow.

Forbidden:

- Custom Hermes image, `docker build` for Hermes, `docker commit`, `docker cp`
  installation, package installation inside container, or manual edits inside a
  running Hermes container.
- Telegram business UX, inline buttons, callbacks, allowlist production UX.
- Real store API/scraping, raw store HTML, live prices/availability.
- Direct Hermes writes to Application DB or Domain Core imports from plugin.
- Administrative tools in user toolsets: terminal, arbitrary filesystem,
  browser, SQL, model/toolset/skill modification, secrets.
- Reading `.env`, `auth.json`, tokens, credentials, or private user data.

## Current Decisions

- Hermes is the agent runtime, not the owner of business rules or persistence.
- Domain Core remains independent from Hermes and Telegram.
- Application service owns DB schema, repositories, migrations and transaction
  boundary.
- Hermes plugin/tools are adapters and must call Application HTTP API.
- Memory can support conversation convenience but never replaces Application
  DB for critical state.
- M7 leaves real store integration and Telegram UX out of scope.

## Checks

- Documentation/skill-only: `git diff --check` plus relevant validation.
- Hermes API discovery: record exact version/commands inspected and failures.
- Tool/schema/hook changes: targeted contract tests and handler tests.
- Stage gate: M8 integration/fake-agent command plus lint/typecheck/smoke as
  needed.

## Message Economy

- For small scoped tasks, use one short update before edits and one final
  report.
- Read only files directly affected by the task plus this brief.
- Open full docs/ADRs only when the task requires their exact content.
- For Hermes API details, inspect exact local version instead of loading broad
  unrelated docs.
