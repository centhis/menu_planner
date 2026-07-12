# ADR-0010: Shopping list and mock catalog strategy

Date: 2026-07-11

Status: Accepted

## Context

Stage 8 / M7 must add deterministic shopping-list calculation and a reviewed
mock catalog after M6B proved versioned recipes and local one-slot replacement.

M7 must not hide real store integration, raw store scraping, Hermes/Telegram
UX, production model matching, or model-owned arithmetic inside the shopping
calculation. Confirmed menu and recipe versions remain the source boundary;
external catalog data is untrusted unless represented as a reviewed normalized
snapshot.

## Decision

Use a minimal deterministic M7 slice:

```text
confirmed menu version + recipe versions + mock catalog snapshot
-> normalized ingredient quantities
-> deterministic unit conversion and merge
-> deterministic mock catalog matching
-> package and cost calculation by code
-> shopping list version linked to menu version and catalog snapshot
-> exact checklist updates by shopping_item_id
```

M7 does not implement real store APIs, scrapers, live prices, live availability,
raw store HTML, production Hermes plugin/tools, Telegram UX, production model
dependency, or model-performed arithmetic/matching.

### Source policy

Shopping-list calculation may use only:

- confirmed menu versions;
- validated and persisted recipe versions linked to that menu;
- reviewed mock catalog snapshot data;
- explicit command parameters.

It must not use Hermes memory, raw Telegram text, unverified model output,
live store pages, secrets, private runtime state, or external network data.

Building a shopping list must not mutate confirmed menu or recipe state.

### Normalized ingredient and unit model

M7 will introduce a minimal normalized ingredient model with:

- `schema_version`;
- stable normalized ingredient id;
- display name;
- quantity;
- unit;
- supported dimension.

The first deterministic slice may use a small reviewed ingredient dictionary
derived from M6B synthetic recipe fixtures. This dictionary is a technical
test boundary, not the final product taxonomy.

Unknown ingredient ids, unknown units, unsupported dimensions, or incompatible
unit conversions must return controlled machine-readable errors rather than
guessing.

### Supported units and conversion policy

M7 supports only explicitly listed units inside explicitly listed dimensions.

The initial technical dimensions are:

- mass;
- volume;
- count.

Conversion is allowed only within the same dimension and only through a
reviewed conversion table. Cross-dimension conversion, density-based
conversion, locale-specific package semantics, and natural-language unit
inference are out of M7 unless explicitly added by a later decision.

### Scaling, merging, and rounding policy

Ingredient quantities are scaled by deterministic numeric ratio:

```text
target_portions / recipe_portions
```

M7 may assume target portions equal recipe portions until a later task adds an
explicit serving-scaling command.

Merging combines identical normalized ingredient ids after conversion to the
canonical unit for that dimension. Ordering must be stable.

Rounding is code-owned. M7 must choose deterministic rounding rules for:

- displayed ingredient quantities;
- package counts;
- price/cost totals when price exists in the mock snapshot.

Model output must never perform rounding, package calculation, or price math.

### Pantry and leftovers policy

Pantry and leftovers are zero by default in M7.

No pantry inventory, leftovers deduction, substitution, owned-products list, or
implicit "already have it" behavior is accepted in this ADR. These sources may
be added only after a later product decision defines ownership, freshness,
quantity, expiration, and user-confirmation semantics.

### StoreCatalogProvider contract

Application code owns the catalog provider boundary.

M7 will define a `StoreCatalogProvider` interface that returns reviewed
catalog snapshot data. The provider must not fetch live store data during M7
calculation.

Provider output is untrusted until validated against the mock catalog snapshot
contract.

### Mock catalog snapshot shape and versioning

The M7 mock catalog snapshot must include:

- `schema_version`;
- snapshot id;
- snapshot version or created-at metadata;
- catalog items with stable ids;
- normalized ingredient ids supported by each item;
- package quantity and package unit;
- optional price/currency fields if accepted by tests;
- optional aisle/category fields only if needed for deterministic display.

Snapshot id and version are part of shopping-list identity and preview/hash
inputs. The same menu, recipe versions, and catalog snapshot must produce the
same shopping list.

### Product matching policy

M7 product matching is deterministic and fixed by reviewed mapping.

An ingredient may match:

- exactly one catalog item by explicit normalized ingredient id; or
- a controlled ambiguity result requiring confirmation/disambiguation.

M7 must not infer products from free text, model output, raw store pages,
prices, descriptions, or fuzzy matching unless a later decision accepts that
behavior with eval evidence.

If multiple catalog items match a normalized ingredient and no deterministic
default is accepted, M7 returns a controlled ambiguity instead of selecting a
product.

### Package and cost calculation policy

Package calculation is deterministic code:

```text
package_count = ceil(required_quantity / package_quantity)
```

Only same-dimension quantities may be compared. Package count is an integer.

Cost calculation is allowed only when the mock snapshot contains reviewed
price and currency for the selected catalog item. Missing price is controlled
and must not block shopping-list generation unless a later task requires
priced lists.

Live price, live availability, discounts, loyalty pricing, taxes, delivery
fees, and substitutions are out of M7.

### Shopping list versioning

A shopping list version must link to:

- user id;
- shopping list id;
- shopping list version;
- source menu id and version;
- recipe version ids used for calculation;
- catalog snapshot id and version;
- generated shopping items.

Creating a shopping list version must run through the application boundary.
Failure must leave confirmed menu, recipe versions, and existing shopping-list
state unchanged.

### Checklist update and disambiguation policy

Checklist state changes must target exact `shopping_item_id`.

Text commands such as "milk bought" are not allowed to mutate checklist state
directly when multiple items could match. They must return a controlled
disambiguation response listing candidate item ids or request a precise
selection through a later adapter UX.

M7 does not implement production Telegram checklist UX.

### Replacement impact and diff policy

After one-slot replacement, shopping-list recalculation must be predictable:

- only recipe/ingredient inputs affected by the replaced slot may change;
- unchanged ingredients remain stable after sorting and canonicalization;
- the shopping-list diff must show added, removed, and changed shopping items;
- the diff must include source menu version, recipe version ids, and catalog
  snapshot id/version.

Replacement must not mutate confirmed menu or recipe state while calculating
shopping-list impact.

### Model/provider/raw-output policy

No model-backed product matching or shopping-list generation is accepted by
this ADR.

Any later model-backed experiment must separately choose provider/model,
prompt/schema versioning, credentials handling, raw-output retention,
sanitization, eval dataset, cost/latency reporting, and deterministic fallback
behavior.

## Consequences

- M7 can be verified without Hermes, Telegram, external model providers,
  network access, live store APIs, or secrets.
- Unit conversion, package counts, cost totals, and checklist mutation remain
  deterministic and testable.
- Mock catalog snapshots can support repeatable tests while keeping real store
  integration out of scope.
- Final product taxonomy, matching quality, prices/availability, pantry, and
  production UX remain explicit future decisions.

## Not Decided Here

- Final ingredient taxonomy.
- Final unit system beyond the M7 technical table.
- Density conversion or cross-dimension conversion.
- Pantry, leftovers, owned products, and substitution semantics.
- Real store provider, scraper, API, or raw HTML handling.
- Live price and availability policy.
- Production product matching, fuzzy matching, or model-backed matching.
- Taxes, discounts, loyalty pricing, delivery fees, or budget optimization.
- Production checklist UX in Hermes/Telegram.
- Production model/provider/prompt choice for catalog or shopping behavior.
