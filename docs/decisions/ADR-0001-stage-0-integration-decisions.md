# ADR-0001: Stage 0 integration decisions

Date: 2026-07-08

Status: Accepted

## Context

Stage 0 verified the ready-made Hermes image, Docker Compose launch, read-only
bind mounts, plugin/tool/hook capability, Codex-backed inference, Telegram
Gateway transport, built-in Telegram callbacks, runtime state paths, and
state persistence.

The next step is to move from capability evidence to implementation choices
without inventing untested Hermes APIs or weakening the Domain Core boundary.

## Decisions

### 1. Hermes to Application integration

Use an HTTP API boundary between Hermes and the Menu Planner application:

- Hermes plugin/tools act as an adapter to the application HTTP API;
- the application service owns use cases, validation, workflows, persistence,
  and commits;
- keep Domain Core independent of Hermes and Telegram imports.

This keeps Hermes as dialog/runtime infrastructure and keeps application
architecture clean. The cost is one explicit service boundary, which is
acceptable for the project.

### 2. Model provider and local model scope

Defer local models to a separate later stage.

For the immediate post-Stage-0 work, use the verified cloud-capable Hermes
provider path for capability and integration work. The passing Stage 0
`openai-codex` smoke test does not by itself select a production model or
final provider matrix.

### 3. Hermes Dashboard authentication

Keep the dashboard available for development and operations, but treat current
basic auth as a temporary Stage 0/dev mechanism.

Before production exposure, replace dashboard authentication with a more
production-grade option such as a stronger dashboard auth provider, OAuth,
reverse proxy auth, or another explicitly selected mechanism.

### 4. Telegram confirmations

Use Hermes built-in Telegram slash confirmation callbacks, the `sc:*` flow, as
the preferred confirmation mechanism for Menu Planner.

Menu Planner confirmation IDs remain application-owned domain objects. The
adapter must map the Hermes callback flow to Domain Core confirmation checks
rather than letting Telegram callback data commit state directly.

### 5. Telegram user toolset

Use a minimal user toolset for the Telegram user workflow:

```text
menu_planner_*
```

Do not expose these broad built-in toolsets to the normal Menu Planner
Telegram user workflow:

```text
terminal
file
browser
code_execution
```

Administrative and diagnostic capabilities must stay outside the ordinary
user path.

### 6. Project code and configuration mounts

Use read-only host bind mounts for project-owned Hermes inputs, following the
Stage 0 probe pattern.

This applies to:

- production Menu Planner Plugin source;
- project Hermes skills, if used;
- managed Hermes configuration;
- adapter source mounted into Hermes, if a Menu Planner plugin is used.

Mutable Hermes runtime state remains in named volumes or another explicit
runtime storage mechanism, not in project source mounts.

### 7. Application persistence

Use PostgreSQL / an application database for Menu Planner application state
from the walking skeleton onward.

The application service owns PostgreSQL schema, migrations, repositories, and
the transaction boundary. Hermes must not apply migrations, write directly to
the application database, or rely on physical table layout.

Hermes runtime state remains separate from Menu Planner confirmed business
state. Confirmed domain data must not exist only in Hermes memory, sessions,
or other Hermes runtime files.

### 8. Container build boundary

Hermes must run only from the ready-made Docker image. Building or mutating a
Hermes image remains forbidden.

The application image is project-owned. `docker compose build app` is allowed
and expected when application dependencies or image contents change.

## Consequences

- M1 should include PostgreSQL/application DB setup instead of a long-lived
  file-only domain store.
- The production plugin should be a thin adapter from Hermes tools/hooks to
  the application HTTP API.
- The Telegram platform toolset must be restricted before any real user
  workflow is exposed.
- A follow-up confirmation spike should prove the exact `sc:*` callback
  round-trip, including user ID, chat ID, message ID, thread ID if present, and
  application `confirmation_id` mapping.
- A later provider/model decision should pin the cloud model matrix and define
  when local-model readiness work begins.

## Not Decided Here

- Exact production cloud provider and model IDs.
- Exact production-grade dashboard auth provider.
- Exact PostgreSQL schema, migration tooling, and application language/runtime.
