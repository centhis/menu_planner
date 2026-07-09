# M1 walking skeleton report

Date: 2026-07-09

## Environment

- Workspace: `/home/centhis/menu_planner`
- Runtime services are managed by Docker Compose.
- Secrets are expected in local `.env`; `.env` was not opened or copied into
  this report.

## Runtime and toolchain

- Application runtime: Python 3.12.
- Dependency policy: pinned `requirements.txt` and `requirements-dev.txt`,
  sourced from `requirements.in` and `requirements-dev.in`.
- Web runtime: FastAPI with Uvicorn.
- Database driver: psycopg 3.
- Migration tool: Alembic.
- Test runner: pytest.
- Linter/formatter: Ruff.
- Type checker: mypy strict mode for `src`, `tests`, and `migrations`.

## Compose services

`docker compose config --services`:

```text
postgres
app
hermes
```

`docker compose config --images`:

```text
nousresearch/hermes-agent:v2026.6.19
postgres:16-alpine
menu-planner-app:local
```

`docker compose config --volumes`:

```text
hermes-data
postgres-data
```

Hermes remains on the ready-made image and has no `build:` section. The only
Dockerfile in the repository is `Dockerfile.app`, which belongs to the
application service.

The application image is project-owned. Building it is allowed and expected
when dependencies or image contents change. Building Hermes remains forbidden.

## Database

- PostgreSQL runs as the `postgres` Compose service.
- Application DB connection settings are assembled into `DATABASE_URL` inside
  `compose.yaml` from `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.
- `.env` stores primitive values and secrets only; Compose or the application
  assembles derived values.
- The application service owns PostgreSQL schema, migrations, repositories,
  and transaction boundaries. Hermes does not own schema or write directly to
  Application DB.
- The initial Alembic revision is technical-only and creates no domain tables.
- Applied migration head: `20260709_0001 (head)`.

## Commands

Verified commands:

```text
scripts/dev.sh up
scripts/dev.sh migrate
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh check
docker compose ps
docker compose config --services
docker compose config --images
docker compose config --volumes
find . -iname 'Dockerfile*' -print
git diff --check
```

`docker compose build app` is architecturally allowed for the application
image and expected when dependencies change, but the tool approval layer
rejected that command during this run
because it applies the older Hermes-specific build restriction too broadly.
The checked Compose layout still keeps the restriction where it belongs:
Hermes has no build context, while the application service owns
`Dockerfile.app`.

## Checks

Passing checks:

```text
scripts/dev.sh test      -> 22 passed
scripts/dev.sh lint      -> All checks passed
scripts/dev.sh typecheck -> Success: no issues found in 21 source files
scripts/dev.sh smoke     -> compose, tests, app health, DB, HTTP, migrations ok
scripts/dev.sh check     -> format, lint, typecheck, tests, smoke ok
git diff --check         -> ok
secret scan              -> ok outside test fixtures
```

Smoke coverage:

- Compose services, images, and named volumes are present.
- Hermes service is checked for absence of `build:`.
- `Dockerfile.app` is the only Dockerfile.
- Stage 0 probe plugin is not mounted or enabled in the default runtime.
- PostgreSQL readiness is checked with `pg_isready`.
- Application health/readiness logic is checked.
- HTTP `/healthz` and `/readyz` are checked. Target `/readyz` scope includes
  app, PostgreSQL, migration state, and Hermes for the full local system path.
- Alembic migration status reaches the baseline head.

## Secret handling

- `.env` was not opened.
- `.env.example` contains placeholders only.
- `.dockerignore` excludes local secret-bearing files from the app build
  context.
- No secrets were copied into the report.

## Known limits

- M1 contains no profile, menu, recipe, shopping list, confirmation, Telegram
  UX, or production business workflow.
- Domain Core contracts are not implemented in M1.
- The app service uses read-only bind mounts for project-owned app files in
  local Compose checks so test/lint/typecheck see host edits immediately.
- The current M1 app image carries dev/check dependencies and test files for
  reproducible local checks. Splitting runtime and development/check images is
  deferred to the next stage planning.
- Full destructive runtime reset with volume deletion is documented but was not
  executed in this run because it deletes named volumes, can remove Hermes
  Codex authorization state, and needs explicit operator approval. Treat
  `docker compose down -v` as a release/reproducibility drill or emergency
  reset.
- `git add --dry-run .` was blocked in this Codex sandbox because `.git` is
  read-only: `Unable to create .../.git/index.lock`. The operator should run
  it outside the sandbox before commit.

## Gate M1 result

Gate M1 is functionally satisfied for the non-destructive path:

- PostgreSQL starts.
- Empty application starts.
- Migrations apply.
- Tests, lint, typecheck, and smoke checks pass.
- Health/readiness responses work.
- Runtime deletion and recreation path is documented.

The destructive volume deletion proof remains operator-gated.

## Reflection

- Hidden manual steps: `.env` must exist with local values; this is documented
  and intentionally not committed.
- Versions are pinned for Python image, PostgreSQL image, Hermes image, and
  Python dependencies.
- Logs and command failures were clear enough to diagnose missing files in the
  app image, formatting drift, and type issues.
- No M2+ business logic entered the walking skeleton.
- Hermes runtime state and application PostgreSQL state remain separate.
