---
name: m8-hermes-plugin-integration
description: "Use when building the Menu Planner M8 Hermes plugin integration slice: actual Hermes API discovery, reproducible plugin packaging, narrow tools, strict tool schemas, structured tool results, toolsets, pre-message and pre-tool hooks, versioned Hermes runtime skills, DB/API context sourcing, agentic and guided modes, fake model integration tests, prompt-injection tests, and M8 report, without Telegram Alpha, custom Hermes image, mutable container installs, real store integration, direct DB writes from Hermes, admin tools in user toolsets, or production model rollout."
---

# M8 Hermes plugin integration workflow

## Scope

- Build only Hermes plugin integration up to Gate M8.
- Inspect actual Hermes version, CLI help, plugin API, and image behavior
  before implementing. Do not invent Hermes APIs by analogy.
- Add or refine plugin adapter, narrow tools, tool schemas, tool results,
  toolsets, hooks, runtime skills, application context sourcing, fake model
  tests, prompt-injection tests, and M8 report.
- Use Application HTTP API for domain operations. Do not import Domain Core
  directly from Hermes plugin/tools.
- Do not implement Telegram Alpha, real store integration, custom Hermes image,
  mutable container installation, admin tools in user toolsets, or production
  model rollout.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m9-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
Hermes boundary, Docker/runtime configuration, or when the brief is
insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 9.md`
- `docs/experiments/m7-shopping-list-and-mock-catalog.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `docs/decisions/ADR-0010-shopping-list-and-mock-catalog.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation and actual Hermes runtime/API before editing
   Hermes integration code.
3. If plugin API, packaging, tool naming, hook semantics, toolset config,
   context source, model/provider, fake model strategy, or guided/agentic mode
   is blocking, ask the user during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and verified Hermes image behavior.
6. Add the smallest testable change.
7. Run targeted schema/tool/hook tests first.
8. Run M8 integration/eval checks when the task changes plugin behavior,
   toolsets, hooks, runtime skills, or agent workflow behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine tool schema, fixture, hook,
  or skill changes when the brief and affected files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Hermes is runtime/adapter, not source of domain authority.
- Free text never calls arbitrary tools directly.
- User toolsets must not expose terminal, arbitrary filesystem/browser, SQL,
  secrets, model/toolset/skill modification, or admin MCP tools.
- Hooks are defense in depth; handlers/application services repeat critical
  checks.
- Memory does not replace Application DB for critical state.
- Business rules must not live only in Hermes skills/prompts.
- Keep Domain Core independent from Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
