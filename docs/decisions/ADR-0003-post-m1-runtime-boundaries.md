# ADR-0003: Post-M1 runtime boundaries

Date: 2026-07-09

Status: Accepted

## Context

Stage 1 added the walking skeleton: application container, PostgreSQL,
migrations, health/readiness checks, tests, lint/typecheck, and smoke checks.

After M1, several runtime boundaries needed to be made explicit before M2
planning starts.

## Decisions

### 1. Container build boundary

Hermes must continue to run only from the ready-made Docker image.

Forbidden:

- Dockerfile for Hermes;
- `docker build` for Hermes;
- `docker compose build hermes`;
- custom Hermes image;
- mutating Hermes container state as a deployment mechanism.

Allowed and expected:

- `Dockerfile.app`;
- `docker compose build app`;
- rebuilding the application image when dependencies or image contents change.

The application image is project-owned because dependencies are installed
there. The Hermes image is not project-owned.

### 2. Hermes to application integration

Hermes integrates with Menu Planner through the application HTTP API.

Hermes plugin/tools are adapter layer only. They must not import Domain Core
directly, own business workflows, or write to Application DB.

### 3. Persistence ownership

Application service owns:

- PostgreSQL schema;
- Alembic migrations;
- repositories;
- transaction boundary;
- confirmed application state commits.

Hermes must not apply migrations, write directly to PostgreSQL, or depend on
physical table layout.

### 4. Runtime reset boundary

`docker compose down -v` is not part of the normal development workflow.

It is allowed only as:

- release/reproducibility drill;
- emergency reset.

It must be run with explicit warning because it deletes named volumes,
including PostgreSQL application state and Hermes runtime state. For this
project, that can also remove Hermes Codex authorization state stored in the
Hermes volume.

### 5. Configuration boundary

`.env` stores primitive values and secrets only.

Derived values such as `DATABASE_URL` are assembled in Compose or by the
application from primitive configuration.

### 6. Readiness boundary

`/healthz` reports application process health.

`/readyz` reports readiness of the full local system path needed for the
product to operate:

- application process;
- PostgreSQL;
- expected migration state;
- Hermes reachability.

Hermes is an external component from the application architecture point of
view, but it is critical for the operating product and therefore belongs in
readiness.

### 7. M2 boundary planning

Exact M2 use-case/API boundaries are intentionally deferred to the planning
work for the next stage.

The next stage must decide the first domain contracts before adding business
entities or production workflows.

The next stage planning must also decide how to split the current M1
all-in-one application image into runtime and development/check images. M1
keeps dev tools and tests in the app image for reproducible checks; a
production runtime image should not carry mypy, pytest, Ruff, or test files
unless an explicit later decision keeps that tradeoff.

## Consequences

- CI and local reproducibility should build the application image when needed.
- Policies and reviewer rules must distinguish `docker compose build app`
  from forbidden Hermes image builds.
- Application readiness checks need to grow from DB-only readiness to
  app + DB + migrations + Hermes.
- Runtime image hardening should separate production runtime dependencies from
  development/check dependencies.
- Domain Core stays isolated from Hermes and Telegram.
