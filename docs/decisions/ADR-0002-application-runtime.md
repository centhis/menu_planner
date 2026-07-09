# ADR-0002: Application runtime and toolchain

Date: 2026-07-09

Status: Accepted

## Context

Stage 1 / M1 needs an empty reproducible application skeleton with
PostgreSQL, migrations, health/readiness checks, tests, lint/typecheck, and a
smoke check.

ADR-0001 selected an HTTP integration direction:

- Hermes plugin/tools call the application HTTP API;
- the application service owns use cases, validation, workflows, persistence,
  and commits;
- keep Domain Core independent of Hermes and Telegram imports;
- store Menu Planner application state in PostgreSQL / Application DB;
- keep confirmed business state out of Hermes runtime state.

The existing Stage 0 probe plugin is Python code loaded by Hermes from a
read-only host bind mount. Choosing Python for the application and Domain Core
keeps the first production plugin adapter thin while preserving a clean HTTP
service boundary.

The current host has `python3` 3.12 available, but no host `pip`/`ensurepip`.
Therefore M1 commands should be reproducible through the application container
and project command entrypoints, not by relying on host Python package
installation.

## Decision

Use Python 3.12 for the Menu Planner application runtime and Domain Core.

### Language and version

- Language: Python.
- Version: Python 3.12.
- Runtime location: an application container/service, separate from the Hermes
  image.

### Dependency manager

Use `pip` inside the application environment.

The project will keep dependency inputs and pinned install files in Git:

```text
requirements.in
requirements-dev.in
requirements.txt
requirements-dev.txt
```

`requirements*.txt` files are the committed lock artifacts. They must pin exact
versions. Dependency changes must update the relevant input and pinned output
files in the same task.

Do not add new production dependencies without an ADR update or an explicit
task that names the dependency and its purpose.

### Application service shape

Use a small ASGI HTTP application.

Initial shape for M1:

- an application service in `compose.yaml`;
- source mounted from the project workspace;
- configuration read from environment variables;
- `GET /healthz` for process health;
- `GET /readyz` for readiness of the whole local system path: application
  process, PostgreSQL connectivity, migration state, and Hermes reachability;
- no profile, menu, recipe, shopping list, or production workflow endpoints.

The application service owns its Dockerfile and container image setup. Building
the application image is allowed and expected because dependencies are
installed in that image.

Any Dockerfile added for this project must be for the application only and must
not be used as, named as, or treated as a Hermes image. `docker compose build
app` is allowed; `docker compose build hermes` is forbidden.

### Configuration boundary

`.env` stores primitive values and secrets only. Derived values such as
`DATABASE_URL` are assembled in Compose or by the application from primitive
configuration.

### Persistence ownership

The application service owns PostgreSQL schema, Alembic migrations,
repositories, and transaction boundaries. Hermes must not apply migrations,
write directly to the application database, or depend on the physical schema.

### Production dependencies

Use these production components for the M1 skeleton:

- FastAPI for the ASGI application surface;
- Uvicorn for the local ASGI server;
- Psycopg 3 for PostgreSQL connectivity;
- Alembic for migrations.

Exact package versions are selected when the pinned requirements files are
created.

### Formatter

Use Ruff formatter.

### Linter

Use Ruff lint.

### Type checker

Use mypy.

Python source in `src/` should be type-annotated from the start. M1 typecheck
scope is the empty application skeleton and migration/support code only.

### Test runner

Use pytest.

M1 tests should cover:

- config parsing without secrets in logs;
- health/readiness behavior;
- PostgreSQL connectivity through the application boundary;
- migration/smoke behavior where practical.

Tests must not require a real Hermes agent turn.

### Migration tool

Use Alembic.

M1 should add an empty initial migration or baseline migration only. Domain
tables for profile, menu, recipes, shopping list, confirmations, or workflows
are out of scope until later milestones.

### Command entrypoint

Use `make` as the developer-facing command entrypoint.

Expected command set:

```text
make setup
make format
make format-check
make lint
make typecheck
make test
make migrate
make smoke
make check
make clean-runtime
```

`make check` should be the local CI-equivalent command for M1 and should run
format-check, lint, typecheck, tests, and smoke checks once the skeleton exists.

### CI command set

Until a hosted CI system is added, the reproducible CI command is:

```text
make check
```

If a CI workflow is added during M1, it should execute the same command set
rather than defining a separate behavior.

## Consequences

- M1 can keep the production Menu Planner plugin thin because Hermes plugin
  code only needs to call the application HTTP API.
- PostgreSQL is the application source of truth from the skeleton onward.
- Host Python package availability is not a prerequisite for a clean checkout;
  project commands should run through the application container/environment.
- Node, Go, Rust, and local-model tooling are not selected for M1 application
  development.

## Out of scope for this decision

- Production cloud provider and model IDs.
- Production-grade Hermes dashboard authentication.
- Telegram business UX.
- Domain schemas for profile, menu, recipes, shopping list, workflows, or
  confirmations.
- Exact pinned package versions, which are fixed when dependency files are
  added.
