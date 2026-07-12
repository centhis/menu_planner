---
name: m7-shopping-list-catalog
description: "Use when building the Menu Planner M7 deterministic shopping list and mock catalog slice: normalized ingredients, supported units, deterministic conversions, portion scaling, ingredient merging, StoreCatalogProvider, MockStoreCatalogProvider snapshots, package and cost calculation, shopping list versions, checklist item updates, disambiguation, property tests, and M7 report, without real store integration, raw store HTML, Hermes plugin, Telegram UX, model arithmetic, or production model dependency."
---

# M7 shopping list and mock catalog workflow

## Scope

- Build only deterministic shopping list and mock catalog up to Gate M7.
- Add or refine normalized ingredients, units, conversions, catalog snapshot,
  product matching, package/cost calculation, shopping list versioning,
  checklist updates, disambiguation, golden/property tests, and M7 report.
- Use confirmed menu/recipe versions and reviewed catalog snapshots only.
- Do not implement real store integration, raw store scraping, production
  Hermes plugin/tools, Telegram UX, model arithmetic, or production model
  dependency.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m8-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
or when the brief is insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 8.md`
- `docs/experiments/m6b-recipes-and-replacements.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0009-recipes-and-replacements.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If normalized ingredient taxonomy, unit dimensions, pantry/leftovers,
   product matching, package rounding, prices/availability, checklist
   disambiguation, or versioning policy is blocking, ask the user during that
   step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run targeted unit/contract/property tests first.
8. Run M7 eval/golden checks when the task changes shopping calculation,
   catalog matching, checklist behavior, or replacement diff behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine fixture, conversion,
  property-test, mock-catalog, or checklist changes when the brief and affected
  files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Shopping-list arithmetic is code-owned and deterministic.
- Unknown units or dimensions produce controlled errors.
- Model/fake output must never calculate packages, prices, or checklist state.
- Shopping list versions must link to menu version and catalog snapshot.
- Checklist mutation requires exact item identity or disambiguation.
- Keep real store integration and raw HTML out of M7.
- Keep Domain Core independent from Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
