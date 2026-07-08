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

### 1. Hermes to Domain Core integration

Use a hybrid approach:

- start with an in-process Menu Planner Plugin adapter that calls a local
  Domain Core module;
- keep an explicit adapter boundary so the Domain Core can later move behind a
  separate application service/API if needed;
- keep Domain Core independent of Hermes and Telegram imports.

This preserves early development speed while avoiding a hard dependency on the
Hermes process boundary.

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
- application/domain source mounted into Hermes, if the hybrid in-process
  adapter requires it.

Mutable Hermes runtime state remains in named volumes or another explicit
runtime storage mechanism, not in project source mounts.

### 7. Application persistence

Use PostgreSQL / an application database for Menu Planner application state
from the walking skeleton onward.

Hermes runtime state remains separate from Menu Planner confirmed business
state. Confirmed domain data must not exist only in Hermes memory, sessions,
or other Hermes runtime files.

## Consequences

- M1 should include PostgreSQL/application DB setup instead of a long-lived
  file-only domain store.
- The production plugin should be a thin adapter from Hermes tools/hooks to
  Domain Core contracts.
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
- Whether the hybrid in-process adapter will later be split into a separate
  service.
