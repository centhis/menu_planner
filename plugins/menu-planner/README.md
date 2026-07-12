# Menu Planner Hermes plugin

This package is the host-side Hermes adapter for M8.

## Boundary

The plugin is not Domain Core and is not an Application service. It must call
the Menu Planner Application HTTP API for all reads, previews, confirmations
and state changes.

Forbidden in this package:

- importing `menu_planner.domain`;
- importing `menu_planner.application`;
- importing `menu_planner.infrastructure`;
- importing `menu_planner.bootstrap`;
- importing database, migration, ORM or SQL client modules;
- reading secrets or local credentials;
- writing directly to the Application database.

## Layout

```text
plugins/menu-planner/
├── README.md
├── __init__.py
├── adapter.py
├── context.py
├── handlers.py
├── modes.py
├── plugin.yaml
├── policy.py
├── results.py
├── runtime_skills.py
├── skills/
├── toolsets.py
└── tools.py
```

`plugin.yaml` and `__init__.py` match the installed Hermes v0.17 plugin
contract. `tools.py` defines the narrow tool catalog and strict schemas.
`results.py` defines the structured tool result envelope. `toolsets.py`
defines workflow-scoped user toolsets. `policy.py` implements the
`pre_gateway_dispatch` message policy hook and `pre_tool_call` tool policy
hook. `handlers.py` registers Hermes tool handlers and repeats critical checks
before calling the Application HTTP API. `context.py` loads authoritative
context from the Application HTTP API. `modes.py` defines agentic and guided
mode contracts over the same tool schemas and Application API commands.
`runtime_skills.py` registers versioned Hermes skills packaged under `skills/`.

## Mount strategy

The target deployment should mount this host directory read-only into Hermes as
a user plugin:

```text
plugins/menu-planner -> /opt/data/plugins/menu-planner:ro
```

`/opt/data` is the image's `HERMES_HOME`, so this matches Hermes user plugin
discovery without enabling broad project plugin discovery through
`HERMES_ENABLE_PROJECT_PLUGINS`.

The plugin must be enabled through managed host config. Mutable container state,
`docker cp`, package installation inside the container and custom Hermes images
are not target solutions.

## Adapter policy

`adapter.py` uses the Python standard library only and sends requests to a
configured Application HTTP base URL.

Every request propagates `X-Correlation-ID`. State-changing calls can also
propagate `Idempotency-Key`.

Errors are mapped into structured objects:

- `application_timeout`;
- `application_unreachable`;
- `application_http_error`;
- `application_invalid_json`;
- `application_request_invalid`.

Tool handlers built in later M8 steps should wrap these adapter results in the
project's structured Hermes tool result contract.

## Result contract

Hermes tool handlers must return JSON strings. `results.py` provides helpers
for stable success and error envelopes.

Success results include:

- `success: true`;
- `operation_id`;
- `correlation_id`;
- optional `entity_id` and `entity_version`;
- `data`;
- `warnings`;
- `next_allowed_actions`.

Error results include:

- `success: false`;
- `operation_id`;
- `correlation_id`;
- `retryable`;
- `errors` with stable `code`, `message` and optional `field`;
- `next_allowed_actions`.

Unexpected exceptions are mapped to `unexpected_tool_error` with a generic
message. Raw exception text must not cross the Hermes tool boundary.

## Tool policy

The M8 catalog includes only narrow Menu Planner operations:

- workflow status read;
- profile preview and confirmed profile commit;
- menu draft generation;
- recipe draft generation;
- one-slot replacement preview;
- shopping list build;
- one shopping checklist item update.

Every input schema is an object with `additionalProperties: false`.

State-changing tools carry an explicit `mutation_policy`:

- `preview_only` for generated drafts/previews that still need application
  policy checks before accepted state changes;
- `requires_confirmation` for confirmed profile commit;
- `direct_update_allowed` for the single checklist item toggle.

No terminal, filesystem, browser, SQL, model, skill, secret or admin tools are
part of this catalog.

## Toolsets

The versioned toolset config fixture is
`fixtures/hermes/menu_planner_toolsets/toolsets.v1.json`.

User-visible toolsets are scoped by workflow state:

- `menu_planner_read_only` exposes workflow status in every user state;
- `menu_planner_profile` exposes profile preview and confirmed profile commit
  in profile states;
- `menu_planner_menu` exposes menu draft generation in ready/menu states;
- `menu_planner_recipe` exposes recipe draft and one-slot replacement preview
  in ready/recipe states;
- `menu_planner_shopping` exposes shopping list build and one checklist item
  update in ready/shopping states.

`menu_planner_admin_dev` is intentionally empty in M8 and is not part of the
user role.

## Pre-message Policy

The plugin registers `pre_gateway_dispatch`. The hook evaluates user-originated
messages before the normal Hermes agent/tool loop.

It blocks messages when:

- the user is unauthenticated or unbound;
- the channel is not in the M8 allowed set;
- the message exceeds `MAX_MESSAGE_CHARS`;
- the rate-limit placeholder is active;
- the workflow state is unknown;
- the message attempts administrative commands or secret/tool/runtime access.

Allowed messages return `{"action": "allow"}`. Blocked messages return
`{"action": "skip"}` with a structured policy result.

## Pre-tool Policy

The plugin registers `pre_tool_call`. The hook blocks tool calls when:

- the tool is unknown or looks administrative;
- the tool is not in the active workflow-state user toolset;
- the tool call user does not match the bound user;
- `correlation_id` is missing;
- required arguments are missing or unexpected arguments are present;
- argument types do not match the strict schema;
- the call attempts secret access;
- a state-changing call omits `idempotency_key`;
- a confirmation-required call omits `confirmation_id`.

Blocked calls return Hermes action `block` with a structured JSON error
message and policy details.

## Handler Boundary

`handlers.py` repeats critical checks even when `pre_tool_call` is bypassed in
tests or by a runtime bug. Each handler:

- looks up the static tool definition;
- reruns `evaluate_pre_tool_policy`;
- refuses unknown workflow states, inactive tools, user mismatch, missing
  correlation id, missing idempotency key and missing confirmation id;
- calls only the Application HTTP API through `adapter.py`;
- maps Application errors into the structured tool result contract.

Handlers do not import Domain Core, repositories, database code or migrations.

## Context Loading

`context.py` fetches current context from the Application HTTP API at the
`/m8/context/users/<user_id>` boundary.

The context payload includes:

- current `workflow_state`;
- allowed tools derived from versioned toolset metadata;
- versioned toolset config;
- confirmed profile, menu, recipes and shopping-list state when returned by the
  Application API;
- an optional bounded `memory_hint`.

Hermes memory is never accepted as critical state. If memory conflicts with
Application API state, Application API state wins. If critical state is missing
from the Application API response, the plugin returns a structured error
instead of inventing it from memory.

## Modes

`modes.py` preserves two runtime modes without changing Domain Core:

- `agentic`: Hermes chooses the next tool from the active `allowed_tools`
  context, but still uses the same strict schemas, handlers, policy hooks and
  Application HTTP API commands.
- `guided`: workflow logic selects the next tool; a local model or fixture only
  fills that tool's structured arguments.

Both modes use the same `ToolDefinition` catalog and the same
`handlers.handle_tool_call` boundary. The deterministic guided fixture is
`fixtures/hermes/menu_planner_modes/guided_fake_workflow.v1.json`.

The provider-free integration command is:

```sh
scripts/dev.sh m8-fake-integration
```

It runs `scripts/m8_fake_model_integration.py` with synthetic inputs, a fixture
client and no production model credentials or external providers.

## Runtime Skills

Runtime skills are versioned assets under `plugins/menu-planner/skills`.

Registered skills:

- `intent-interpretation-v1`;
- `clarification-v1`;
- `menu-generation-v1`;
- `validation-repair-v1`;
- `preview-explanation-v1`.

Each skill points to structured tools/results and states that the Application
HTTP API and Domain validation are authoritative. Skills must not contain
secret values, private data or business rules that bypass schemas, handlers,
hooks, confirmation, idempotency or Application/Domain validation.
