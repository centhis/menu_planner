# M4 profile vertical slice report

Date: 2026-07-10

## Goal

M4 proves the first deterministic business vertical slice for profile without
Hermes business adapter, Telegram UX, Intent Router, LLM generation, menu,
recipes, shopping list, store catalog, or substitutions.

The verified path is:

```text
structured command
-> ProfileDraft
-> validation
-> preview
-> persistent Confirmation
-> safe commit
-> ProfileVersion read-back
```

The main question was whether the M2 contracts/policy and M3 safe-commit
primitives support a real profile workflow without adding a probabilistic or
adapter-specific component.

## Scope

Included in M4:

- M4 Codex skill and guardrails.
- ADR-0006 with the minimal M4-only profile shape and deferred product
  decisions.
- deterministic `ProfileDraft` and `ProfileVersion` validation.
- valid and invalid profile fixtures with stable machine-readable errors.
- profile persistence mapping onto M3 versioned records.
- application commands and queries for draft, validation, preview,
  confirmation, commit, current profile read-back, and workflow status.
- temporary CLI/test API scenario for the profile happy path.
- negative tests for invalid input, workflow denial, confirmation failures,
  idempotency replay/conflict, stale version, and transaction rollback.
- SQL restart/read-back/audit coverage for the profile vertical slice.

Excluded from M4:

- LLM generation, repair loops, or eval harness.
- M5 Intent Router.
- production Hermes plugin or Hermes tool schemas.
- Telegram business UX and Telegram callbacks.
- menu, recipe, shopping list, store catalog, substitutions, or generated
  drafts.
- final product profile schema, taxonomies, onboarding UX, and user-facing
  confirmation copy.
- any custom Hermes image or mutation of the ready-made Hermes image.

## Implemented

- `.agents/skills/m4-profile-vertical-slice/SKILL.md` keeps the M4 boundary
  explicit.
- `docs/decisions/ADR-0006-profile-vertical-slice.md` records the M4-only
  technical profile shape and the M3 safe-commit mapping.
- `docs/decisions/open-questions.md` contains OQ-004 for final product profile
  decisions.
- `src/menu_planner/domain/contracts/validation.py` validates the M4 profile
  shape deterministically.
- `fixtures/domain/contracts/profile_draft/` and
  `fixtures/domain/contracts/profile_version/` cover valid and invalid profile
  contract examples.
- `src/menu_planner/application/profile_persistence.py` maps profile drafts and
  committed versions to M3 versioned records.
- `src/menu_planner/application/profile_service.py` provides the deterministic
  profile application commands and queries.
- `src/menu_planner/application/profile_scenario.py` provides a reusable
  test API for the full scenario.
- `src/menu_planner/bootstrap/profile_cli.py` provides the temporary CLI entry
  point.
- `docs/runbooks/m4-profile-scenario.md` documents the CLI command and
  idempotency replay behavior.
- `src/menu_planner/infrastructure/profile_sql.py` adapts profile persistence
  to the existing SQL versioned-record repository.
- `src/menu_planner/application/safe_commit.py` keeps one transactional commit
  path for profile and generic M3 records. During M4 SQL restart/audit testing,
  the write order was corrected so the audit event is inserted before the
  committed versioned record that references it. This preserves the existing
  M3 semantics and satisfies the PostgreSQL foreign key.

## Intentionally Not Implemented

- No final product meaning is assigned to fixture values such as `peanut`,
  `vegetables`, `stovetop`, `en-US`, or `UTC`.
- No HTTP API shape was selected for profile.
- No adapter-level idempotency key mapping was selected for Hermes, Telegram,
  or future HTTP clients.
- No user-facing default confirmation TTL was selected; M4 commands and tests
  use explicit `expires_at`.
- No production Hermes plugin, Telegram callback flow, or Intent Router was
  added.
- No menu, recipe, shopping list, store, or substitution workflow was added.

## Verification Commands

Commands run for the final M4 checks:

```text
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
git diff --check
```

Additional focused checks run during M4:

```text
docker compose run --rm app python -m pytest tests/unit/test_profile_sql.py -q
python3 -m compileall -q src/menu_planner/application/safe_commit.py tests/unit/test_profile_sql.py
git diff --no-index --check /dev/null tests/unit/test_profile_sql.py
docker compose run --rm app python -m menu_planner.bootstrap.profile_cli --help
```

Results from the final check pass:

```text
scripts/dev.sh test      -> 121 passed
scripts/dev.sh lint      -> All checks passed
scripts/dev.sh typecheck -> Success: no issues found in 54 source files
scripts/dev.sh smoke     -> smoke ok
git diff --check         -> ok
```

The Docker-based commands require Docker socket access in this sandbox. Initial
sandboxed attempts failed with a Docker permission error and were repeated with
explicit approval.

## Gate M4 Result

Result: passed for the deterministic profile vertical slice.

M4 proves that the profile workflow can reuse the M2 policy/contract surface
and M3 safe-commit primitives, including persistent confirmations,
idempotency, versioning, audit, transaction rollback, and read-back after a
process/service boundary. It does not prove product profile completeness or any
LLM/Hermes/Telegram adapter behavior.

## Gate M4 Checklist

[x] M4 Codex skill exists and was used for implementation tasks.
[x] ADR-0006 or equivalent decision note fixes the minimal M4 profile slice.
[x] Unknown final product profile fields are not invented.
[x] ProfileDraft validation is deterministic and tested.
[x] Invalid profile input returns machine-readable errors.
[x] Profile workflow uses M2 state machine/policy and blocks disallowed actions.
[x] Profile preview has canonical payload and human-readable summary.
[x] Profile confirmation is persistent and bound to user, operation, entity,
    version, draft and summary hash.
[x] Profile commit creates a new ProfileVersion.
[x] Profile commit writes audit in the same transaction.
[x] Idempotency replay does not create duplicate ProfileVersion.
[x] Idempotency payload mismatch is rejected.
[x] Stale preview/version mismatch cannot change confirmed profile.
[x] Current committed profile can be read after restart.
[x] CLI/test API scenario runs without Hermes, Telegram and LLM.
[x] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[x] No menu, recipe, shopping list, store catalog, Intent Router, LLM,
    production Hermes plugin or Telegram UX added.
[x] No Hermes image mutation or custom Hermes image added.
[x] scripts/dev.sh test passes.
[x] scripts/dev.sh lint passes.
[x] scripts/dev.sh typecheck passes.
[x] scripts/dev.sh smoke passes.
[x] git diff --check passes.
[x] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[x] M4 report is filled.

## Reflection

The profile workflow fit cleanly on top of the M2 contracts/policy surface and
M3 safe-commit primitives. M4 needed profile-specific mapping and application
commands, but did not need a second confirmation, idempotency, audit, or commit
path.

M3 commit semantics did not need to change for profile. The only M4-discovered
fix was SQL write ordering inside the same transaction: the audit event must
exist before the committed versioned record can reference it. The visible
commit semantics remain the same.

The application transaction boundary is the `SafeCommitUnitOfWork` used by
`SafeCommitOrchestrator.commit`. Profile code enters through
`ProfileApplicationService.commit_profile`, but the atomic write set is still
the M3 safe-commit transaction: idempotency start, confirmation validation,
version check, audit event, committed version, confirmation status, and
idempotency outcome.

The profile validation errors most likely to become user-facing through an
adapter are missing required fields, invalid primitive type, invalid enum-like
shape, and invalid range. Exact user copy is not selected in M4.

The fields actually needed for the vertical slice were only the M4 technical
shape: `user_facts`, `strict_restrictions`, and `soft_preferences`, with enough
primitive fields to prove object, array, string, and positive integer
validation.

The product profile fields that remain unresolved are tracked in OQ-004:
required MVP fields, meaning of people count, supported locales/time zones,
taxonomies for restrictions and preferences, budgets, calories, stores,
temporary wishes, confidence/source attribution, clarification history,
expiration, UX copy, and user-facing confirmation TTL.

The CLI/test API can be replaced by a Hermes HTTP adapter later without
changing Domain Core. The adapter should call the Application API and preserve
the same draft, preview, confirmation, idempotency, and commit boundaries.

Idempotency key formation after Hermes/Telegram is still unresolved. M4 uses an
explicit CLI/test key. Future adapters must decide how to derive stable keys
from HTTP headers, Hermes turn metadata, Telegram callback data, sessions, or a
separate application-generated token.

The confirmation TTL for real UX is not selected. M4 requires explicit
`expires_at` and tests both valid and expired confirmations.

Before M5, the project needs decisions about Intent Router placement, intent
confidence thresholds, ambiguity handling, eval/golden datasets, adapter-level
idempotency key mapping, user-facing confirmation TTL/copy, and which profile
fields can safely feed menu workflows.

## Remaining Assumptions

- ADR-0006 profile fields are technical assumptions only.
- One current committed profile per `user_id` is enough for M4.
- The M3 `m3_versioned_records` primitive remains the persistence target for
  M4 profile versions.
- CLI/test API callers provide explicit `expires_at` and idempotency keys.
- Adapter schema and HTTP API shape remain deferred.

## Decisions Before M5

- Confirm where Intent Router lives: application service, Hermes hook, tool, or
  another adapter boundary.
- Define confidence thresholds and ambiguity policies for profile-related
  intents.
- Define eval cases for dangerous state-changing misroutes.
- Choose adapter-level idempotency key mapping.
- Choose user-facing confirmation TTL and copy.
- Decide which profile fields and validation errors become product-facing
  before menu workflows depend on them.

Do not proceed to M5 without a separate explicit task.
