# ADR-0011: Hermes plugin integration strategy

Date: 2026-07-12

Status: Accepted

## Context

Stage 9 / M8 moves from deterministic application slices to a narrow Hermes
plugin boundary. Earlier stages already decided that Hermes is the dialog and
agent runtime, while Menu Planner domain authority remains in the Application
service and Domain Core.

The main M8 risk is mixing several concerns at once:

- plugin API discovery;
- plugin packaging and Docker mounts;
- tool contracts;
- hooks and toolsets;
- runtime skills and prompt behavior;
- model/provider behavior;
- Telegram UX;
- real store integration.

M8 must prove a narrow, reproducible Hermes adapter without turning Hermes
memory, prompts, tools, or user free text into a source of confirmed business
state.

Stage 0 recorded Hermes plugin evidence for
`nousresearch/hermes-agent:v2026.6.19` / Hermes v0.17.0 in
`docs/experiments/hermes-plugin-api.md`. M8 still requires fresh local
inspection before implementing plugin code because the running image, managed
config, plugin API, hook behavior, and toolset behavior are runtime facts, not
assumptions.

## Decision

M8 will build a minimal Hermes plugin integration slice:

```text
Hermes message/runtime context
-> pre-message policy
-> structured intent / clarification
-> restricted toolset
-> pre-tool policy
-> Hermes plugin tool adapter
-> Application HTTP API
-> Application/Domain checks
-> structured tool result
```

M8 does not implement Telegram Alpha, real store integration, production model
rollout, custom Hermes image work, mutable container installs, or broad
administrative tool access.

### Required Hermes runtime evidence before implementation

Before implementing plugin code, M8 must record fresh evidence for the actual
local runtime:

- ready-made Hermes image tag and Hermes version;
- relevant `hermes` CLI help for plugins, tools, hooks, skills, config and
  toolsets;
- plugin discovery paths and manifest format;
- plugin entrypoint signature;
- tool registration signature and handler calling convention;
- valid hook names and hook callback semantics for pre-message and pre-tool
  checks;
- toolset configuration and visibility behavior;
- managed config and bind-mount behavior;
- fake/local provider options usable for deterministic tests, if any.

Evidence must be gathered read-only. It must not print `.env`, `auth.json`,
tokens, credentials, private keys, or runtime secrets.

### Plugin packaging and image boundary

Hermes continues to run only from the ready-made Docker image.

Accepted packaging direction:

- project-owned Hermes plugin source lives on the host under a reproducible
  project path;
- plugin source is mounted read-only into Hermes;
- managed Hermes config is mounted read-only;
- mutable Hermes runtime state remains in named volumes or another explicit
  runtime state location;
- container restart/recreate is allowed after host-file/config changes.

Forbidden target mechanisms:

- Dockerfile for Hermes;
- `docker build` for Hermes;
- `docker compose build hermes`;
- custom Hermes image;
- `docker commit`;
- `docker cp` to install plugin code;
- installing packages inside the Hermes container;
- editing files inside a running Hermes container;
- relying on manual `docker exec` mutations as product state.

If actual Hermes plugin packaging requires a different file layout or
configuration shape, that evidence must be recorded before implementation.

### Adapter boundary

Hermes plugin/tools are adapter layer only.

The plugin must call the Menu Planner Application HTTP API for domain
operations. It must not:

- import Domain Core directly;
- import application repositories or SQL schema internals;
- write Application DB directly;
- apply migrations;
- own transaction boundaries;
- treat Hermes memory as source of truth for profile, menu, recipes, shopping,
  catalog, confirmations, or audit state.

Application service remains owner of validation, workflows, permissions,
version checks, confirmation, idempotency, persistence and commit.

### Tool naming and strict schema policy

M8 tools must be narrow and operation-specific.

Accepted naming policy:

- tool names use a stable `menu_planner_` prefix;
- each tool maps to one bounded domain/application operation;
- no single generic "run command", "execute SQL", "edit file", "browse",
  "terminal", or "admin" tool belongs in the user toolset.

Each tool must define strict input schema with:

- explicit `schema_version`;
- `user_id` or adapter-resolved user identity where applicable;
- operation-specific ids and expected versions;
- bounded enum fields for status/action choices;
- no arbitrary code, SQL, shell command, filesystem path, browser URL, or raw
  prompt payload unless explicitly accepted by a later decision.

Tool schemas are adapter contracts. Application HTTP handlers repeat critical
validation and must reject invalid or stale data even if Hermes policy/hook
logic is bypassed.

### Structured tool result contract

Every tool returns a structured result envelope encoded according to the
actual Hermes handler return convention confirmed in M8 discovery.

The logical envelope must include:

- `schema_version`;
- `ok`;
- operation or tool name;
- correlation id;
- structured `data` on success;
- structured `error` on failure with stable machine code, message, path and
  details;
- no secrets, raw credentials, `.env`, `auth.json`, tokens, private keys, raw
  model hidden prompts, or raw store HTML.

Failures must be machine-readable enough for tests and repair prompts.

### Toolsets by workflow state and role

M8 will split tool access by role and workflow state.

Normal user/agent toolsets may expose only approved Menu Planner tools needed
for the current workflow state. They must not expose:

- terminal;
- arbitrary filesystem;
- arbitrary browser;
- SQL;
- secrets/credential tools;
- model/provider modification tools;
- toolset/skill/plugin modification tools;
- administrative MCP tools.

Administrative/diagnostic capabilities, if present in Hermes, remain outside
the normal Menu Planner user toolset and are tested as unavailable to the user
agent.

### Pre-message hook policy

The pre-message policy hook is defense in depth before intent/tool planning.

It should block or route to safe clarification for:

- disallowed channel or user identity;
- messages attempting admin/toolset/skill/model/plugin modification;
- requests for terminal, filesystem, SQL, raw credential access, arbitrary
  browser use, or direct DB mutation;
- attempts to treat Hermes memory as confirmed application state;
- attempts to bypass confirmation or expected-version checks.

The hook does not replace Application policy or tool handler checks.

### Pre-tool hook policy

The pre-tool policy hook checks the requested tool call against:

- authenticated/allowed user context;
- current workflow state;
- current role/toolset;
- operation class;
- required confirmation/preview/expected version;
- dangerous argument patterns such as shell commands, SQL, filesystem paths,
  raw credentials, or broad admin actions.

The pre-tool hook blocks tools outside the current policy surface. Tool
handlers and the Application service repeat critical checks independently.

### Handler and Application duplicate-check policy

M8 accepts hooks as defense in depth only.

Every state-changing tool handler must:

- call Application HTTP API rather than Domain Core or DB directly;
- pass correlation id and adapter metadata;
- require expected versions where relevant;
- map Application errors to structured tool errors;
- avoid committing state directly;
- avoid trusting Hermes memory for critical facts.

Application services must continue to enforce authorization, workflow state,
version, confirmation, idempotency and domain validation checks.

### Versioned Hermes runtime skills policy

Runtime skills may guide:

- intent interpretation;
- clarification;
- validation error repair;
- preview explanation;
- bounded agentic workflow steps.

Runtime skills must be versioned project artifacts and mounted/configured
reproducibly. They must not be the only place where business rules, security
rules, version checks, confirmation requirements, unit arithmetic, package
calculation, or shopping-list mutation are enforced.

### Application context sourcing

Critical context comes from Application DB/API, not Hermes memory.

Hermes memory may be used only for conversational convenience and non-critical
recall. Before a tool acts, the adapter or Application API must read current
state from the Application boundary and re-check versions/policy.

### Agentic and guided modes

M8 may support both guided and agentic modes, but both modes must use the same
domain commands, tool schemas, structured results and Application checks.

Guided mode may expose fewer tools or require explicit step-by-step user
choices. Agentic mode may sequence allowed tools, but it must not gain extra
authority, hidden admin tools, direct DB writes, or bypass confirmations.

### Fake model/provider integration-test policy

M8 integration tests should use a deterministic fake model/provider or
controlled fake-agent path when possible.

Tests must not require production model credentials, network access, live
providers, real Telegram transport, real store APIs, or secrets. If the actual
Hermes runtime cannot support a fake provider cleanly, the limitation must be
recorded and the test strategy adjusted without selecting a production model
by accident.

### Prompt-injection and admin-tool tests

M8 must test attempts to escalate through prompt text, including attempts to:

- call terminal or shell;
- read files or secrets;
- execute SQL;
- bypass confirmation or expected-version checks;
- modify models, toolsets, skills, plugins or configuration;
- use administrative MCP/tools from a normal user context;
- make Hermes memory override Application DB.

Expected result: normal user agent cannot see or call administrative tools,
and Application/handler checks still reject unsafe requests if hook policy is
bypassed in a test.

### Out of M8

M8 does not implement:

- Telegram Alpha, inline buttons, callbacks, or production Telegram UX;
- real store API, scraper, raw store HTML, live price, or live availability;
- production model/provider rollout;
- local model readiness matrix;
- dashboard production auth hardening;
- final deployment hardening;
- custom Hermes image;
- mutable container install;
- broad admin tools in user toolsets;
- direct DB writes from Hermes;
- business workflows whose only validation lives in Hermes prompts/skills.

## Consequences

- Step 3 must inspect the actual Hermes runtime before implementation.
- Plugin implementation will be constrained to reproducible host files and
  read-only mounts.
- Tool contract work can proceed without Telegram Alpha or real store
  integration.
- Application HTTP API endpoints may need to be added or refined so Hermes can
  remain a thin adapter.
- M8 tests must include both positive workflow behavior and negative
  prompt-injection/admin-tool cases.
- Unresolved runtime/API/fake-model details remain explicit in OQ-009 until
  discovery and implementation evidence resolves them.

