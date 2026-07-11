# M6A Agent Brief

Use this brief before routine M6A tasks. Open full source documents only when
changing an ADR/stage plan, component boundary, or unresolved product/model
decision.

## Goal

M6A proves menu draft generation and validation behind the safe M4/M5 boundary:

```text
confirmed profile + explicit planning request
-> PlanningContext
-> MenuDraftGenerator
-> MenuDraft
-> validation
-> optional OperationPreview
```

M6A does not activate a menu directly and does not implement recipes,
shopping lists, store catalog, substitutions, Hermes plugin, or Telegram UX.

## Scope

Allowed:

- M6A Codex skill and stage report.
- ADR for menu draft contract, generation policy, validation, repair loop, and
  model/provider experiment boundaries.
- `PlanningContext`, `MenuDraft`, `MealSlot`, and validator refinements.
- Deterministic fake generator and golden fixtures.
- Bounded repair loop using structured validation errors.
- Optional model-backed generation experiment only after explicit ADR/user
  decision.
- Preview for a validated menu draft if it does not bypass confirmation or
  commit safety.

Forbidden:

- Menu activation/commit directly from model output.
- Recipe generation, substitutions, shopping list, store catalog.
- Production Hermes plugin/tools/hooks/toolsets or Telegram UX.
- Real provider credentials, `.env`, `auth.json`, tokens, or private user data.
- Treating ADR-0006 profile fixture values as final product semantics.

## Current Decisions

- M5 accepts conservative application-layer routing and keeps menu intents
  unsupported/deferred until M6 contracts/workflows exist.
- Model-backed routing is not accepted by M5.
- OQ-004 final profile schema remains open.
- M6A should start with a deterministic fake generator and only add a real
  model experiment if provider/model/prompt/logging decisions are explicit.
- Hard safety invariant: invalid or unconfirmed menu drafts never become active
  confirmed state.

## Checks

- Documentation/skill-only: `git diff --check` plus relevant validation.
- Contract/validator/generator changes: targeted unit/contract tests.
- Repair/golden workflow changes: golden tests and any M6A eval command.
- Shared/risky/stage-gate changes: add lint/typecheck/smoke as needed.

## Message Economy

- For small scoped tasks, use one short update before edits and one final
  report.
- Read only files directly affected by the task plus this brief.
- Open full docs/ADRs only when the task requires their exact content.
