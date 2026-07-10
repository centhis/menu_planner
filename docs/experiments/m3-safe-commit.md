# M3 safe commit report

Date: 2026-07-10

## Environment

- Workspace: `/home/centhis/menu_planner`
- Application runtime: Python 3.12 in the application container.
- Database: PostgreSQL 16 through Docker Compose.
- Test runner: pytest.
- Linter/formatter: Ruff.
- Type checker: mypy.
- M3 was verified without a real Hermes agent turn, LLM call, Telegram callback,
  or production Menu Planner Hermes plugin.
- `.env`, `auth.json`, tokens, and credentials were not opened or copied into
  this report.

## Persistence strategy

M3 uses generic safe-commit primitives instead of production profile, menu,
recipe, shopping-list, or store tables.

Implemented primitives:

- persistent confirmations;
- idempotency records scoped by user, operation, and key;
- audit events;
- generic `m3_versioned_records` for draft and committed version mechanics.

Application-layer ports and the transaction orchestration live in
`src/menu_planner/application/safe_commit.py`. SQL adapters and the unit of
work live in `src/menu_planner/infrastructure/safe_commit_sql.py`.

Domain Core remains framework- and runtime-independent. Boundary tests cover
that Domain Core does not import application, infrastructure, adapters, ORM,
HTTP clients, Hermes, Telegram, or model SDK modules.

## Migration summary

Migration:

```text
migrations/versions/20260710_0002_m3_safe_commit_primitives.py
```

It creates only M3 primitives:

- `confirmations`
- `idempotency_records`
- `audit_events`
- `m3_versioned_records`

It does not create production profile, menu, recipe, shopping-list, store, LLM,
Hermes plugin, or Telegram business tables.

Current migration status:

```text
20260710_0002 (head)
```

## Preview and hash

`OperationPreview.summary_hash` is derived from canonical committed-relevant
payload data:

- `schema_version`
- `operation`
- `user_id`
- `entity_type`
- `entity_id`
- `expected_version`
- `draft_version`
- `committed_relevant_payload`

The hash uses JSON canonicalization with sorted keys, compact separators,
UTF-8 bytes, and SHA-256 lowercase hex output.

Covered behavior:

- object key order does not change the hash;
- committed-relevant payload, version, or user changes do change the hash;
- display-only wording in preview changes does not drive the hash;
- `build_operation_preview` uses the computed hash.

## Confirmation lifecycle

Persistent confirmation lifecycle is implemented in the application layer.

Covered behavior:

- create pending confirmation;
- lookup by user;
- confirm pending confirmation;
- validate confirmed confirmation for commit;
- reject pending confirmation;
- reject expired confirmation with stable machine-readable error;
- reject wrong-user confirmation with stable machine-readable error;
- reject stale preview hash with stable machine-readable error;
- reject rejected or already used confirmations;
- preserve pending confirmation across a new lifecycle instance;
- preserve confirmation across a new SQL repository/connection before confirm.

Expiration is checked through explicit `expires_at`. M3 does not introduce a
hidden default TTL.

## Idempotency behavior

Idempotency is implemented with a canonical request fingerprint over
committed-relevant command input.

Covered behavior:

- missing key is rejected;
- first request creates an in-progress record;
- completed outcome can be recorded;
- same key and same payload returns controlled replay;
- same key and different payload returns stable machine-readable conflict;
- failed commit validation records a failed idempotency outcome.

The idempotency key remains an explicit application-command field in M3.
HTTP headers, Hermes turn metadata, Telegram callbacks, and session mappings
are deferred adapter concerns.

## Transaction and audit behavior

`SafeCommitOrchestrator` performs generic M3 commit orchestration through a
unit of work:

- starts idempotency;
- validates confirmation;
- checks current committed version against `expected_version`;
- checks draft version existence;
- writes committed version from draft payload;
- marks confirmation committed;
- records idempotency outcome;
- writes audit event;
- commits or rolls back the unit of work.

Covered behavior:

- happy path writes committed version, confirmation status, idempotency outcome,
  and audit event;
- version mismatch blocks commit;
- draft version mismatch blocks commit;
- changed preview blocks commit;
- expired confirmation blocks commit;
- wrong-user confirmation blocks commit;
- reused confirmation with a new idempotency key is rejected;
- repeated same idempotency key and same payload returns replay;
- repeated same idempotency key and different payload is rejected;
- stale concurrent commit attempt is rejected without sleep-only synchronization;
- audit write failure rolls back partial commit state;
- version write failure rolls back partial commit state.

SQL `get_current_committed` uses `for update`, and the versioned-record table
has a unique constraint on user/entity/version/status to prevent duplicate
committed rows for the same generic version.

## Commands

Commands run for Gate M3 verification:

```text
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh migration-status
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
scripts/dev.sh test             -> 99 passed
scripts/dev.sh lint             -> All checks passed
scripts/dev.sh typecheck        -> Success: no issues found in 46 source files
scripts/dev.sh migration-status -> 20260710_0002 (head)
scripts/dev.sh smoke            -> smoke ok
git diff --check                -> ok
```

`git diff --no-index --check /dev/null` was also run for the new M3 test files;
it produced no whitespace diagnostics. Exit code `1` is expected for no-index
comparison against `/dev/null`.

## Boundary checks

`docker compose config --services`:

```text
postgres
app
hermes
```

`docker compose config --images`:

```text
menu-planner-app:local
nousresearch/hermes-agent:v2026.6.19
postgres:16-alpine
```

`rg -n '^\s*build\s*:' compose.yaml`:

```text
60:    build:
```

Manual interpretation:

- `build:` is present only for the application service.
- Hermes still uses the ready-made `nousresearch/hermes-agent:v2026.6.19`
  image.
- No custom Hermes image was added.
- M3 tests do not require a Hermes agent turn, Telegram callback, or LLM call.

`find . -iname 'Dockerfile*' -print`:

```text
./Dockerfile.app
```

## Known limits

- M3 proves generic safe-commit mechanics only. It does not implement
  production profile, menu, recipe, shopping-list, or store workflows.
- No LLM generation, Intent Router, production Hermes plugin, Telegram
  business UX, or Telegram callback mapping was added.
- The concurrency test covers deterministic stale-version behavior without
  sleep-only synchronization. A heavier future PostgreSQL integration stress
  test can be added when a production vertical slice needs it.
- User-facing confirmation copy and default confirmation TTL remain deferred to
  a later user-workflow or adapter milestone.
- Business correction policy remains the ADR-0005 MVP policy: create
  correcting versions rather than deleting or rewriting committed history.

## Gate M3 result

Result: passed for M3 generic safe commit.

Gate checklist:

```text
[x] M3 Codex skill exists and is usable.
[x] ADR-0005 safe commit and persistence strategy accepted.
[x] M3 error catalog additions are stable and tested.
[x] M3 persistence migrations exist.
[x] Migrations do not create production profile/menu/recipe/shopping workflows.
[x] Repository/application ports exist outside Domain Core.
[x] SQL adapters live outside Domain Core.
[x] Domain import-boundary tests still pass.
[x] OperationPreview summary_hash is deterministic.
[x] Changed preview invalidates old confirmation.
[x] Persistent Confirmation lifecycle is implemented and tested.
[x] Expired confirmation cannot commit.
[x] Wrong-user confirmation cannot commit.
[x] Used/replayed confirmation behavior follows ADR-0005.
[x] Idempotency storage is implemented and tested.
[x] Same idempotency key with different payload is rejected.
[x] Transactional commit checks ownership, operation, version, confirmation,
    summary_hash and idempotency.
[x] Concurrent commit is safe.
[x] Audit event is written in the same transaction as commit.
[x] Rollback leaves no partial committed state.
[x] Restart between preview and confirm is covered.
[x] No LLM generation, Intent Router, production Hermes plugin, or Telegram UX
    added.
[x] No Hermes image mutation or custom Hermes image added.
[x] scripts/dev.sh test passes.
[x] scripts/dev.sh lint passes.
[x] scripts/dev.sh typecheck passes.
[x] scripts/dev.sh smoke passes.
[x] git diff --check passes.
[x] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[x] M3 report is filled.
```

## Reflection

- Generic M3 primitives are sufficient to start a first profile vertical slice
  without rewriting the commit model, as long as M4 maps profile drafts and
  committed profile versions onto the same preview-confirm-commit flow.
- The actual transaction boundary is the application unit of work, implemented
  by `SafeCommitUnitOfWork` and `SqlSafeCommitUnitOfWork`.
- ORM, SQL, infrastructure imports, HTTP clients, Hermes, Telegram, and model
  SDK imports did not enter Domain Core.
- Commit errors that affect user action can become user-facing through adapter
  copy later: expired confirmation, stale preview, wrong confirmation status,
  version mismatch, and idempotency replay/conflict. Raw transaction conflict
  details should remain developer diagnostics.
- Explicit `expires_at` is supplied by tests/application commands and compared
  directly during confirmation validation. M3 does not choose a hidden default.
- Repeat after restart is handled through persisted confirmation and
  idempotency records, not process memory.
- Audit trail for successful generic committed changes includes user,
  operation, entity identity, previous/new version, confirmation id,
  idempotency key, summary hash, result status, and metadata.
- Correcting versions without deleting committed history remains enough for
  the MVP safe-commit policy.
- Before M4, the main remaining decisions are profile draft shape, user-facing
  confirmation TTL, HTTP/API mapping, and adapter-level idempotency key source.
- ADR-0001 through ADR-0004 do not need changes for M3; ADR-0005 records the
  new persistence and safe-commit decisions.
