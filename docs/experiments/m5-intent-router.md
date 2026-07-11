# M5 Intent Router report

Date: 2026-07-11

## Goal

M5 proves that reviewed free text can be routed into schema-valid
`ParsedIntent` or a controlled machine-readable error, then into a
`PolicyDecision`, with measured safety and without giving text the ability to
mutate confirmed application state.

The verified chain is:

```text
user text
-> router candidate
-> ParsedIntent validation
-> workflow policy decision
-> allowed next action / clarification / denial / confirmation policy
```

M5 does not prove Hermes, Telegram, menu generation, recipes, shopping list,
store catalog, substitutions, model-backed routing, or production UX behavior.

## Scope

Included in M5:

- M5 Codex skill and brief to keep work inside the intent-router boundary.
- ADR-0007 with router placement, eval strategy, variants, metrics, safety
  thresholds, and selected M5 baseline.
- M5 intent taxonomy tied to current `WorkflowAction` values and operation
  classes.
- Versioned synthetic eval dataset split into development and holdout.
- Offline eval runner and CLI command.
- Deterministic `rule_based_baseline` router.
- Application routing boundary that validates `ParsedIntent` and applies
  existing workflow policy without execution.
- Safety/regression tests for dangerous misroutes.

Excluded from M5:

- direct commit from router output;
- confirmation creation;
- writes to confirmed application state;
- PostgreSQL schema changes or persistence changes;
- production Hermes plugin, tools, hooks, toolsets, skills, or callbacks;
- Telegram business UX or Telegram idempotency mapping;
- menu generation, recipes, shopping list, store catalog, substitutions;
- production model/API dependency or model-backed routing;
- reading, logging, or displaying `.env`, `auth.json`, tokens, credentials, or
  private production chat logs.

## Router Variants

- `rule_based_baseline` / `m5.rule_based_baseline.v1`: accepted for the next
  milestone boundary. It is deterministic, offline, dependency-free, and
  runnable without Hermes, Telegram, model providers, network, or secrets.
- `fixture_expected` / `m5.eval_skeleton.v1`: test candidate used only to
  verify eval harness behavior against expected fixtures.
- `model_backed_candidate`: skipped and deferred. ADR-0007 requires an explicit
  future decision for provider/model choice, credentials handling,
  prompt/schema versioning, raw-output policy, and eval logging before any
  model-backed experiment.

## Dataset

- Dataset path: `fixtures/evals/intent_router/dataset.v1.json`
- Dataset version: `m5.intent_eval_dataset.v1`
- Taxonomy path: `fixtures/evals/intent_router/taxonomy.v1.json`
- Taxonomy version: `m5.intent_taxonomy.v1`
- Split strategy: explicit `development` / `holdout`
- Case count: 12

Coverage includes read-only, draft-producing, state-changing,
administrative, unsupported, incomplete, ambiguous, conflicting workflow
state, prompt-injection, mixed-intent, typo, conversational variant, and
dangerous state-changing/admin labels.

The dataset is synthetic and reviewed. It is not production chat history.

## Metrics

Final M5 eval command:

```text
scripts/dev.sh m5-eval
```

Result:

```text
router_candidate.name                         rule_based_baseline
router_candidate.version                      m5.rule_based_baseline.v1
case_count                                    12
failures                                      0
schema_valid_rate                            1.0
exact_intent_accuracy                         1.0
operation_class_accuracy                      1.0
parameter_extraction_accuracy                 1.0
ambiguity_recall                              1.0
missing_field_recall                          1.0
expected_policy_outcome_accuracy              1.0
dangerous_false_automatic_execution_rate      0.0
administrative_denial_rate                    1.0
unsupported_intent_handling_rate              1.0
latency_ms_total                              1.289
latency_ms_per_case_avg                       0.107393
cost                                          null
model_backed_experiment.status                skipped
```

Dangerous failures: none.

## Selected Decision

Gate M5 accepts `rule_based_baseline` for the next milestone boundary.

The selected M5 threshold/fallback policy is conservative:

- confidence is diagnostic only;
- confidence never bypasses workflow policy;
- read-only output may route to the suggested next action only when workflow
  policy allows it;
- state-changing output routes to confirmation policy, never direct commit;
- ambiguous or incomplete output routes to clarification;
- administrative output is denied in the user workflow;
- unsupported or unknown output returns controlled `unsupported`;
- model-backed routing remains deferred.

ADR-0007 records this decision. OQ-005 records production adapter decisions
that remain open.

## Implemented

- `.agents/skills/m5-intent-router/SKILL.md`
- `docs/briefs/m5-agent-brief.md`
- `docs/Stage 5.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `fixtures/evals/intent_router/taxonomy.v1.json`
- `fixtures/evals/intent_router/dataset.v1.json`
- `src/menu_planner/application/intent_eval.py`
- `src/menu_planner/application/intent_router.py`
- `src/menu_planner/application/intent_routing.py`
- `src/menu_planner/bootstrap/intent_eval_cli.py`
- `tests/unit/domain/test_m5_intent_taxonomy.py`
- `tests/unit/domain/test_m5_intent_eval_dataset.py`
- `tests/unit/test_intent_eval.py`
- `tests/unit/test_intent_routing.py`
- `scripts/dev.sh m5-eval`

## Intentionally Not Implemented

- No production Hermes plugin or Hermes tool schema.
- No Telegram business UX, callback flow, or Telegram metadata mapping.
- No direct commit, confirmation creation, or confirmed-state mutation from
  router output.
- No menu generation, recipe generation, shopping list, store catalog, or
  substitution workflow.
- No model-backed router, model provider, prompt, production threshold, or
  model/API dependency.
- No final HTTP API shape for router calls.
- No adapter-level idempotency key mapping.
- No final product profile schema or menu-generation input contract.
- No Hermes image mutation, custom Hermes image, or Docker daemon change.

## Verification Commands

Commands run for the final M5 checks:

```text
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m5-eval
git diff --check
```

Results:

```text
scripts/dev.sh test      -> 148 passed
scripts/dev.sh lint      -> All checks passed
scripts/dev.sh typecheck -> Success: no issues found in 62 source files
scripts/dev.sh smoke     -> smoke ok
scripts/dev.sh m5-eval   -> failures: 0, dangerous false automatic execution: 0.0
git diff --check         -> ok
```

The Docker-based commands require Docker socket access in this sandbox and
were run with explicit approval. No secret files were opened or displayed.

## Gate M5 Result

Result: passed for the measured deterministic Intent Router baseline.

M5 proves the current application-layer router/eval boundary for the M5
taxonomy and synthetic eval set. It does not prove production natural-language
coverage, model-backed routing, Hermes/Telegram adapter behavior, or M6
generation workflows.

Do not proceed to M6 menu draft generation, Hermes plugin work, Telegram UX, or
production model-backed routing without a separate user task.

## Gate M5 Checklist

[x] M5 Codex skill exists and was used for implementation tasks.
[x] ADR-0007 or equivalent decision note fixes router/eval strategy.
[x] Intent taxonomy is tied to current workflow actions and operation classes.
[x] Unknown/future intents do not become allowed by default.
[x] Eval dataset is versioned and split into development/holdout.
[x] Dataset covers read-only, draft-producing, state-changing, administrative,
    unsupported, incomplete, ambiguous, conflicting, prompt-injection, and
    mixed-intent cases.
[x] Router returns schema-valid ParsedIntent or controlled machine-readable
    error.
[x] PolicyDecision is produced through existing workflow/policy code.
[x] Administrative user-channel requests are denied.
[x] Ambiguous dangerous input routes to clarification.
[x] State-changing input routes to preview/confirmation policy, not commit.
[x] Dangerous state-changing/admin false automatic execution rate is zero.
[x] Confidence thresholds are eval-based or explicitly deferred.
[x] Eval runner records router/model/schema versions, parsed output, policy
    decision, errors, latency and metrics without secrets.
[x] Baseline router runs without Hermes, Telegram, external provider, or
    secrets.
[x] Model-backed candidate is measured or explicitly skipped with reason.
[x] No menu generation, recipes, shopping list, store catalog, production
    Hermes plugin, Telegram UX, or direct commit added.
[x] No Hermes image mutation or custom Hermes image added.
[x] scripts/dev.sh test passes.
[x] scripts/dev.sh lint passes.
[x] scripts/dev.sh typecheck passes.
[x] scripts/dev.sh smoke passes.
[x] M5 eval command passes.
[x] git diff --check passes.
[x] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[x] M5 report is filled.

## Reflection

The current M5 taxonomy is enough for the next milestone boundary only if M6
continues to treat menu, recipe, shopping, store, and substitution requests as
unsupported until their own contracts and workflows are introduced.

The intents to keep for the immediate next boundary are `show_status`,
`submit_profile_draft`, `confirm_profile_draft`, `cancel_workflow`,
`install_skill` for administrative denial coverage, and `unsupported`.
Future menu-related intent names should remain deferred rather than partially
implemented in M5 code.

Rules are more reliable and cheaper than model-backed routing for the current
small taxonomy, administrative denial, unsupported future intents, and
confirmation-policy routing. A model may become useful later for broader
language coverage and parameter extraction, but it should be measured against
the baseline and must not become an executor.

The eval dataset covers the dangerous state-changing/admin cases required for
M5, including prompt injection, workflow conflict, mixed intent, administrative
requests, and malformed router output. It is still small and synthetic, so it
should grow before production Telegram/Hermes exposure.

The only threshold proven by measurement is the hard safety gate:

```text
dangerous state-changing/admin false automatic execution rate = 0
```

No production confidence thresholds are selected. Confidence remains
diagnostic and subordinate to workflow policy.

Ambiguous persistent preference/restriction requests are good candidates for
future guided buttons or forms. M5 only proves they route to clarification.

The application-layer router placement can later be called by a Hermes or HTTP
adapter without moving router logic into Domain Core. Domain Core remains
independent from Hermes, Telegram, HTTP clients, ORM, and model SDKs.

The M4 profile fields remain technical: `user_facts`, `strict_restrictions`,
and `soft_preferences` are enough for deterministic profile validation, but
not final menu-generation product semantics. OQ-004 remains open for the final
profile/menu input shape.

Data that should remain deterministic-only includes workflow state, policy
decisions, confirmation identity, idempotency mapping, commit permission,
secrets, credentials, and confirmed-state writes. Future model inputs should
use sanitized, reviewed context and should never carry commit authority.

## Decisions Before M6

- Define the M6 menu draft contract and validation rules.
- Decide which profile fields are safe and useful as menu-generation input.
- Keep router output connected only to draft/preview/confirmation workflows,
  not direct commit.
- Decide whether M6 needs additional eval cases for menu-generation requests
  before changing those intents from `unsupported`.
- Decide model/provider/prompt policy for generation separately from M5
  routing.
- Keep production Hermes/Telegram adapter mapping and idempotency mapping open
  until a dedicated adapter milestone.

## Remaining Assumptions

- M5 eval cases are synthetic and reviewed; they are sufficient for Gate M5 but
  not sufficient for production natural-language coverage.
- The accepted baseline is intentionally conservative and may reject or clarify
  valid real user phrasing until future datasets expand coverage.
- Production thresholds, guided clarification UX, model-backed routing, and
  adapter mapping remain open in `docs/decisions/open-questions.md`.
