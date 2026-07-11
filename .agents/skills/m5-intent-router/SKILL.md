---
name: m5-intent-router
description: "Use when building the Menu Planner M5 Intent Router and eval harness: intent taxonomy, versioned eval datasets, router candidates, ParsedIntent validation, policy decisions, ambiguity handling, safety metrics, and M5 reports, without menu generation, Hermes plugin, Telegram UX, recipes, shopping list, or direct commit."
---

# M5 Intent Router workflow

## Scope

- Build only the measured Intent Router and eval harness.
- Convert user text into schema-valid `ParsedIntent`, controlled errors, and
  `PolicyDecision`.
- Reuse existing Domain Core contracts, workflow policy, operation classes,
  stable errors, and M4 profile flow boundaries.
- Add versioned eval datasets, runner, metrics, and safety tests.
- Do not execute commits, generate menus/recipes, create shopping lists, build
  production Hermes plugin/tools, or add Telegram UX.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m5-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
or when the brief is insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 5.md`
- `docs/experiments/m4-profile-vertical-slice.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0006-profile-vertical-slice.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If router placement, model/provider choice, confidence threshold, or
   dangerous-action policy is blocking, ask the user during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run the narrowest relevant checks first.
8. Run M5 eval checks when the task changes router behavior or dataset.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine fixture, test, or router
  changes when the brief and affected files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Router returns intent/policy/error only; it must not commit application
  state.
- Workflow policy remains the authority for allowed actions and confirmation.
- State-changing intents require preview/confirmation and never direct commit.
- Administrative intents are denied in user workflow.
- Self-reported confidence is not trusted without eval calibration.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
