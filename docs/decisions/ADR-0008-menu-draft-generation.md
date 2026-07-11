# ADR-0008: Menu draft generation strategy

Date: 2026-07-11

Status: Accepted

## Context

Stage 6 / M6A must prove validated menu draft generation without menu
activation, recipes, substitutions, shopping list, store catalog, production
Hermes plugin, Telegram UX, direct commit, or production model dependency.

M4 proved a technical profile vertical slice. M5 proved a conservative
application-layer Intent Router and intentionally kept menu, recipe, shopping,
store, and substitution intents unsupported or deferred until their production
contracts and workflows exist.

M6A starts after Gate M5 and must not turn model or fake generator output into
confirmed state. Generator output is untrusted until deterministic validation
accepts it. Invalid drafts must stop before preview. Validated drafts may get a
safe preview, but activation remains out of M6A and must require a later
confirmation/commit path.

## Decision

Use a minimal one-day menu draft generation slice for M6A.

The M6A flow is:

```text
confirmed profile data + explicit planning request
-> PlanningContext
-> deterministic fake MenuDraftGenerator
-> MenuDraft
-> deterministic validation
-> optional bounded repair loop
-> safe OperationPreview for validated draft only
```

M6A does not activate a menu, create recipes, build a shopping list, match
products, call Hermes tools, use Telegram callbacks, or write confirmed menu
state.

### Scope: one-day first

M6A implements one-day menu draft generation first.

The initial technical scope is:

- one `PlanningContext`;
- one date or day identifier supplied by explicit planning request;
- a small set of explicit meal slots supplied by request or fixture;
- one `MenuDraft` containing `MealSlot` entries for that day;
- deterministic validation and golden fixtures for the one-day path.

Week generation is deferred until the one-day checks are green and a later
task explicitly expands the fixture set and validation rules. A week draft must
not be inferred from one-day behavior by default.

### PlanningContext source policy

`PlanningContext` may be built only from:

- confirmed profile data read through the application profile boundary;
- explicit planning request parameters;
- deterministic technical defaults accepted by this ADR;
- workflow/user identity needed for policy and ownership checks.

`PlanningContext` must not be built from:

- Hermes memory as a source of truth;
- raw Telegram text;
- unverified model output;
- final product profile semantics not accepted by a decision;
- `.env`, `auth.json`, tokens, credentials, or private runtime state.

Because OQ-004 remains open, M6A may use only a small technical mapping from
the M4 profile shape. That mapping is not the final menu-generation product
schema.

### MenuDraft and MealSlot shape

The M6A contracts use the existing Domain Core contract pattern: Python
standard-library dataclasses/enums with explicit `schema_version`, explicit
validators, JSON fixtures, and stable machine-readable errors.

The initial `MealSlot` shape should stay minimal and verifiable:

- `schema_version`;
- date or day identifier;
- meal type;
- requirements as JSON-compatible data.

The initial `MenuDraft` shape should stay minimal and verifiable:

- `schema_version`;
- `draft_id`;
- `status`;
- `user_id`;
- `planning_context_id`;
- one-day period metadata;
- meal slots and generated dish candidates as structured JSON-compatible data;
- validation status or validation-related metadata only if needed by tests.

Product semantics such as calories, macros, cuisine taxonomy, budget, store
availability, recipe IDs, ingredient quantities, substitutions, and shopping
list data are out of M6A unless a later explicit task accepts them.

### Validator strategy and errors

Menu validation is deterministic code, not prompt text.

M6A validators should cover only rules that can be checked with accepted M6A
data:

- schema version and required fields;
- one-day period completeness;
- required meal slots from the explicit request/fixture;
- JSON-compatible generated item structure;
- strict restriction and equipment checks when the data is present in the
  accepted technical profile/context shape;
- active time and portions only when explicitly supplied by context;
- duplicate/repetition checks only within the one-day scope;
- referential integrity between `PlanningContext`, `MenuDraft`, and `MealSlot`
  identifiers.

Invalid drafts must return stable machine-readable error codes. If existing
generic contract/policy errors are insufficient, M6A may add menu-specific
stable errors to the domain error catalog. Raw `KeyError`, `TypeError`, parser
exceptions, provider exceptions, or stack traces must not cross the validation
boundary for expected invalid input.

### Fake generator policy

The Gate M6A generator is a deterministic fake generator.

It must:

- implement a small application/domain port;
- be runnable without Hermes, Telegram, external provider, network, or
  secrets;
- produce reproducible one-day menu drafts from reviewed fixtures;
- be covered by golden tests;
- never activate a menu or write confirmed state;
- never rely on production model/provider behavior.

The fake generator is a safety and contract harness, not a product-quality meal
planner.

### Model-backed generation policy

No model-backed menu generation is accepted by this ADR.

A model-backed experiment may be added only by a later explicit task or
decision that selects:

- provider/model/version;
- prompt/schema versioning;
- credentials handling;
- raw-output logging and sanitization policy;
- eval/golden dataset;
- failure handling and repair bounds.

No production model/API dependency is added for M6A by this ADR.

### Prompt/schema and raw output policy

For the deterministic fake generator, there is no prompt and no model raw
output.

If a later model-backed experiment is approved, prompt/schema versions must be
recorded in the experiment artifact. Raw output may be retained only for
synthetic/reviewed inputs and only after checking that it does not contain
secrets, credentials, private user data, or unreviewed production text.
Otherwise raw output must be omitted or sanitized.

### Bounded repair loop

M6A may add a bounded repair loop after deterministic validation fails.

The M6A technical assumption is:

```text
max repair attempts = 2
```

Each attempt must consume structured validation errors and produce another
untrusted `MenuDraft` candidate that must be validated again. The loop stops
when:

- validation passes;
- the max attempt count is reached;
- the repair output is malformed;
- the repair repeats the same validation failure without progress;
- the failure is classified as non-repairable.

Repair attempts may be logged as structured test/eval artifacts without
secrets or private data. A failed repair loop must not produce preview,
confirmation, commit, or confirmed-state writes.

### Preview policy

M6A may create an `OperationPreview` only for a validated menu draft.

Preview must:

- use the existing safe preview/hash pattern;
- include committed-relevant technical payload;
- not activate the menu;
- not create or consume a confirmation unless a later stage explicitly adds a
  menu safe-commit workflow;
- not write confirmed menu state.

Invalid drafts and failed repair loops must not become commit previews.

## Consequences

- M6A can proceed without choosing a production model provider.
- One-day generation becomes the safety harness before week generation.
- Final product menu semantics remain explicit decisions rather than hidden
  assumptions.
- M6A validation and repair behavior can be tested without Hermes, Telegram,
  external providers, network, or secrets.
- Menu activation remains protected by later confirmation/commit work.

## Not Decided Here

- Final product profile schema and final menu-generation input schema.
- Whether default meal slots are breakfast/lunch/dinner or user-configurable.
- Supported planning period UX beyond the initial one-day slice.
- Nutrition, budget, cuisine, store, product, substitutions, recipe, and
  shopping-list semantics.
- Production model/provider/prompt choice for generation.
- Production raw-output retention policy.
- Production Hermes plugin, Hermes tools, Telegram UX, callback mapping, or
  adapter idempotency mapping.
- Menu activation, menu confirmation lifecycle, or menu safe commit.
- Any change to the ready-made Hermes image, Docker daemon, dashboard,
  gateway, auth flow, model provider, or runtime state layout.
