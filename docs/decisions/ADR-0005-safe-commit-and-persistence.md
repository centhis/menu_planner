# ADR-0005: Safe commit and persistence strategy

Date: 2026-07-10

Status: Accepted

## Context

Stage 3 / M3 must make confirmed state changes deterministic and safe before
any production profile workflow, menu workflow, LLM generation, Hermes business
adapter, Telegram business UX, or Intent Router work.

ADR-0001 selected PostgreSQL / Application DB for Menu Planner application
state and kept confirmed business state out of Hermes runtime memory. ADR-0002
selected Python 3.12, FastAPI, Psycopg 3, Alembic, and PostgreSQL for the
application runtime. ADR-0003 made the Application service responsible for
PostgreSQL schema, migrations, repositories, transaction boundaries, and
confirmed application state commits. ADR-0004 defined M2 domain contracts,
including `OperationPreview`, `Confirmation`, `AuditEvent`,
`PolicyDecision`, stable validation errors, state machine, and policy checks.

M2 deliberately stopped at contract and policy shape. Persistent
confirmations, idempotency storage, optimistic locking, committed version
storage, transaction orchestration, and audit persistence belong to M3.

The main M3 safety question is whether a repeat request, concurrent commit,
stale preview, expired confirmation, wrong user, version mismatch, restart, or
model error can damage confirmed data.

## Decision

Use generic M3 persistence primitives to prove safe commit mechanics before
creating production profile, menu, recipe, shopping list, or store tables.

### M3 persistence primitives

M3 migrations may create only these persistence primitives:

- `confirmations` for durable confirmation lifecycle state.
- `idempotency_records` for state-changing command replay and conflict
  detection.
- `audit_events` for durable machine-readable audit records.
- A minimal generic versioned-record table or equivalent test target for M3
  commit mechanics.

The generic versioned-record primitive exists only to test versioning,
optimistic locking, draft-vs-committed behavior, idempotency, rollback, and
audit. It must not become a production profile, menu, recipe, shopping list, or
store workflow by another name.

Production tables for profile, menu, recipe, shopping list, store catalog, and
Telegram UX state are forbidden until M4+ explicitly introduces them.

### Ports and adapters

Repository and application ports for confirmations, idempotency records,
versioned records, and audit live outside Domain Core in the application layer.

SQL adapters live in the infrastructure layer and implement those ports using
PostgreSQL. SQL, Psycopg, Alembic, ORM-like infrastructure, HTTP clients,
Hermes, Telegram, and model SDK imports must not enter Domain Core.

Hermes plugin/tools, when added in a later milestone, remain adapter layer and
call the Application HTTP API. They must not import Domain Core directly, apply
migrations, write to PostgreSQL, or depend on physical table layout.

### Transaction boundary

The Application service owns the safe commit transaction boundary.

A state-changing commit is one application use case that checks and writes in a
single database transaction:

- ownership by `user_id`;
- operation;
- entity identity;
- current committed version;
- `expected_version`;
- `draft_version`;
- confirmation status;
- confirmation expiration;
- `summary_hash`;
- idempotency key and request fingerprint;
- optimistic locking result.

The transaction must either complete all state changes or leave no partially
committed state. A successful commit writes the committed version, confirmation
status update, idempotency outcome, and audit event atomically.

### Isolation and locking

Use database transactions with row-level locking on the confirmation,
idempotency record, and target versioned record rows touched by a commit.

Use optimistic locking through `expected_version` as the application-level
conflict check. If the current committed version differs from
`expected_version`, the commit fails with a stable machine-readable version
mismatch error and must not create a new committed version.

If concurrent transactions race, the losing transaction must return a stable
machine-readable transaction conflict, version mismatch, idempotency replay, or
confirmation status error. It must not silently overwrite confirmed state.

### Draft and committed versions

M3 separates draft state from committed state at the persistence-primitive
level.

A draft version is candidate data that may be previewed and confirmed. A
committed version is the durable source of truth after a successful safe
commit. State-changing commits create or advance committed versions; they do
not mutate an older committed version in place.

Each committed version belongs to a `user_id` and an entity identity, carries a
monotonic integer version, and records enough metadata to connect it to the
confirmation, idempotency key, and audit event that produced it.

M3 may use a generic entity type and generic JSON-compatible payload for the
test primitive, but it must keep production business schemas out of scope.

### OperationPreview summary hash

`OperationPreview.summary_hash` is computed from a canonical JSON-compatible
payload, not from free-form user-facing text.

Canonicalization rules for M3:

- include stable committed-relevant fields such as `schema_version`,
  `operation`, `user_id`, `entity_id`, `expected_version`, `draft_version`,
  and the committed-relevant preview payload;
- sort object keys recursively;
- preserve array order because array order can be semantically relevant;
- use normalized JSON separators without insignificant whitespace;
- use UTF-8 bytes;
- hash with SHA-256 and store the lowercase hex digest.

Fields that only affect display wording, formatting, or adapter presentation
must not be the only source of the hash. Any change to committed-relevant
preview data must produce a different `summary_hash` and make an older
confirmation unusable for commit.

M3 accepts a strict split between technical preview data and user-facing
preview copy:

- technical canonical preview payload is required and drives `summary_hash`;
- user-facing preview copy is optional adapter/application presentation data;
- display-only wording changes must not invalidate confirmation;
- committed-relevant payload changes must invalidate confirmation;
- exact Telegram/user-facing copy is deferred until M4/M9 user workflows.

### Confirmation lifecycle

Persistent confirmations must support at least these statuses:

```text
pending
confirmed
committed
expired
rejected
used
```

M3 implementation may use a narrower physical state model if it still exposes
equivalent lifecycle behavior and stable machine-readable errors.

Commit requires a confirmation that matches:

- `confirmation_id`;
- `user_id`;
- `operation`;
- `entity_id`;
- `expected_version`;
- `draft_version`;
- non-expired `expires_at`;
- eligible status;
- `summary_hash`.

Pending confirmations must survive application restart because they live in
Application DB, not only in Hermes sessions, Telegram callbacks, process
memory, or local runtime files.

### Expiration policy

M3 must implement expiration checks through an explicit `expires_at` value
supplied by the application command or test.

M3 must not introduce a hidden default confirmation lifetime. Tests must cover
both non-expired and expired confirmations by supplying concrete `expires_at`
values.

Operation-specific default confirmation lifetimes are out of scope for M3. The
first user-facing workflow should start with one simple global default chosen
in M4 or M9, not with per-operation TTL policy in M3.

### Idempotency policy

State-changing commit commands require an idempotency key.

The idempotency key is scoped at minimum by `user_id`, operation, and key. The
stored record also keeps a request fingerprint or payload hash computed from
canonical committed-relevant command input.

Behavior:

- first request with a new key records the in-progress or completed outcome;
- repeat with the same key and same request fingerprint returns the stored
  predictable outcome or a controlled replay response;
- repeat with the same key and different request fingerprint fails with a
  stable machine-readable idempotency payload mismatch error;
- absence of a required key fails before commit with a stable
  machine-readable error.

For M3, the idempotency key is an explicit field on the application command.
Hermes, Telegram, HTTP header, callback, session, and turn-metadata mappings
are adapter concerns deferred until the corresponding Hermes/Telegram
milestones.

### Audit events

Audit events are written in the same transaction as the committed change they
describe.

M3 audit records must include enough machine-readable data to explain a commit
without relying on free-form log text:

- `audit_event_id`;
- `created_at`;
- `user_id`;
- operation;
- entity identity;
- previous version when applicable;
- new version when applicable;
- `confirmation_id`;
- idempotency key or idempotency record reference;
- `summary_hash`;
- result status;
- stable reason or error code when applicable;
- JSON-compatible metadata for diagnostics.

Audit write failure fails the whole commit transaction. A successful committed
change without its audit event is not allowed.

M3 does not add an audit cleanup, archival, or retention job. Audit events are
retained until explicit database reset or a later retention decision. The
schema must include `created_at` and stable machine-readable fields so a future
retention policy can be added without changing commit semantics.

### Restart behavior

After application restart, pending confirmations and idempotency records are
loaded from PostgreSQL and handled by the same checks as before restart.

A pending non-expired confirmation remains eligible for commit if all other
checks still match. An expired confirmation must fail predictably. A completed
idempotency record must still replay or conflict according to the stored
request fingerprint and outcome.

No M3 correctness property may depend on Hermes memory, Telegram callback
state, or process-local caches surviving restart.

### Rollback policy

M3 must prove database transaction rollback: injected failures during version
write, confirmation update, idempotency outcome write, or audit write must not
leave partially committed state.

Business rollback for MVP uses correcting versions rather than deleting or
rewriting committed history. M3 does not implement production business
rollback workflows; it only proves transaction rollback and preserves history
for future correcting versions.

## Consequences

- M3 can be tested without Hermes, Telegram, LLM calls, Intent Router, or
  production profile/menu workflows.
- The Application service remains the only component that applies migrations
  and writes confirmed state to Application DB.
- Domain Core remains persistence-implementation independent and continues to
  provide contracts, validation, policy, and deterministic rules.
- The generic M3 versioned-record primitive gives concurrency and idempotency
  tests a real database target without prematurely designing product entities.
- Future M4 profile workflow should reuse these safe commit primitives instead
  of introducing a separate profile-specific commit path.
- M3 commands use explicit `expires_at` and idempotency key fields, keeping
  transport-specific defaults and mappings out of the safe commit layer.
- M3 keeps audit records indefinitely in the application database until a later
  retention policy is selected.
- MVP business correction should create new versions instead of deleting or
  rewriting committed history.

## Not Decided Here

- Production profile, menu, recipe, shopping list, or store schemas and
  workflows.
- Exact user-facing preview copy for Telegram or other UI channels.
- User-facing global confirmation lifetime value for the first vertical
  workflow.
- Adapter mapping from Hermes/Telegram/HTTP transport metadata to the explicit
  M3 idempotency key command field.
- Audit retention duration, archival, deletion policy, and cleanup jobs beyond
  the M3 decision to retain records until a later policy exists.
- Intent Router confidence thresholds, eval harness, LLM generation, model
  adapters, Hermes plugin implementation, and Telegram business UX.
- Any change to the ready-made Hermes image, dashboard, gateway, auth flow,
  model provider, runtime state layout, or Docker daemon configuration.
