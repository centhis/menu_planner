# ADR-0009: Recipes and replacements strategy

Date: 2026-07-11

Status: Accepted

## Context

Stage 7 / M6B must extend the safe M6A menu-draft boundary with recipe drafts
and local replacement of exactly one meal slot.

M6A proved deterministic one-day menu draft generation, validation, bounded
repair, and safe preview without activating a menu or writing confirmed menu
state. M6B must not turn fake or model output into confirmed state directly.
Recipe and replacement outputs are untrusted until deterministic validation
accepts them.

M6B must also avoid hiding shopping-list, store-catalog, product matching,
Hermes/Telegram, or production model decisions inside recipe implementation.

## Decision

Use a minimal M6B slice for recipe drafts and one-slot replacement.

The M6B flow is:

```text
accepted menu fixture or confirmed menu version
-> deterministic fake RecipeDraftGenerator
-> RecipeDraft
-> deterministic recipe validation
-> versioned recipe persistence through application boundary
-> explicit one-slot replacement request
-> new menu draft/version with exact replacement diff
-> stale confirmation protection
```

M6B does not implement shopping lists, store catalog, product matching, prices,
packages, aisle data, production Hermes plugin, Telegram UX, production model
dependency, or direct activation from fake/model output.

### Accepted menu source policy

M6B may start from an accepted menu fixture derived from the M6A technical
shape, or from a minimal confirmed-menu path if persistence/replacement tests
need one.

The accepted menu source must be:

- validated before use;
- explicit in tests or application commands;
- independent from Hermes memory, raw Telegram text, unverified model output,
  secrets, or private runtime state.

M6B does not select the final production menu activation workflow. If a
minimal confirmed-menu path is added, it is a technical test boundary for
recipes and replacement safety, not the final product activation flow.

### Recipe timing policy

Recipes may be generated after an accepted or confirmed menu boundary exists.

M6B may also support explicit pre-generation for a validated menu draft only
as a technical test path if the output cannot become confirmed recipe state
without validation and application persistence.

Recipes must not be generated implicitly from router text, Hermes memory, or
model output. Recipe generation must not mutate the active menu by itself.

### RecipeDraft schema and versioning

M6B will add or refine a minimal `RecipeDraft` contract with:

- `schema_version`;
- `user_id`;
- `draft_id`;
- status;
- source menu/menu-slot reference;
- title;
- portions;
- ingredients with quantity and unit fields;
- equipment;
- active and total time;
- steps;
- storage and reheating metadata.

Recipe versioning belongs to the application boundary. A valid recipe draft may
be persisted as a versioned recipe record only after deterministic validation
passes. Invalid recipe drafts must not become valid recipe versions.

M6B does not decide final nutrition, cuisine, budget, product, package,
substitution, or shopping-list semantics.

### Validator strategy and stable errors

Recipe validation is deterministic code, not prompt text.

M6B validators should cover only rules that can be checked with accepted M6B
technical data:

- schema version and required fields;
- ingredients and quantities;
- portions;
- equipment;
- active and total time;
- ingredient usage in steps;
- no new ingredients only in steps;
- temperature/method consistency when both are present;
- storage and reheating metadata when present;
- source menu/menu-slot referential integrity.

Invalid recipes and invalid replacement outputs must return stable
machine-readable errors. If existing generic contract/policy errors are
insufficient, M6B may add recipe/replacement-specific stable errors to the
domain error catalog.

Raw `KeyError`, `TypeError`, parser exceptions, provider exceptions, or stack
traces must not cross validation boundaries for expected invalid input.

### Fake recipe generator policy

The Gate M6B recipe generator is deterministic and fake.

It must:

- implement a small application/domain port;
- be runnable without Hermes, Telegram, external providers, network, or
  secrets;
- produce reproducible recipe drafts from reviewed menu fixtures;
- be covered by golden tests;
- never activate a menu, persist a recipe, or write confirmed state directly;
- never rely on production model/provider behavior.

The fake recipe generator is a safety and contract harness, not a
product-quality recipe author.

### Recipe persistence policy

Recipe persistence is owned by the application service.

The application boundary may persist only validated recipe drafts as versioned
records. Persistence must run inside an explicit transaction boundary and must
not be performed by Hermes, Telegram, Domain Core, or model code.

Failure before commit must leave confirmed menu and recipe state unchanged.

### One-slot replacement semantics

Replacement is local.

A replacement request must:

- identify the user;
- identify the source menu draft/version or accepted menu fixture;
- identify exactly one target meal slot;
- provide an explicit replacement candidate or generator input;
- produce a new menu draft/version rather than mutating the source menu in
  place.

The replacement operation must change exactly one meal slot. All unaffected
meal slots must remain unchanged according to the accepted comparison rule for
the contract. The default M6B technical assumption is JSON-value equality for
unaffected slot payloads after canonical ordering of object keys.

Replacement output is untrusted until validation passes. Fake/model output
must not activate the replacement directly.

### Exact diff semantics

Replacement preview/diff must be exact and user-facing.

The diff must include:

- source menu reference;
- target meal slot id;
- before payload for the replaced slot;
- after payload for the replacement slot;
- confirmation-relevant metadata, including version or draft reference;
- explicit statement that unaffected slots are unchanged.

The diff must not include shopping-list, store-catalog, package, price, aisle,
or product-matching impact in M6B.

### Stale confirmation behavior

Parallel replacement must be detected deterministically.

If another replacement or menu version change updates the same menu after a
preview/confirmation was created, stale confirmation must be rejected through
the existing safe-commit/version/hash pattern or an M6B equivalent that uses
expected version and summary hash.

A stale confirmation must not create a new menu version, recipe version, or
confirmed state mutation.

### Dependent data recalculation in M6B

M6B dependent recalculation means only data explicitly accepted for M6B:

- replacement diff fields;
- recipe draft/version links for the changed meal slot when recipe behavior is
  part of the task;
- validation status and machine-readable errors for the affected replacement
  candidate.

M6B does not recalculate shopping lists, store products, prices, packages,
availability, aisle data, nutrition plans, or substitutions.

### Model-backed recipe/replacement experiment policy

No model-backed recipe or replacement generation is accepted by this ADR.

A model-backed experiment may be added only by a later explicit task or
decision that selects:

- provider/model/version;
- prompt/schema versioning;
- credentials handling;
- raw-output logging and sanitization policy;
- eval/golden dataset;
- cost/latency reporting;
- validation, repair, stale-confirmation, and failure bounds.

No production model/API dependency is added for M6B by this ADR.

### Prompt/schema and raw output policy

For the deterministic fake generator, there is no prompt and no model raw
output.

If a later model-backed experiment is approved, prompt/schema versions must be
recorded in the experiment artifact. Raw output may be retained only for
synthetic/reviewed inputs and only after checking that it does not contain
secrets, credentials, private user data, or unreviewed production text.
Otherwise raw output must be omitted or sanitized.

## Consequences

- M6B can proceed without choosing a production model provider.
- Recipe and replacement safety can be tested without Hermes, Telegram,
  external providers, network access, or secrets.
- Replacement remains local and exactly one-slot scoped.
- Shopping-list and store-catalog concerns remain separate later milestones.
- Final product recipe, units, storage, reheating, and replacement UX semantics
  remain explicit decisions rather than hidden assumptions.

## Not Decided Here

- Final recipe ingredient taxonomy.
- Final unit system and unit conversion policy.
- Final portion semantics for households and leftovers.
- Final cookware/equipment taxonomy.
- Final active/total time semantics.
- Final temperature and cooking-method ontology.
- Final storage and reheating product requirements.
- Final recipe quality, nutrition, budget, cuisine, substitution, and product
  matching semantics.
- Final menu activation workflow.
- Final replacement confirmation UX.
- Production model/provider/prompt choice for recipes or replacements.
- Production raw-output retention policy.
- Production Hermes plugin, Hermes tools, Telegram UX, callback mapping, or
  adapter idempotency mapping.
- Shopping list, store catalog, product matching, prices, packages, aisle data,
  shopping checklist, or purchase arithmetic.
- Any change to the ready-made Hermes image, Docker daemon, dashboard,
  gateway, auth flow, model provider, or runtime state layout.
