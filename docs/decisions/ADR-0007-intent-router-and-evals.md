# ADR-0007: Intent Router and eval strategy

Date: 2026-07-11

Status: Accepted

## Context

Stage 5 / M5 must prove that free text can be routed into schema-valid
`ParsedIntent`, controlled errors, and `PolicyDecision` with measurable safety
before any production Hermes plugin, Telegram UX, menu generation, recipes,
shopping list, store catalog, or direct commit path is added.

M2 already provides the Domain Core contracts, operation classes, workflow
state machine, policy decisions, and stable error catalog. M3 provides safe
commit primitives. M4 proves a deterministic profile vertical slice without
Hermes, Telegram, Intent Router, or LLM.

M5 must not give free text the ability to directly change confirmed
application state. The router is a classification and policy input boundary,
not an executor.

## Decision

Use an application-layer Intent Router boundary for M5.

The M5 router receives text and routing context and returns one of:

- a schema-valid `ParsedIntent`;
- a controlled machine-readable error;
- a `PolicyDecision` derived by applying existing workflow/policy code to the
  parsed intent.

The router must not call profile commit commands, create confirmations, write
to PostgreSQL, call Hermes tools, call Telegram callbacks, generate menus, or
perform any side effect. State-changing output may only route toward
preview/confirmation policy in a later application workflow.

### Router placement

For M5, the router lives in the Application layer as a deterministic use-case
boundary:

```text
text + workflow context
-> router candidate
-> ParsedIntent validation
-> workflow policy decision
-> intent/policy/error result
```

This placement is a technical M5 decision for testability and safety. Future
Hermes or Telegram adapters may call this boundary through an HTTP API, but M5
does not define the production HTTP shape, Hermes tool schema, Telegram
callback mapping, or adapter-level idempotency key source.

Domain Core remains independent from Hermes, Telegram, ORM, HTTP clients, and
model SDKs. Router implementation details must not enter Domain Core.

### Router variants

M5 compares these variants:

- `rule_based_baseline`: target for Gate M5 unless later evidence shows it is
  insufficient. It is deterministic, offline, dependency-free, and runnable
  without Hermes, Telegram, model providers, network, or secrets.
- `fake_model_candidate`: optional test double for malformed output and
  validation behavior. It is not a production router.
- `model_backed_candidate`: deferred experiment. It may be added only by a
  later explicit task if provider/model choice, credentials handling, prompt
  versioning, raw-output policy, and eval logging are approved.

No new production model/API dependency is selected by this ADR.

### Intent names in M5

The M5 taxonomy starts from existing workflow actions and operation classes.

Included intents:

- `show_status`;
- `submit_profile_draft`;
- `confirm_profile_draft`;
- `cancel_workflow`;
- `install_skill` or an equivalent administrative-denial fixture;
- `unsupported`.

Future menu, recipe, shopping list, store, substitution, and generated-draft
intents are represented only as `unsupported` or deferred cases until a later
milestone implements their production workflows.

Unknown intent names must not become allowed by default.

### ParsedIntent validation

Every router candidate output is treated as untrusted JSON-compatible data.
The eval runner and router boundary must validate it through the existing
`ParsedIntent` contract validator before applying workflow policy.

Invalid router output becomes a controlled machine-readable error. Expected
invalid input or malformed model output must not leak raw parser exceptions,
`KeyError`, `TypeError`, provider exceptions, stack traces, secrets, or
credentials.

### Workflow and policy application

Policy is applied after parsing through the existing workflow/policy code.

The router does not decide final permission by itself. It may propose an
intent, operation class, missing fields, ambiguities, scope, and next action,
but workflow policy remains the authority for whether the action is allowed,
denied, clarification-required, confirmation-required, unsupported, or blocked
by current state.

Administrative requests are denied in the user workflow. State-changing
requests must never be interpreted as direct commit permission.

### Eval dataset strategy

Use versioned fixtures under:

```text
fixtures/evals/intent_router/
```

The dataset must be reproducible and split into:

- `development`: visible cases used while implementing router behavior;
- `holdout`: cases used for Gate M5 regression and threshold decisions.

Each case records:

- dataset schema/version metadata;
- split;
- user text;
- workflow state and user context needed for policy;
- expected `ParsedIntent`;
- expected operation class;
- expected parameters, missing fields, and ambiguities;
- expected `PolicyDecision` outcome;
- safety labels such as state-changing, administrative, prompt-injection,
  ambiguous, incomplete, unsupported, mixed-intent, and dangerous.

The dataset must not contain real private user data, `.env` values,
`auth.json`, tokens, credentials, or production chat logs.

### Gate metrics

M5 Gate metrics are:

- schema-valid rate;
- exact intent accuracy;
- operation-class accuracy;
- parameter extraction accuracy;
- ambiguity recall;
- missing-field recall;
- expected policy outcome accuracy;
- dangerous false automatic execution rate;
- administrative denial rate;
- unsupported intent handling rate;
- latency, when measured locally;
- cost, only if it is available without exposing credentials or secrets.

The hard safety threshold for M5 is:

```text
dangerous state-changing/admin false automatic execution rate = 0
```

Dangerous state-changing or administrative cases must not route to automatic
execution. They must route to deny, clarify, unsupported, or
preview/confirmation policy, depending on the case and workflow state.

### Confidence policy

Self-reported router or model confidence is not trusted as sufficient evidence
for execution safety.

For the rule-based baseline, M5 may record deterministic confidence-like values
for diagnostics, but those values do not grant execution permission. Gate M5
acceptance depends on measured eval behavior and workflow policy, not on raw
confidence.

Production confidence thresholds are deferred until eval data can justify
them. If no threshold is selected by Gate M5, the report must state that
threshold policy remains open and that conservative fallback behavior is
required.

### Eval logging and artifacts

Eval reports may record:

- dataset version and split;
- router candidate name and version;
- prompt/schema version, if a prompt exists;
- model/provider/version, if a model-backed candidate is explicitly selected;
- parsed output after validation/sanitization;
- controlled errors;
- policy decision;
- latency;
- metrics.

Eval reports must not record secrets, raw `.env` values, `auth.json`, tokens,
provider credentials, private Telegram IDs, or unreviewed private user text.

For model-backed experiments, raw model output may be stored only if the input
dataset is synthetic/reviewed and the output is checked for secrets/private
data. Otherwise, raw output must be omitted or sanitized.

### M5 eval decision

After M5 steps 1-9, the `rule_based_baseline` candidate is selected as the
router variant to carry into the next milestone boundary.

Decision evidence from the M5 eval command on 2026-07-11:

- dataset: `m5.intent_eval_dataset.v1`;
- taxonomy: `m5.intent_taxonomy.v1`;
- candidate: `rule_based_baseline` / `m5.rule_based_baseline.v1`;
- case count: 12;
- failures: 0;
- schema-valid rate: 1.0;
- exact intent accuracy: 1.0;
- operation-class accuracy: 1.0;
- parameter extraction accuracy: 1.0;
- ambiguity recall: 1.0;
- missing-field recall: 1.0;
- expected policy outcome accuracy: 1.0;
- administrative denial rate: 1.0;
- unsupported intent handling rate: 1.0;
- dangerous false automatic execution rate: 0.0;
- model-backed experiment: skipped.

The selected M5 threshold policy is conservative:

- confidence values remain diagnostic only;
- no confidence threshold may bypass workflow policy;
- read-only output may route to the allowed next action only when workflow
  policy allows it;
- state-changing output routes to confirmation policy, never direct commit;
- ambiguous or incomplete output routes to clarification;
- administrative output routes to denial in the user workflow;
- unsupported or unknown output routes to controlled `unsupported`.

No production model-backed router is accepted in M5. The model-backed
candidate remains deferred until provider/model choice, credentials handling,
prompt/schema versioning, raw-output retention, and eval logging are explicitly
approved.

Known weaknesses and dataset gaps:

- the M5 dataset is small and synthetic;
- the baseline intentionally covers only M5 intents and profile-related
  fixtures;
- future menu, recipe, shopping, store, and substitution requests remain
  unsupported until their milestones introduce production workflows;
- production confidence thresholds, Hermes/Telegram routing context, and
  adapter-level idempotency mapping remain open decisions.

## Consequences

- M5 can proceed with a deterministic baseline and eval harness without
  choosing a model provider.
- Router behavior becomes measurable before any Hermes or Telegram adapter is
  connected.
- The application layer owns router orchestration and policy application for
  M5, while Domain Core remains adapter-independent.
- Future model-backed routing can be compared against the baseline using the
  same eval command and metrics.
- State-changing and administrative safety are explicit Gate metrics rather
  than implicit prompt instructions.

## Not Decided Here

- Production Hermes plugin, Hermes tools, hooks, toolsets, or skills.
- Telegram business UX, callback mapping, or Telegram confirmation copy.
- Menu generation, recipe generation, shopping list, store catalog, or
  substitutions.
- Production model/provider choice for routing.
- Production confidence thresholds beyond the M5 zero-dangerous-auto-execution
  gate.
- Final HTTP API shape for router calls.
- Adapter-level idempotency key source.
- Final product profile schema and menu-generation input contract.
- Any change to the ready-made Hermes image, Docker daemon, dashboard,
  gateway, auth flow, model provider, or runtime state layout.
