# M7 Shopping List and Mock Catalog Report

Date: 2026-07-12

Status: Gate M7 passed for the deterministic shopping-list and mock-catalog
slice.

## Goal

M7 proves that accepted menu/recipe versions and a reviewed mock catalog
snapshot can be transformed into a deterministic, versioned shopping list:

```text
confirmed menu + recipe versions + catalog snapshot
-> normalized ingredient quantities
-> deterministic unit conversion and merge
-> mock catalog matching
-> package and cost calculation
-> shopping list version
-> exact checklist item updates or controlled disambiguation
```

M7 intentionally stops before production Hermes plugin work, Telegram UX, real
store integration, production model-backed matching, and final price/
availability decisions.

## Scope

Implemented in scope:

- M7 Codex skill and M7 brief for routine implementation tasks.
- ADR-0010 shopping-list and mock-catalog strategy.
- Minimal normalized ingredient, unit definition, unit conversion, and
  shopping list version contracts with fixtures.
- Deterministic supported unit policy for mass, volume, and count.
- Controlled errors for unknown units and unsupported dimensions.
- Deterministic ingredient scaling, canonical conversion, and merge.
- `StoreCatalogProvider` interface and deterministic
  `MockStoreCatalogProvider`.
- Deterministic catalog matching by reviewed normalized ingredient ids.
- Controlled product ambiguity and missing product errors.
- Package count and cost calculation by code.
- Shopping list versions linked to source menu version, recipe version refs,
  and catalog snapshot id/version.
- Predictable shopping-list diff after one-slot replacement.
- Exact checklist updates by `shopping_item_id`.
- Controlled text disambiguation for checklist updates.
- M7 golden/eval command: `scripts/dev.sh m7-eval`.

Out of scope:

- Real store API, scraper, live prices, live availability, raw store HTML.
- Production Hermes plugin/tools/hooks/toolsets.
- Telegram business UX.
- Production model dependency or model-owned arithmetic/matching.
- Pantry, leftovers, owned-products inventory, substitutions, delivery fees,
  taxes, discounts, loyalty prices, and store-specific availability.

## Contract, Calculation, and Catalog Decisions

ADR-0010 accepts a deterministic technical slice:

- Shopping calculation may use only confirmed menu versions, recipe versions,
  reviewed mock catalog snapshots, and explicit command parameters.
- Unknown units, unknown dimensions, unsupported conversions, no matching
  product, ambiguous product match, invalid package shape, missing required
  price, stale shopping list version/hash, missing shopping item, and ambiguous
  checklist text all produce machine-readable controlled errors.
- Supported dimensions are `mass`, `volume`, and `count`.
- Supported units are `g`, `kg`, `ml`, `l`, and `piece`.
- Canonical units are `g`, `ml`, and `piece`.
- Ingredient quantities are scaled by `target_portions / recipe_portions`.
- Merging is by normalized ingredient id and dimension after canonicalization.
- Package count is `ceil(required_quantity / package_quantity)`.
- Cost calculation uses reviewed mock snapshot price/currency when present.
- Pantry and leftovers are zero by default in M7.

## Matching and Checklist Decisions

- Product matching is deterministic by explicit normalized ingredient ids in
  reviewed snapshot data.
- Multiple matching catalog products return a controlled ambiguity instead of
  choosing a product.
- Checklist status mutation requires an exact `shopping_item_id`.
- Text commands are resolved only by deterministic fields:
  `shopping_item_id`, `ingredient_id`, `product_id`, and `display_name`.
- One clear text match may delegate to the exact item updater.
- Multiple text matches return disambiguation candidates and do not mutate
  state.
- No text match returns a controlled missing-item error.
- The M7 slice does not implement Telegram UI for choosing a candidate.

## Property and Eval Metrics

Code-level tests cover:

- unit conversion and unsupported units/dimensions;
- deterministic scaling and merge;
- merge ordering and associativity for disjoint groups;
- mock catalog snapshot validation and raw-field rejection;
- deterministic product matching, no-match, and ambiguous-match behavior;
- package count, package quantity, price, and missing-price behavior;
- shopping-list version identity and source hash changes;
- replacement diff added/removed/quantity-changed items;
- exact checklist updates, stale protection, idempotence, and missing item;
- text one-match, multiple-match disambiguation, and no-match behavior.

M7 eval command result:

```text
scripts/dev.sh m7-eval -> failures: 0
```

Eval metrics were green for:

- normalized unit conversion;
- ingredient scaling/merge;
- mock catalog snapshot matching;
- package/cost calculation;
- shopping list version identity;
- replacement diff;
- exact checklist update;
- one-match text update;
- ambiguous text disambiguation;
- no-match controlled error;
- no confirmed-state mutation;
- no external provider requirement;
- no credential reads.

## Verification Commands

Commands run for the final M7 checks:

```text
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh m7-eval
git diff --check
```

Results:

```text
scripts/dev.sh test      -> 247 passed
scripts/dev.sh lint      -> All checks passed
scripts/dev.sh typecheck -> Success: no issues found in 99 source files
scripts/dev.sh m7-eval   -> failures: 0
git diff --check         -> ok
```

The Docker-based commands require Docker socket access in this sandbox and
were run with explicit approval. Secret files such as `.env`, `auth.json`,
tokens, and credentials were not opened or displayed.

`scripts/dev.sh smoke` was not run during the final M7 report step because M7
changed deterministic application/eval behavior, not the runtime smoke path.

## Gate M7 Result

Result: passed for the deterministic shopping-list and mock-catalog slice.

M7 proves the current technical path from menu/recipe/catalog versions to
shopping-list versions, replacement diffs, exact checklist updates, and
controlled text disambiguation. It does not prove production catalog quality,
real store availability, live prices, production checklist UX, pantry/leftover
semantics, production model-backed matching, or Telegram/Hermes adapter UX.

Do not proceed to Hermes plugin, Telegram UX, real store integration, live
prices/availability, production model-backed matching, or scraper work without
a separate user task and explicit decisions.

## Gate M7 Checklist

[x] M7 Codex skill exists and was used for implementation tasks.
[x] M7 brief exists and was used for routine tasks.
[x] ADR-0010 or equivalent decision note fixes shopping-list strategy.
[x] Normalized ingredient and unit contracts have schema_version and fixtures.
[x] Unknown unit returns controlled error, not guess.
[x] Unsupported dimension returns controlled error, not guess.
[x] Ingredient scaling and merging are deterministic.
[x] Unit/package/rounding property tests pass.
[x] MockStoreCatalogProvider returns deterministic snapshot data.
[x] Product matching is fixed or explicitly confirmable.
[x] Shopping list version links to menu version and catalog snapshot.
[x] Same inputs create the same shopping list.
[x] Shopping-list arithmetic is not performed by a model.
[x] One-slot replacement creates predictable shopping-list diff.
[x] Checklist item status changes only by exact item id or disambiguated match.
[x] Ambiguous text checklist update requires disambiguation.
[x] Failure leaves confirmed menu, recipes and shopping list state unchanged.
[x] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[x] No real store integration, raw store HTML, production Hermes plugin,
    Telegram UX, or production model dependency added.
[x] `scripts/dev.sh test` passed.
[x] `scripts/dev.sh lint` passed.
[x] `scripts/dev.sh typecheck` passed.
[x] M7 golden/eval command passed.
[x] `git diff --check` passed.

## Remaining Assumptions

- The normalized ingredient dictionary is a technical M7 fixture boundary, not
  the final product taxonomy.
- The supported unit table is intentionally small.
- Cross-dimension conversions, density conversions, and natural-language unit
  inference are not accepted.
- Pantry and leftovers are assumed empty.
- Mock catalog prices are reviewed fixture data only.
- Missing price is controlled and does not block unpriced list generation.
- Text checklist matching is deterministic and limited to normalized item
  fields; production language UX is not selected.
- The current checklist update implementation is application-level and
  side-effect free; persistence/adapter behavior needs a later explicit task.

## Decision Point: Prices and Availability in MVP

M7 leaves the price/availability product decision open. Before production
shopping workflows, decide:

- whether MVP shopping lists show prices at all;
- whether prices are static reviewed estimates or live store prices;
- whether availability is hidden, static, or live;
- whether missing price should block list generation, display an unknown
  value, or require user confirmation;
- whether taxes, delivery fees, discounts, loyalty prices, substitutions, and
  store-specific package preferences are in MVP.

The related open question is `OQ-008` in
`docs/decisions/open-questions.md`.

## Decisions Required Before Hermes Plugin or Real Store Integration

Before starting Hermes plugin, Telegram UX, real store integration, scraper
work, or production model-backed matching, explicitly decide:

- final ingredient and product taxonomy;
- real catalog provider strategy;
- raw catalog artifact retention and sanitization policy;
- live price/availability policy;
- pantry/leftovers semantics;
- checklist disambiguation UX and confirmation copy;
- adapter-level identity, stale-version, and audit boundaries;
- whether any model-backed catalog matching is allowed and how it is evaluated.

Until those decisions are made, keep M7 shopping-list calculation deterministic,
mock-catalog-only, and adapter-independent.
