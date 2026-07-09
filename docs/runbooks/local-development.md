# Local development runbook

This runbook covers the Stage 1 / M1 walking skeleton only. It is for the
empty reproducible application runtime, PostgreSQL, migrations, tests, and
smoke checks. It does not cover profile, menu, recipes, shopping list,
production workflows, Telegram business UX, or a production Menu Planner
plugin.

## Prerequisites

- Docker and Docker Compose are available.
- `python3` is available for the current bootstrap commands.
- Real secrets stay only in local `.env`.
- Do not install packages inside the Hermes container.
- Do not edit files inside running containers.

`make` is the intended developer-facing command entrypoint. On hosts where
`make` is not installed, use the equivalent `scripts/dev.sh <command>` form.

## Prepare `.env`

Create a local `.env` from the example:

```bash
cp .env.example .env
```

Fill only local values in `.env`. Never commit `.env`, `auth.json`, API keys,
Telegram tokens, dashboard passwords, session secrets, or private keys.

Required local values include:

```text
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD
HERMES_DASHBOARD_BASIC_AUTH_SECRET
TELEGRAM_BOT_TOKEN
TELEGRAM_ALLOWED_USERS
POSTGRES_PASSWORD
```

`POSTGRES_DB` and `POSTGRES_USER` can keep the example defaults for local M1
development. `DATABASE_URL` is assembled in `compose.yaml` from the Postgres
settings and should not be duplicated in `.env`.

The project rule is: `.env` stores primitive values and secrets only; Compose
or the application assembles derived values such as `DATABASE_URL`.

## Validate Setup

Use:

```bash
scripts/dev.sh setup
```

or, when `make` is installed:

```bash
make setup
```

This verifies that Python is available and Docker Compose can parse the local
configuration. It does not start the full product.

## Start Services

Use:

```bash
scripts/dev.sh up
```

or:

```bash
make up
```

At the current M1 stage this starts PostgreSQL and the application service.
Hermes is part of the same Compose project and is a critical external runtime
component for the full local system path.

Check services with:

```bash
docker compose ps
```

## Apply Migrations

Use:

```bash
scripts/dev.sh migrate
```

or:

```bash
make migrate
```

Migrations are applied by the application container. The application service
owns PostgreSQL schema, Alembic migrations, repositories, and transaction
boundaries; Hermes must not apply migrations or write directly to the
application database.

Check migration status with:

```bash
scripts/dev.sh migration-status
```

or:

```bash
make migration-status
```

## Run Tests

Use:

```bash
scripts/dev.sh test
```

or:

```bash
make test
```

The current test suite covers configuration redaction, health/readiness logic,
database probe errors, migration baseline constraints, command entrypoints, and
smoke-script structure. Tests do not require a real Hermes agent turn.

## Run Smoke

Use:

```bash
scripts/dev.sh smoke
```

or:

```bash
make smoke
```

Smoke checks:

- Compose services include `hermes` and `postgres`;
- Compose images include the ready Hermes image, PostgreSQL image, and
  application image;
- named volumes include `hermes-data` and `postgres-data`;
- `compose.yaml` does not contain `build:` under the `hermes` service;
- Stage 0 probe plugin is not mounted or enabled in the default runtime;
- `Dockerfile.app` is the only Dockerfile and belongs only to the application
  service;
- `docker compose build app` is allowed and expected when dependencies or image
  contents change;
- `docker compose build hermes` is forbidden;
- unit tests pass;
- application health/readiness logic works, with `/readyz` covering app,
  PostgreSQL, migration state, and Hermes for the full local system path;
- PostgreSQL readiness is checked with `pg_isready` when the container is
  running;
- migration status is checked when Alembic is available.

If Docker runtime access is unavailable or a dependency is not running, smoke
prints a documented `deferred` message for that part.

## Run Local Check

Use:

```bash
scripts/dev.sh check
```

or:

```bash
make check
```

The command runs the checks available for M1: format-check, lint, typecheck,
unit tests, smoke, HTTP health/readiness, DB checks, and migration status.

## Stop Services

Use:

```bash
scripts/dev.sh down
```

or:

```bash
make down
```

This stops the Compose project without deleting named volumes.

Use this carefully: if Hermes is running in the same Compose project, `down`
stops Hermes too.

## Clean Generated Files

Use:

```bash
scripts/dev.sh clean
```

or:

```bash
make clean
```

This removes Python `__pycache__` directories under `src`, `tests`, and
`migrations`.

## Delete Local Runtime State

Destructive reset is intentionally not part of the normal workflow. Treat it as
a release/reproducibility drill or emergency reset only.

Warning: this deletes named volumes, including PostgreSQL application state and
Hermes runtime state for this Compose project. It can also remove Hermes Codex
authorization state stored in the Hermes volume.

Run only after an explicit operator decision:

```bash
docker compose down -v
```

After deleting volumes, recreate the local M1 state with:

```bash
scripts/dev.sh up
scripts/dev.sh migrate
scripts/dev.sh smoke
```

or the equivalent `make` commands when `make` is available.

## Current M1 Limits

- No business entities or production workflows are implemented in M1.
- M2 API/use-case boundaries are intentionally deferred to planning the next
  stage.
- Runtime/development image split is intentionally deferred to planning the
  next stage; M1 keeps test/lint/typecheck tooling in the application image for
  reproducible local checks.
- Production model/provider selection and production-grade Hermes dashboard
  auth are still later decisions.
