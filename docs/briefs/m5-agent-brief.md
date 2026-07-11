# M5 Agent Brief

Use this brief before routine M5 tasks. Open the full source documents only
when changing an ADR/stage plan, component boundary, or unresolved decision.

## Goal

M5 proves a measured Intent Router and eval harness:

```text
user text -> ParsedIntent or controlled error -> PolicyDecision
```

The router must not execute commits, write confirmed state, create
confirmations, call Hermes tools, call Telegram callbacks, or generate menus.

## Scope

Allowed:

- M5 intent taxonomy tied to existing `WorkflowAction` values.
- Versioned eval datasets and development/holdout split.
- Eval runner, metrics, reports, and safety regression tests.
- Deterministic/rule-based baseline router.
- Optional model-backed experiment only if ADR-0007 explicitly selects it.
- Policy decision through existing workflow/policy code.

Forbidden:

- Direct commit from router output.
- Menu generation, recipes, shopping list, store catalog, substitutions.
- Production Hermes plugin/tools/hooks/toolsets or Telegram UX.
- New production model/API dependency without explicit decision.
- Reading, logging, or displaying `.env`, `auth.json`, tokens, credentials, or
  private user data.

## Current Decisions

- ADR-0007 places the M5 router in the Application layer.
- `rule_based_baseline` is the Gate M5 target unless later evidence changes
  the decision.
- `model_backed_candidate` is deferred unless explicitly approved.
- Future menu/recipe/shopping intents are unsupported or deferred in M5.
- Hard safety threshold: dangerous state-changing/admin false automatic
  execution rate is `0`.
- Self-reported confidence is diagnostic only and not execution permission.

## Checks

- Documentation/skill-only: `git diff --check` plus relevant validation.
- Dataset/router behavior changes: targeted unit tests and M5 eval command.
- Shared/risky/stage-gate changes: add lint/typecheck/smoke as needed.

## Message Economy

- For small scoped tasks, use one short update before edits and one final
  report.
- Read only files directly affected by the task plus this brief.
- Open full docs/ADRs only when the task requires their exact content.
