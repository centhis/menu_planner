# M6A menu draft generation report

Date: 2026-07-11

## Goal

M6A proves that confirmed profile data plus an explicit planning request can
produce a validated technical `MenuDraft`, optionally pass a bounded repair
loop, and create a safe `OperationPreview` without activating a menu or writing
confirmed menu state.

The verified chain is:

```text
confirmed profile data + explicit planning request
-> PlanningContext
-> deterministic fake MenuDraftGenerator
-> MenuDraft contract validation
-> menu semantic validation
-> bounded repair loop
-> safe OperationPreview for validated draft only
```

M6A does not prove recipes, substitutions, shopping lists, store catalog,
Hermes plugin behavior, Telegram UX, real model generation, or menu activation.

## Scope

Included in M6A:

- M6A Codex skill and brief to keep work inside the menu-draft boundary.
- ADR-0008 with one-day-first generation strategy, validation policy, repair
  loop, safe preview boundary, and model experiment boundary.
- Minimal `PlanningContext`, `MealSlot`, and `MenuDraft` contracts with
  fixtures.
- PlanningContext builder from confirmed `ProfileVersion` data and explicit
  planning request parameters.
- Deterministic fake menu draft generator and one-day golden fixtures.
- Deterministic menu validators with machine-readable errors.
- Bounded repair loop with structured attempt metadata.
- Safe preview for validated `MenuDraft` using the existing M3 preview hash
  pattern.
- M6A eval/golden command with model-backed and week-draft status recorded.

Excluded from M6A:

- direct menu activation or menu safe-commit workflow;
- recipes, substitutions, shopping list, store catalog, ingredient quantities,
  nutrition, budget, cuisine taxonomy, or product matching;
- production Hermes plugin, tools, hooks, toolsets, skills, or Telegram UX;
- production model provider, model SDK, prompt, credentials, or raw model
  output logging;
- week/month menu generation, because ADR-0008 accepts only the one-day Gate
  M6A period shape;
- final product profile schema or final meal-slot taxonomy.

## Decisions

Contract decisions:

- `PlanningContext` includes `planning_request_id`, one-day `period_start` /
  `period_end`, reviewed `meal_slots`, and JSON-compatible `constraints`.
- `MealSlot` includes explicit `slot_id`, date, meal type, and requirements.
- `MenuDraft` includes `planning_context_id`, one-day period metadata,
  `meal_slots`, and `generated_items`.
- Contract validation keeps one-day period constraints deterministic and
  rejects malformed or incomplete contract payloads.

Generator decisions:

- Gate M6A uses `fake_menu_draft_generator` /
  `m6a.fake_generator.v1`.
- The fake generator is deterministic, side-effect free, and runnable without
  Hermes, Telegram, network, external providers, or secrets.
- Generator output remains untrusted until validation succeeds.

Validator decisions:

- Menu validation is deterministic code, not prompt text.
- Validators cover period completeness, meal slots, strict restrictions,
  equipment, active time, portions, repetition, and referential integrity.
- Invalid drafts return stable machine-readable `DomainError` values suitable
  for repair-loop input.
- Invalid drafts and failed repair loops cannot create a safe preview.

Repair decisions:

- The repair loop has an explicit default max attempt count of 2, matching
  ADR-0008.
- Each attempt receives structured validation errors and produces another
  untrusted candidate that must be validated again.
- Repair failure is controlled and leaves confirmed state unchanged.

Preview decisions:

- Preview is allowed only for a validated menu draft.
- Preview uses `OperationPreviewInput` and the canonical M3 summary-hash
  pattern.
- Preview includes a user-facing summary in `changes`, but does not create a
  confirmation, commit, active menu, or confirmed menu version.

## Model-Backed Experiment Status

Status: skipped.

Reason: ADR-0008 accepts deterministic fake generation for Gate M6A and defers
model-backed generation until provider/model/version, prompt/schema versioning,
credentials handling, raw-output retention/sanitization, eval dataset, and
failure-handling policy are explicitly approved.

The M6A eval report records:

```text
model_backed_experiment.status          skipped
model_backed_experiment.provider        null
model_backed_experiment.model           null
prompt_schema_version                   null
credentials_read                        false
raw_output_stored                       false
external_provider_required              false
```

No model credentials were read, printed, or required.

## Week Draft Status

Status: skipped.

Reason: ADR-0008 accepts the Gate M6A one-day period shape only. Week
generation remains deferred until period semantics, week fixtures, and week
validation rules are explicitly accepted.

The M6A eval report records:

```text
week_draft_expansion.status             skipped
week_draft_expansion.one_day_gate_green true
week_draft_expansion.adr_accepts_period_shape false
week_draft_expansion.fixtures_added     false
```

## Golden And Eval Metrics

Final M6A eval command:

```text
scripts/dev.sh m6a-eval
```

Result:

```text
schema_version                          m6a.menu_draft_eval_report.v1
generator_candidate.name                fake_menu_draft_generator
generator_candidate.version             m6a.fake_generator.v1
failures                                0
generation_ok                           true
validation_ok                           true
repair_ok                               true
preview_ok                              true
max_repair_attempts                     2
confirmed_state_changed                 false
side_effects_executed                   false
external_provider_required              false
preview.created                         true
preview.requires_confirmation           true
model_backed_experiment.status          skipped
week_draft_expansion.status             skipped
```

## Implemented

- `.agents/skills/m6a-menu-draft-generation/SKILL.md`
- `docs/briefs/m6-agent-brief.md`
- `docs/Stage 6.md`
- `docs/decisions/ADR-0008-menu-draft-generation.md`
- `fixtures/domain/contracts/planning_context/valid/minimal.json`
- `fixtures/domain/contracts/planning_context/invalid/meal_slots_empty.json`
- `fixtures/domain/contracts/planning_context/invalid/week_period_not_m6a.json`
- `fixtures/domain/contracts/meal_slot/valid/minimal.json`
- `fixtures/domain/contracts/meal_slot/invalid/missing_slot_id.json`
- `fixtures/domain/contracts/menu_draft/valid/minimal.json`
- `fixtures/domain/contracts/menu_draft/invalid/missing_planning_context_id.json`
- `fixtures/domain/contracts/menu_draft/invalid/generated_item_missing_title.json`
- `fixtures/golden/m6a_menu_draft_generation/one_day/planning_context.json`
- `fixtures/golden/m6a_menu_draft_generation/one_day/menu_draft.json`
- `fixtures/golden/m6a_menu_draft_generation/invalid/missing_generated_items.json`
- `src/menu_planner/application/planning_context.py`
- `src/menu_planner/application/menu_generation.py`
- `src/menu_planner/application/menu_validation.py`
- `src/menu_planner/application/menu_repair.py`
- `src/menu_planner/application/menu_preview.py`
- `src/menu_planner/application/menu_eval.py`
- `src/menu_planner/bootstrap/menu_eval_cli.py`
- `src/menu_planner/domain/contracts/models.py`
- `src/menu_planner/domain/contracts/validation.py`
- `src/menu_planner/domain/errors.py`
- `tests/unit/test_planning_context.py`
- `tests/unit/test_menu_generation.py`
- `tests/unit/test_menu_validation.py`
- `tests/unit/test_menu_repair.py`
- `tests/unit/test_menu_preview.py`
- `tests/unit/test_menu_eval.py`
- `tests/contract/test_domain_contract_fixtures.py`
- `scripts/dev.sh m6a-eval`

## Intentionally Not Implemented

- No recipe generation.
- No substitutions.
- No shopping list.
- No store catalog or product matching.
- No ingredient quantities, nutrition, budget, cuisine taxonomy, or product
  meal semantics.
- No production Hermes plugin, tool, hook, toolset, skill, or Telegram UX.
- No direct menu activation.
- No menu confirmation or safe-commit workflow.
- No production model provider, model SDK, prompt, or credentials.
- No raw model output logging.
- No week or month draft generation.
- No Hermes image mutation, custom Hermes image, or Docker daemon change.

Do not proceed to recipes, substitutions, shopping list, store catalog,
production Hermes/Telegram UX, model-backed generation, or menu activation
without a separate user task and explicit decisions.

## Verification Commands

Commands run for the final M6A checks:

```text
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m6a-eval
git diff --check
```

Results:

```text
scripts/dev.sh test      -> 175 passed
scripts/dev.sh lint      -> All checks passed
scripts/dev.sh typecheck -> Success: no issues found in 75 source files
scripts/dev.sh smoke     -> smoke ok
scripts/dev.sh m6a-eval  -> failures: 0
git diff --check         -> ok
```

The Docker-based commands require Docker socket access in this sandbox and
were run with explicit approval. Secret files such as `.env`, `auth.json`,
tokens, and credentials were not opened or displayed.

## Gate M6A Result

Result: passed for the deterministic one-day fake-generator slice.

M6A proves the current technical generation/validation/repair/preview boundary
for one-day menu drafts. It does not prove product-quality meal planning,
week/month planning, real model generation, recipes, substitutions, shopping
lists, Hermes/Telegram adapter UX, or menu activation.

Do not proceed to recipes, substitutions, shopping list, store catalog,
production Hermes/Telegram UX, model-backed generation, or menu activation
without a separate user task.

## Gate M6A Checklist

[x] M6A Codex skill exists and was used for implementation tasks.
[x] M6A brief exists and was used for routine tasks.
[x] ADR-0008 or equivalent decision note fixes menu draft generation strategy.
[x] PlanningContext uses only confirmed profile data and explicit request
    parameters.
[x] Unknown final product profile/menu fields are not invented.
[x] MenuDraft and MealSlot contracts have schema_version and fixtures.
[x] Invalid MenuDraft returns machine-readable validation errors.
[x] Fake MenuDraftGenerator is deterministic and side-effect free.
[x] One-day golden happy path passes before week expansion.
[x] Week draft, if included, is covered by golden fixtures. Week draft is not
    included in Gate M6A; skipped reason is recorded.
[x] Bounded repair loop has explicit max attempts and controlled failure.
[x] Malformed/invalid generator output cannot create preview.
[x] Invalid draft cannot become preview for commit.
[x] Model/fake output cannot activate menu or write confirmed state.
[x] Failure leaves active/confirmed menu state unchanged.
[x] Optional model-backed experiment is measured or explicitly skipped.
[x] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[x] No recipes, substitutions, shopping list, store catalog, production Hermes
    plugin, Telegram UX, or direct menu activation added.
[x] No Hermes image mutation or custom Hermes image added.
[x] scripts/dev.sh test passes.
[x] scripts/dev.sh lint passes.
[x] scripts/dev.sh typecheck passes.
[x] scripts/dev.sh smoke passes.
[x] M6A golden/eval command passes.
[x] git diff --check passes.
[x] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[x] M6A report is filled.

## Reflection

PlanningContext separation:

- `PlanningContext` is built through the application boundary from confirmed
  `ProfileVersion` data and explicit request parameters.
- It does not use raw conversation text, Hermes memory, Telegram metadata,
  model output, or secrets as sources of truth.

Profile fields used:

- M6A uses only a small technical subset from profile fields: strict
  restrictions, available equipment, active-time limit, and optional people
  count when present.
- These fields are not accepted as final product profile semantics.

Deterministic validator boundary:

- Period completeness, slot coverage, equipment availability, active-time
  limits, portions, repetition, and referential integrity are deterministic.
- Taste, nutrition quality, cuisine fit, budget quality, ingredient realism,
  recipe feasibility, and substitution quality require later product or
  model/human decisions.

Repair loop value:

- The repair loop proves bounded retry behavior and structured error handoff.
- It does not prove that repair is better than full regeneration; that remains
  a future model/product experiment.

MenuDraft complexity:

- The current `MenuDraft` shape is still small enough for fake generation and
  future local model experiments.
- Adding recipes, ingredients, substitutions, shopping items, or week/month
  planning would materially increase complexity and needs a separate decision.

User-facing errors:

- Some errors can later become adapter/user-facing after copy review:
  missing slots, strict restriction violation, unavailable equipment, active
  time exceeded, invalid portions, repeated item, and unknown slot reference.
- M6A keeps them as machine-readable application errors.

M5 taxonomy:

- Menu-generation intents can remain unsupported/deferred until M6B or a later
  task decides how to expose draft-producing menu generation safely.
- M5 taxonomy should not be expanded to execute menu generation automatically
  without a new router/eval decision.

Model/provider/prompt policy:

- A real model-backed generator needs provider/model/version, prompt/schema
  versioning, credentials handling, raw-output retention/sanitization, eval
  dataset, cost/latency reporting, and repair/failure policy.

Decisions before recipes, substitutions, and shopping:

- Final meal-slot taxonomy.
- Final one-day/week/month period semantics.
- Final product profile fields for generation.
- Menu activation confirmation lifecycle and idempotency mapping.
- Recipe, ingredient, substitution, product matching, and shopping-list
  contracts.
- Hermes/Telegram adapter UX for preview, repair, confirmation, and failure
  states.

## Remaining Assumptions And Open Questions

Relevant open questions are recorded in
`docs/decisions/open-questions.md`, especially OQ-006.

Remaining assumptions:

- M6A remains one-day-first and fake-generator-only.
- `people_count`, active-time, equipment, and strict restrictions are
  technical inputs for validation tests, not final product semantics.
- Week draft generation remains skipped until ADR/OQ decisions accept period
  shape, fixtures, and validation rules.
- Model-backed generation remains skipped until a separate explicit decision.
- Menu activation remains out of scope until a later safe-commit workflow is
  designed.
