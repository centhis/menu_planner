# M6B Agent Brief

Use this brief before routine Stage 7 / M6B tasks. Open full source documents
only when changing an ADR/stage plan, component boundary, or unresolved
product/model decision.

## Goal

M6B proves recipe drafts and local replacement of one menu slot behind the
safe M6A boundary:

```text
validated or confirmed menu version
-> RecipeDraft generation/validation
-> versioned recipe persistence
-> replace one meal slot
-> new menu draft/version with exact diff
-> stale confirmation protection
```

M6B does not implement shopping lists, store catalog, product matching,
Hermes plugin, Telegram UX, or production model dependency.

## Scope

Allowed:

- M6B Codex skill and stage report.
- ADR for recipe draft contract, recipe timing policy, replacement semantics,
  stale confirmation behavior, and model experiment boundaries.
- `RecipeDraft` contract, fixtures, deterministic validators, fake generator,
  and golden tests.
- Minimal confirmed-menu or accepted-menu fixture/path only if required for
  recipe and replacement safety.
- Versioned recipe persistence through the application boundary.
- Local replacement of exactly one meal slot as a new menu draft/version.
- Exact user-facing diff for replacement.

Forbidden:

- Shopping list, store catalog, product matching, prices, packages, aisle data,
  checklist UX, or unit arithmetic beyond recipe validation.
- Production Hermes plugin/tools/hooks/toolsets or Telegram UX.
- Direct model/fake output writes to confirmed state.
- Real provider credentials, `.env`, `auth.json`, tokens, or private user data.
- Treating M6A technical fixture values as final product semantics.

## Current Decisions

- M6A accepted one-day menu draft generation with deterministic fake generator.
- M6A skipped week draft expansion and model-backed generation.
- M6A preview does not activate a menu or write confirmed menu state.
- Recipe generation must be deterministic/fake-first unless a later ADR selects
  provider/model/prompt/logging policy.
- Replacement must be local: unaffected meal slots remain byte-for-byte or
  semantically unchanged according to the accepted contract.

## Checks

- Documentation/skill-only: `git diff --check` plus relevant validation.
- Contract/validator/generator changes: targeted unit/contract tests.
- Persistence/replacement/stale-confirmation changes: repository/application
  tests and focused regression tests.
- Stage gate: M6B golden/eval command plus lint/typecheck/smoke as needed.

## Message Economy

- For small scoped tasks, use one short update before edits and one final
  report.
- Read only files directly affected by the task plus this brief.
- Open full docs/ADRs only when the task requires their exact content.
