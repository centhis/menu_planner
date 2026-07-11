# M7 Agent Brief

Use this brief before routine Stage 8 / M7 tasks. Open full source documents
only when changing an ADR/stage plan, component boundary, or unresolved
product/provider decision.

## Goal

M7 proves deterministic shopping-list calculation from accepted menu and
recipe versions:

```text
confirmed menu + recipe versions + catalog snapshot
-> normalized ingredient quantities
-> deterministic unit conversion and merge
-> mock catalog matching
-> package and cost calculation
-> shopping list version
-> precise checklist item updates
```

M7 does not implement real store integration, Hermes plugin, Telegram UX,
model-based arithmetic, or product-quality catalog matching.

## Scope

Allowed:

- M7 Codex skill and stage report.
- ADR for shopping-list contracts, unit policy, mock catalog snapshot,
  matching policy, versioning, checklist updates, and disambiguation.
- Normalized ingredients, supported units/dimensions, deterministic
  conversions, scaling by portions, merging, packaging and cost calculations.
- `StoreCatalogProvider` interface and deterministic `MockStoreCatalogProvider`
  with reviewed snapshots.
- Shopping list version linked to menu version and catalog snapshot.
- Exact checklist item updates by ID.
- Controlled disambiguation for text commands with multiple matches.
- Property tests for units, packages, and rounding.

Forbidden:

- Real store API/scraping, live prices, live availability, raw store HTML, or
  production catalog integration.
- Model-performed arithmetic, matching, rounding, packaging, or checklist
  state mutation.
- Production Hermes plugin/tools/hooks/toolsets or Telegram UX.
- Direct model/fake output writes to confirmed state.
- Reading `.env`, `auth.json`, tokens, credentials, or private user data.

## Current Decisions

- M6B recipes are versioned through the application boundary.
- M6B replacement is local and records `shopping_list_impact: none` until M7.
- M7 must make replacement impact on shopping list predictable and testable.
- Store/catalog data is untrusted unless represented as reviewed normalized
  snapshot data.
- Unknown units or dimensions must produce controlled errors, not guesses.

## Checks

- Documentation/skill-only: `git diff --check` plus relevant validation.
- Contract/calculation changes: targeted unit/contract/property tests.
- Catalog/checklist/versioning changes: repository/application tests and
  focused regression tests.
- Stage gate: M7 golden/eval command plus lint/typecheck/smoke as needed.

## Message Economy

- For small scoped tasks, use one short update before edits and one final
  report.
- Read only files directly affected by the task plus this brief.
- Open full docs/ADRs only when the task requires their exact content.
