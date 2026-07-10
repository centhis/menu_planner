# M2 domain skeleton report

Date: 2026-07-10

## Environment

- Workspace: `/home/centhis/menu_planner`
- Application runtime: Python 3.12 in the application container.
- Test runner: pytest.
- Linter/formatter: Ruff.
- Type checker: mypy.
- Runtime services are managed by Docker Compose.
- Secrets are expected in local `.env`; `.env`, `auth.json`, tokens, and
  credentials were not opened or copied into this report.

## Contract strategy

- Contract format is accepted in
  `docs/decisions/ADR-0004-domain-contracts-and-validation.md`.
- Primary M2 contracts are Python standard-library dataclasses and enums in
  `src/menu_planner/domain/contracts/`.
- Runtime validators live in
  `src/menu_planner/domain/contracts/validation.py`.
- All M2 contracts require `schema_version`.
- Initial M2 schema version is `m2.v1`.
- JSON compatibility is checked through fixtures and contract tests, not by
  adopting JSON Schema, OpenAPI, or Pydantic as the domain source of truth.
- No production dependency was added for M2 validation.

## Contracts and fixtures

Domain source files:

```text
src/menu_planner/domain/__init__.py
src/menu_planner/domain/contracts/__init__.py
src/menu_planner/domain/contracts/models.py
src/menu_planner/domain/contracts/validation.py
src/menu_planner/domain/errors.py
src/menu_planner/domain/policy.py
src/menu_planner/domain/workflow.py
```

M2 contract groups: 20.

JSON fixtures: 40 total, one valid and one invalid fixture for each contract
group under:

```text
fixtures/domain/contracts/
```

Contracts covered:

- `ParsedIntent`
- `ProfileDraft`
- `ProfileVersion`
- `PlanningContext`
- `MealSlot`
- `MenuDraft`
- `MenuVersion`
- `Ingredient`
- `RecipeDraft`
- `RecipeVersion`
- `ShoppingListItem`
- `ShoppingList`
- `WorkflowRun`
- `ValidationResult`
- `OperationPreview`
- `Confirmation`
- `PolicyDecision`
- `AuditEvent`
- `ToolSuccessEnvelope`
- `ToolErrorEnvelope`

Contract tests verify:

- fixture directories exist for every registered contract;
- every contract model has `schema_version`;
- valid fixtures validate;
- invalid fixtures fail with stable machine-readable errors.

## Error catalog

Stable error catalog lives in:

```text
src/menu_planner/domain/errors.py
```

The catalog includes:

- `contract.invalid_shape`
- `contract.invalid_enum_value`
- `contract.invalid_field_type`
- `contract.invalid_range`
- `contract.invalid_schema_version`
- `contract.missing_required_field`
- `policy.action_not_allowed`
- `policy.administrative_action_denied`
- `policy.ambiguous_or_incomplete_intent`
- `policy.ownership_required`
- `policy.retry_limit_reached`
- `policy.unsupported_intent`

Each catalog entry has:

- stable `code`;
- developer message;
- machine fields;
- possible sources;
- user exposure policy.

Validation and policy errors are created through catalog-backed factories.
Tests verify code stability, metadata, JSON adapter shape, and validation use
of catalog-backed errors.

## State machine and policy

State machine lives in:

```text
src/menu_planner/domain/workflow.py
```

It defines:

- explicit state table for all `WorkflowState` values;
- `WorkflowAction`;
- operation class mapping;
- allowed actions;
- transitions;
- required data names;
- terminal states;
- retry policy;
- machine errors for denied, administrative, unsupported, and retry-limit
  outcomes.

Policy decision layer lives in:

```text
src/menu_planner/domain/policy.py
```

It accepts `ParsedIntent` and `WorkflowRun`, maps intent names to
`WorkflowAction`, checks state-machine policy, and returns `PolicyDecision`.

Covered outcomes:

- `allow`
- `deny`
- `clarify`
- `confirm`
- `unsupported`

State-changing operations in M2 return `confirm` and
`requires_confirmation=true`; they do not mutate confirmed state, persist
confirmation objects, or perform commit.

## Commands

Host `make` was not available in this Codex environment:

```text
make test      -> /bin/bash: line 1: make: command not found
make lint      -> /bin/bash: line 1: make: command not found
make typecheck -> /bin/bash: line 1: make: command not found
make smoke     -> /bin/bash: line 1: make: command not found
```

Equivalent project commands were run through `scripts/dev.sh`:

```text
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
git diff --check
docker compose config --services
docker compose config --images
rg -n '^\s*build\s*:' compose.yaml
find . -iname 'Dockerfile*' -print
```

The `scripts/dev.sh` and Docker Compose commands require Docker socket access
in this sandbox and were run with explicit approval.

## Checks

Passing checks:

```text
scripts/dev.sh test      -> 56 passed
scripts/dev.sh lint      -> All checks passed
scripts/dev.sh typecheck -> Success: no issues found in 37 source files
scripts/dev.sh smoke     -> smoke ok
git diff --check         -> ok
```

Smoke coverage includes:

- Compose structure;
- skeleton tests;
- application health logic;
- PostgreSQL readiness;
- HTTP health/readiness;
- Alembic migration status.

M2 tests do not require a real Hermes agent turn, LLM generation, Telegram UX,
or PostgreSQL domain tables.

## Boundary checks

`docker compose config --services`:

```text
postgres
app
hermes
```

`docker compose config --images`:

```text
postgres:16-alpine
menu-planner-app:local
nousresearch/hermes-agent:v2026.6.19
```

`rg -n '^\s*build\s*:' compose.yaml`:

```text
60:    build:
```

Manual interpretation: the only `build:` entry is under the `app` service.
The `hermes` service uses the ready-made image and has no `build:` section.

`find . -iname 'Dockerfile*' -print`:

```text
./Dockerfile.app
```

Manual interpretation: the only Dockerfile belongs to the application service.
No Hermes Dockerfile, custom Hermes image, `docker compose build hermes`, or
Hermes container mutation was added.

## Known limits

- M2 implements deterministic contracts, validation, error catalog, state
  machine, and policy decisions only.
- M2 does not implement PostgreSQL domain tables, repositories, transaction
  boundaries, confirmation commit, idempotency persistence, or audit storage.
- M2 does not implement production profile, menu, recipe, shopping list, or
  store workflows.
- M2 does not implement LLM generation, Intent Router M5, eval harnesses,
  model adapters, production Hermes plugin, or Telegram business UX.
- Product-specific fields remain intentionally minimal; unresolved product
  choices are not guessed.
- `PolicyDecision` reaches preview/confirmation policy only. Actual commit and
  persistent confirmation belong to M3.
- Host `make` is unavailable in this environment, so the verified command path
  is `scripts/dev.sh ...`.
- `git status --short` currently includes accumulated untracked M2 files from
  this stage; `git diff --stat` does not show untracked files.

## Gate M2 result

Gate M2 is satisfied for the deterministic domain skeleton path:

- M2 Codex skill exists and is usable.
- ADR-0004 is accepted.
- Domain Core boundary exists.
- Import-boundary tests protect Domain Core from Hermes, Telegram, ORM, HTTP,
  and model SDK imports.
- Contract fixtures exist for all M2 contracts.
- Every M2 contract requires `schema_version`.
- Invalid fixtures fail with stable machine-readable errors.
- Stable error catalog exists and is used by validation and policy.
- State machine is explicit and test-covered.
- Operation classes are implemented.
- PolicyDecision outcomes are test-covered.
- Negative transition matrix blocks forbidden actions.
- Administrative action is denied in user workflow.
- No domain PostgreSQL tables or M3 persistence/commit were added.
- No LLM generation, Intent Router, production Hermes plugin, or Telegram UX
  was added.
- Equivalent `make` checks pass through `scripts/dev.sh`.
- `git diff --check` passes.
- This M2 report is filled.

## Reflection

Rules that are domain-level:

- operation classes;
- schema versioning;
- machine-readable validation errors;
- state transitions;
- retry limits;
- administrative action denial in user workflow;
- policy outcomes and confirmation requirement for state-changing operations.

Rules that are interface-level or later adapter work:

- user-facing wording for errors;
- Telegram button/callback mapping;
- Hermes tool schemas;
- HTTP API schemas;
- LLM repair loop prompts;
- actual user clarification UX.

No current M2 state exists only because of Telegram. The state machine can be
run entirely without LLM and Hermes, as shown by unit and contract tests.

Transitions that may need review before production workflow work:

- how much of recipe generation and product matching should be separate states;
- whether shopping-list building should be its own state after matching;
- whether `ready` should remain terminal once purchase-checklist interactions
  are introduced.

The stable error catalog is sufficient for M2 and for a future repair-loop
starting point, but M3/M4 may need more precise commit, idempotency, ownership,
version-conflict, and audit errors.

Persistence, commit, and real production business workflows did not enter M2.

Fields requiring human or later-stage decision before M3/M4 include:

- exact product/profile field semantics;
- concrete confidence thresholds;
- confirmation expiration rules;
- versioning and idempotency keys;
- audit retention fields;
- exact user-facing clarification strategy.

No ADR update is required immediately for ADR-0001, ADR-0002, ADR-0003, or
ADR-0004. ADR-0004 remains accurate for the implemented standard-library
contract and validation approach.
