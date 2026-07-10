# ADR-0004: Domain contracts and validation strategy

Date: 2026-07-10

Status: Accepted

## Context

Stage 2 / M2 must add deterministic domain contracts, validation, stable
machine-readable errors, state machine rules, and policy checks before any LLM,
Hermes business adapter, Telegram business UX, or persistence/commit work.

ADR-0002 selected Python 3.12 for the application runtime and Domain Core.
ADR-0003 kept Domain Core independent from Hermes, Telegram, ORM, HTTP clients,
model SDKs, and PostgreSQL transaction boundaries.

M2 needs one primary contract format so contracts do not drift between Python
types, JSON examples, fixtures, and future tool schemas. Stage 2 also forbids
new production dependencies without an explicit decision.

## Decision

Use Python standard-library domain contracts as the primary source of truth for
M2.

### Primary contract format

M2 contracts are Python dataclasses, enums, and typed aliases under the Domain
Core package:

```text
src/menu_planner/domain/contracts/
```

Contracts must stay framework-independent and must not import FastAPI,
Pydantic, SQLAlchemy, Psycopg, Alembic, Hermes, Telegram, HTTP clients, or model
SDKs.

Every M2 contract has an explicit `schema_version` field. The initial M2
contract version is a literal string:

```text
m2.v1
```

The value is a technical contract version, not a product or API stability
promise.

### Runtime validators

Runtime validators live next to the contracts:

```text
src/menu_planner/domain/contracts/validation.py
```

Validators accept untrusted JSON-compatible Python values (`dict`, `list`,
`str`, `int`, `float`, `bool`, and `None`) and return either a typed contract
object or a controlled validation result. They must not raise raw parser,
`KeyError`, `TypeError`, or framework exceptions across the Domain Core
boundary for expected invalid input.

Validation is explicit Python code in M2. Do not add a production validation
library for M2.

### JSON-compatible schema checks

M2 does not adopt JSON Schema, OpenAPI schema generation, or Pydantic schema
generation as the source of truth.

JSON compatibility is checked through contract tests that load canonical JSON
fixtures, run the runtime validators, and compare stable machine-readable
errors for invalid examples.

If a future Hermes tool schema, HTTP API schema, or JSON Schema export is
needed, it must be derived from the accepted Domain Core contracts through a
separate adapter-layer decision. The adapter schema must not become the primary
domain contract.

### Fixtures

Contract fixtures live outside production code:

```text
fixtures/domain/contracts/
```

Use this shape:

```text
fixtures/domain/contracts/<contract-name>/valid/*.json
fixtures/domain/contracts/<contract-name>/invalid/*.json
```

Each contract added in M2 must have at least one valid fixture and at least one
invalid fixture. Invalid fixtures must document the expected stable error code
in the corresponding contract test, not only in prose.

### Validation errors

Validation errors are stable, machine-readable objects, not free-form text.

The error catalog lives in:

```text
src/menu_planner/domain/errors.py
```

Error objects use this minimum shape:

```json
{
  "code": "contract.invalid_schema_version",
  "message": "Human-readable diagnostic for logs and tests.",
  "path": ["schema_version"],
  "details": {}
}
```

Rules:

- `code` is stable and snake_case dot-separated.
- `message` is diagnostic only; callers must branch on `code`.
- `path` points to the invalid field or array item when possible.
- `details` contains JSON-compatible diagnostic data only.
- Validation may return multiple errors when that helps repair, but tests for
  forbidden policy or workflow transitions must assert the stable error code.

### Naming and versioning policy

Python contract classes use PascalCase names matching Stage 2 contract names,
for example `ParsedIntent`, `MenuDraft`, `PolicyDecision`, and
`OperationPreview`.

Serialized JSON field names use `snake_case`.

Enum values use lowercase `snake_case` strings.

Breaking changes require a new `schema_version` value and compatibility tests.
M2 only defines `m2.v1`; migration between schema versions is out of scope until
a later stage explicitly needs it.

### Dependency policy

No new production dependency is added for M2 contract validation.

The fact that FastAPI brings Pydantic transitively is not a Domain Core
architecture decision. Domain Core must not depend on Pydantic unless a later
ADR or explicit task selects it as a production dependency for this purpose.

## Consequences

- M2 contracts can be validated without Hermes, LLM, Telegram, PostgreSQL, or
  HTTP API infrastructure.
- Tests can exercise the same validators that future application use cases and
  adapter layers will call.
- The approach is more verbose than schema-library-based validation, but keeps
  M2 dependency-free and makes stable domain errors explicit.
- Future adapter schemas for Hermes tools or HTTP endpoints may duplicate some
  shape information, but they remain adapters over Domain Core contracts.

## Not Decided Here

- PostgreSQL tables, repositories, migrations for domain entities, transaction
  boundaries, commit, idempotency persistence, and audit storage.
- Confirmation commit behavior beyond contract shape and policy decisions.
- Production profile, menu, recipe, shopping list, or store workflows.
- Intent Router M5, confidence thresholds, eval harnesses, and model adapters.
- Hermes plugin implementation and Telegram business UX.
- JSON Schema or OpenAPI generation as a source of truth.
- Schema migration mechanics beyond requiring explicit `schema_version`.
