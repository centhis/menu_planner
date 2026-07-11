# M6B recipes and replacements report

Date: 2026-07-11

## Goal

M6B proves that recipe drafts and local one-slot meal replacement can be
handled behind the safe M6A menu boundary.

The verified chain is:

```text
accepted or confirmed menu boundary
-> deterministic fake RecipeDraftGenerator
-> RecipeDraft contract and semantic validation
-> versioned recipe persistence through application boundary
-> explicit one-slot replacement request
-> new menu draft/version
-> exact replacement diff
-> stale confirmation protection
```

M6B does not prove shopping lists, store catalog, product matching,
Hermes/Telegram UX, production model generation, final recipe quality, or final
menu activation UX.

## Scope

Included in M6B:

- M6B Codex skill and brief to keep work inside recipes and local replacement.
- ADR-0009 with recipe contract, recipe timing, replacement, stale
  confirmation, model experiment, and shopping/catalog boundary decisions.
- Minimal `RecipeDraft` and `RecipeVersion` contracts with valid and invalid
  fixtures.
- Deterministic fake recipe generator with golden fixtures.
- Deterministic recipe validation with stable machine-readable errors.
- Versioned recipe persistence through application boundary and transaction
  boundary.
- Local replacement of exactly one meal slot as a new menu draft/version.
- Exact user-facing replacement diff using the existing `OperationPreview`
  summary-hash pattern.
- Stale replacement protection using current committed menu version checks.
- M6B eval/golden command with model-backed experiment skipped explicitly.

Excluded from M6B:

- shopping list, store catalog, product matching, prices, packages, aisle data,
  shopping checklist, or purchase arithmetic;
- production Hermes plugin, tools, hooks, toolsets, skills, or Telegram UX;
- production model provider, model SDK, prompt, credentials, or raw model
  output logging;
- direct model/fake output writes to confirmed state;
- final product recipe semantics, unit taxonomy, portion semantics, nutrition,
  budget, cuisine, substitution, or product matching behavior;
- final menu activation workflow.

## Decisions

Contract decisions:

- `RecipeDraft` includes `schema_version`, source menu/menu-slot reference,
  title, portions, ingredients, equipment, active/total time, steps, storage,
  and reheating metadata.
- `RecipeVersion` mirrors the persisted validated recipe payload and is stored
  as a versioned application record.
- Contract validation rejects malformed ingredients, invalid quantities,
  missing steps, inconsistent active/total time, invalid portions, unsupported
  bake temperature shape, and storage/reheating metadata gaps.

Generator decisions:

- Gate M6B uses `fake_recipe_draft_generator` /
  `m6b.fake_recipe_generator.v1`.
- The fake generator is deterministic, side-effect free, and runnable without
  Hermes, Telegram, network, external providers, or secrets.
- Generator output remains untrusted until deterministic validation succeeds.

Validator decisions:

- Recipe validation is deterministic code, not prompt text.
- Validators cover accepted source menu item matching, equipment availability,
  ingredient usage, quantities, portions, active/total time, steps, temperature
  consistency, storage, and reheating.
- Invalid recipes return stable `DomainError` values.
- Invalid recipes cannot be persisted as valid recipe versions.

Recipe persistence decisions:

- Recipe persistence is application-owned and uses the M3 versioned-record
  pattern.
- A valid recipe draft can be saved as a committed recipe version with audit
  metadata that contains no prompt text, secrets, or private runtime data.
- Persistence failure rolls back audit and version writes.
- Recipe generation and recipe persistence do not change the active menu.

Replacement and stale-confirmation decisions:

- Replacement accepts an explicit request with source menu version, target meal
  slot, and candidate menu payload.
- Replacement creates a draft menu version; it does not directly commit or
  activate confirmed state.
- Replacement is local: exactly one generated item for the target meal slot may
  change, and unaffected slots are compared by JSON-value equality.
- Replacement diff includes source menu id/version, draft version, target meal
  slot, exact old item, exact new item, recipe/version impact, and
  `shopping_list_impact: none`.
- Stale replacement is rejected when the current committed menu version no
  longer matches the source version used by the request/preview.

## Model-Backed Experiment Status

Status: skipped.

Reason: ADR-0009 accepts only deterministic fake recipe/replacement behavior
for Gate M6B. Model-backed recipe or replacement generation remains deferred
until provider/model/version, prompt/schema versioning, credentials handling,
raw-output retention/sanitization, eval dataset, and failure bounds are
explicitly approved.

The M6B eval report records:

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

## Golden And Eval Metrics

Final M6B eval command:

```text
scripts/dev.sh m6b-eval
```

Result:

```text
schema_version                          m6b.recipe_replacement_eval_report.v1
generator_candidate.name                fake_recipe_draft_generator
generator_candidate.version             m6b.fake_recipe_generator.v1
failures                                0
generation_ok                           true
validation_ok                           true
replacement_diff_ok                     true
stale_confirmation_rejected             true
confirmed_state_changed                 false
side_effects_executed                   false
external_provider_required              false
preview.created                         true
preview.requires_confirmation           true
model_backed_experiment.status          skipped
```

## Implemented

- `.agents/skills/m6b-recipes-replacements/SKILL.md`
- `docs/briefs/m7-agent-brief.md`
- `docs/decisions/ADR-0009-recipes-and-replacements.md`
- `fixtures/domain/contracts/recipe_draft/valid/minimal.json`
- `fixtures/domain/contracts/recipe_draft/invalid/active_time_exceeds_total.json`
- `fixtures/domain/contracts/recipe_draft/invalid/bake_missing_temperature.json`
- `fixtures/domain/contracts/recipe_draft/invalid/ingredient_quantity_zero.json`
- `fixtures/domain/contracts/recipe_draft/invalid/ingredients_empty.json`
- `fixtures/domain/contracts/recipe_draft/invalid/portions_zero.json`
- `fixtures/domain/contracts/recipe_draft/invalid/step_unknown_ingredient.json`
- `fixtures/domain/contracts/recipe_draft/invalid/storage_missing_instructions.json`
- `fixtures/domain/contracts/recipe_version/valid/minimal.json`
- `fixtures/golden/m6b_recipe_generation/one_day/accepted_menu_item.json`
- `fixtures/golden/m6b_recipe_generation/one_day/recipe_draft.json`
- `fixtures/golden/m6b_recipe_generation/invalid/missing_steps.json`
- `src/menu_planner/application/recipe_generation.py`
- `src/menu_planner/application/recipe_validation.py`
- `src/menu_planner/application/recipe_persistence.py`
- `src/menu_planner/application/menu_replacement.py`
- `src/menu_planner/application/recipe_replacement_eval.py`
- `src/menu_planner/bootstrap/recipe_replacement_eval_cli.py`
- `src/menu_planner/domain/contracts/models.py`
- `src/menu_planner/domain/contracts/validation.py`
- `src/menu_planner/domain/errors.py`
- `tests/unit/test_recipe_generation.py`
- `tests/unit/test_recipe_validation.py`
- `tests/unit/test_recipe_persistence.py`
- `tests/unit/test_menu_replacement.py`
- `tests/unit/test_recipe_replacement_eval.py`
- `tests/contract/test_domain_contract_fixtures.py`
- `scripts/dev.sh m6b-eval`

## Intentionally Not Implemented

- No shopping list.
- No store catalog.
- No product matching.
- No prices, packages, aisle data, shopping checklist, or purchase arithmetic.
- No production Hermes plugin, tool, hook, toolset, skill, or Telegram UX.
- No production model provider, model SDK, prompt, credentials, or raw model
  output logging.
- No direct confirmed-state writes from fake/model output.
- No final product recipe taxonomy, unit conversion, nutrition, cuisine,
  budget, substitution, or product matching semantics.
- No final menu activation workflow.
- No Hermes image mutation, custom Hermes image, or Docker daemon change.

Do not proceed to shopping list, store catalog, product matching, production
Hermes/Telegram UX, production model-backed generation, or final menu
activation without a separate user task and explicit decisions.

## Verification Commands

Commands run for the final M6B checks:

```text
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m6b-eval
git diff --check
```

Results:

```text
scripts/dev.sh test      -> 199 passed
scripts/dev.sh lint      -> All checks passed
scripts/dev.sh typecheck -> Success: no issues found in 86 source files
scripts/dev.sh smoke     -> smoke ok
scripts/dev.sh m6b-eval  -> failures: 0
git diff --check         -> ok
```

The Docker-based commands require Docker socket access in this sandbox and
were run with explicit approval. Secret files such as `.env`, `auth.json`,
tokens, and credentials were not opened or displayed.

## Gate M6B Result

Result: passed for the deterministic fake recipe/replacement slice.

M6B proves the current technical recipe generation, validation, persistence,
one-slot replacement, exact diff, and stale-protection boundary. It does not
prove product-quality recipes, shopping lists, store catalogs, product
matching, production Hermes/Telegram UX, production model generation, or final
menu activation.

Do not proceed to shopping list, store catalog, product matching, production
Hermes/Telegram UX, model-backed generation, or final menu activation without
a separate user task.

## Gate M6B Checklist

[x] M6B Codex skill exists and was used for implementation tasks.
[x] M6B brief exists and was used for routine tasks.
[x] ADR-0009 or equivalent decision note fixes recipe and replacement strategy.
[x] RecipeDraft contract has schema_version and fixtures.
[x] Invalid RecipeDraft returns machine-readable validation errors.
[x] Fake RecipeDraftGenerator is deterministic and side-effect free.
[x] Recipe generation does not change active menu by itself.
[x] Recipes are persisted as versions through application boundary.
[x] Replacement changes exactly one meal slot.
[x] Replacement creates a new menu draft/version.
[x] Unaffected meal slots remain unchanged by tests.
[x] User-facing replacement diff is exact and stable.
[x] Stale confirmation after parallel replacement is rejected.
[x] Recipe/replacement failure leaves confirmed state unchanged.
[x] Optional model-backed experiment is measured or explicitly skipped.
[x] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[x] No shopping list, store catalog, product matching, production Hermes
    plugin, Telegram UX, or direct model writes added.
[x] `scripts/dev.sh test` passed.
[x] `scripts/dev.sh lint` passed.
[x] `scripts/dev.sh typecheck` passed.
[x] `scripts/dev.sh smoke` passed.
[x] M6B golden/eval command passed.
[x] `git diff --check` passed.

## Reflection M6

### What proved deterministic?

- Contract shape, required fields, recipe source matching, ingredient/step
  consistency, active/total time checks, equipment checks, exact replacement
  locality, preview hash stability, and stale source-version rejection were
  deterministic enough for code-level tests.

### Where is a model judge needed, and where is code enough?

- Code is enough for schema, referential integrity, exact one-slot replacement,
  stale detection, and no-shopping boundary enforcement.
- A model or human judge may be useful later for recipe quality, taste,
  nutrition, cuisine fit, substitution quality, storage realism, and whether a
  replacement is actually desirable.

### How much did repair loop help versus regeneration?

- M6B did not introduce a recipe/replacement repair loop. The M6A repair loop
  remains useful as a bounded safety pattern, but M6B evidence only proves
  validation, rejection, and stale protection.
- Whether recipe repair is better than full regeneration remains a future
  model/product experiment.

### Did the format become too complex for a future local model?

- The current M6B format is still small enough for a local model experiment:
  one recipe draft, one target slot, and one replacement diff.
- It would become materially more complex if shopping list, store catalog,
  product matching, substitutions, or week/month menu planning were merged into
  the same output.

### Which decisions are needed before shopping list and mock catalog?

- Final recipe ingredient taxonomy.
- Unit system and unit conversion policy.
- Portion, leftovers, and household scaling semantics.
- Equipment/cookware taxonomy.
- Nutrition, budget, cuisine, substitution, and product matching semantics.
- Whether replacement should preserve, invalidate, or regenerate recipe
  versions for affected slots.
- Shopping-list contract, store catalog contract, product matching boundary,
  package/price/aisle data model, and confirmation UX.
- Provider/model/prompt/raw-output policy for any future model-backed recipe or
  replacement experiment.

## Remaining Assumptions And Open Questions

Relevant open questions are recorded in
`docs/decisions/open-questions.md`, especially OQ-007.

Remaining assumptions:

- M6B remains deterministic, fake-generator-only, and provider-free.
- M6B accepted menu fixtures and minimal confirmed-menu paths are technical
  test boundaries, not final product menu activation semantics.
- `available_equipment`, recipe units, portions, storage, reheating, and
  temperature fields are technical validation inputs, not final product
  taxonomy.
- Replacement comparison uses JSON-value equality for unaffected slots.
- Model-backed recipe/replacement generation remains skipped until a separate
  explicit decision.
- Shopping list, store catalog, product matching, package, price, aisle, and
  purchase arithmetic remain out of scope until later milestones.
