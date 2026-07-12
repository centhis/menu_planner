# M8 Hermes plugin integration report

Date: 2026-07-12

## Goal

M8 proves a narrow Hermes plugin boundary without moving Menu Planner domain
authority into Hermes.

The intended path is:

```text
Hermes message/runtime context
-> pre-message policy
-> restricted toolset
-> pre-tool policy
-> Hermes plugin tool adapter
-> Application HTTP API
-> Application/Domain checks
-> structured tool result
```

M8 stops at this gate. Do not proceed to Telegram Alpha without a separate
user request and a fresh boundary decision.

## Scope

Included in M8:

- fresh Hermes runtime/API discovery for the local ready-made image;
- ADR-0011 for plugin strategy and boundaries;
- host-side Menu Planner Hermes plugin package;
- strict tool catalog and schemas;
- structured success/error tool results;
- workflow-state and role-based toolsets;
- `pre_gateway_dispatch` and `pre_tool_call` policy hooks;
- handler-level repeated checks before Application HTTP API calls;
- Application API context sourcing;
- versioned runtime skills;
- agentic and guided mode contracts over the same command surface;
- provider-free fake integration workflow and transcript;
- prompt-injection, admin-tool, toolset, handler and context tests.

Out of scope:

- Telegram Alpha, inline buttons, callbacks or production Telegram UX;
- real store integration, scrapers, raw store HTML, live prices or availability;
- production model/provider rollout;
- custom Hermes image or mutable container installation;
- direct Hermes writes to Application DB;
- Domain Core imports from Hermes plugin code;
- final deployment hardening and production dashboard auth.

## Hermes Version/API Evidence

Fresh evidence is recorded in
`docs/experiments/m8-hermes-runtime-api-discovery.md`.

Observed local runtime:

- image: `nousresearch/hermes-agent:v2026.6.19`;
- digest: `sha256:9f367c7756ef087661a361536a89f438d57a122b958dc23d82d456b1433e6e9e`;
- Hermes: `v0.17.0 (2026.6.19)`;
- upstream revision: `2bd1977d`;
- Python: `3.13.5`;
- OpenAI SDK: `2.24.0`;
- entrypoint: `["/init", "/opt/hermes/docker/main-wrapper.sh"]`;
- workdir: `/opt/hermes`;
- `HERMES_HOME=/opt/data`.

Relevant API facts:

- directory plugins require `plugin.yaml` plus `__init__.py` with
  `register(ctx)`;
- user plugins are discovered under `~/.hermes/plugins/<name>`;
- project plugins are gated by `HERMES_ENABLE_PROJECT_PLUGINS`;
- `PluginContext.register_tool(...)` accepts name, toolset, schema, handler,
  optional check function, env requirements, async flag, description, emoji and
  override flag;
- handlers return JSON strings;
- `pre_gateway_dispatch` can allow, rewrite or skip user-originated messages;
- `pre_tool_call` can block execution with a structured block action;
- plugin-provided skills can be registered as read-only project assets.

The discovery was read-only and did not install packages, mutate the image,
copy files into a container or print secrets.

## Plugin Packaging Decisions

ADR-0011 accepts a host-owned, reproducible plugin package.

Current package:

```text
plugins/menu-planner/
```

Key files:

- `plugin.yaml`;
- `__init__.py`;
- `adapter.py`;
- `tools.py`;
- `results.py`;
- `toolsets.py`;
- `policy.py`;
- `handlers.py`;
- `context.py`;
- `modes.py`;
- `runtime_skills.py`;
- `skills/*/SKILL.md`.

Target mounting direction:

```text
plugins/menu-planner -> /opt/data/plugins/menu-planner:ro
```

This preserves the ready-made Hermes image boundary and avoids broad project
plugin discovery unless later evidence requires it.

## Tool, Schema, Hook And Toolset Decisions

The M8 tool catalog contains eight narrow Menu Planner operations:

- `menu_planner_get_workflow_status`;
- `menu_planner_preview_profile`;
- `menu_planner_commit_profile`;
- `menu_planner_generate_menu_draft`;
- `menu_planner_generate_recipe_draft`;
- `menu_planner_preview_menu_slot_replacement`;
- `menu_planner_build_shopping_list`;
- `menu_planner_update_shopping_checklist_item`.

Every tool schema is an object with `additionalProperties: false`, explicit
`schema_version`, `user_id` and `correlation_id`. State-changing tools carry
`idempotency_key`; confirmation-required tools carry `confirmation_id`.

Tool results are JSON strings with stable success/error envelopes and
machine-readable error codes. Unexpected exceptions are mapped to
`unexpected_tool_error` without exposing raw exception text.

Toolsets are split by workflow state and role:

- read-only workflow status;
- profile preview/commit;
- menu draft generation;
- recipe draft/replacement preview;
- shopping list build/checklist update;
- empty `menu_planner_admin_dev` placeholder outside the user role.

The user toolsets exclude terminal, arbitrary filesystem, browser, SQL,
secrets, model/provider modification, skill/toolset/plugin modification and
admin MCP surfaces.

Hooks are defense in depth:

- `pre_gateway_dispatch` blocks disallowed users, channels, oversized input,
  unknown workflow state and admin/secret/runtime access attempts;
- `pre_tool_call` blocks unknown/admin tools, tools outside active
  workflow-state toolsets, user mismatch, missing correlation/idempotency/
  confirmation data, unexpected args, dangerous arg patterns and secret access.

Handlers repeat critical checks even if hooks are bypassed.

## Runtime Skills Decisions

Versioned runtime skills live under `plugins/menu-planner/skills`.

Registered M8 skills:

- `intent-interpretation-v1`;
- `clarification-v1`;
- `menu-generation-v1`;
- `validation-repair-v1`;
- `preview-explanation-v1`.

Skills guide local interpretation, clarification, repair and explanation only.
They do not own business rules, confirmation, idempotency, version checks,
shopping arithmetic, security policy or persistence.

## Agentic And Guided Mode Status

Both modes use the same `ToolDefinition` catalog, strict schemas, handlers and
Application HTTP API commands.

- `agentic` mode lets Hermes choose from the active `allowed_tools` context.
- `guided` mode selects the next tool from workflow logic and lets a fixture or
  local model fill structured arguments.

M8 keeps guided mode as the safer default for weak or uncertain models because
it exposes fewer choices per step and makes the next command explicit.

## Fake Model/Provider Status

The deterministic provider-free command is:

```sh
scripts/dev.sh m8-fake-integration
```

It uses:

- fixture input from
  `fixtures/hermes/menu_planner_modes/guided_fake_workflow.v1.json`;
- fake Application API clients;
- no production model credentials;
- no live provider calls;
- no Telegram transport.

The bounded workflow transcript is saved at:

```text
docs/experiments/m8-bounded-hermes-workflow-transcript.json
```

The transcript records:

- `provider: fixture`;
- `credentials_used: false`;
- `telegram_used: false`;
- `direct_db_writes: false`;
- Application context call: `GET /m8/context/users/user_001`;
- tool call: `POST /m8/menu/draft`;
- restricted toolset:
  `menu_planner_get_workflow_status`,
  `menu_planner_generate_menu_draft`.

## Commands Run

Commands run during the final M8 steps:

```sh
scripts/dev.sh m8-fake-integration
python3 -m unittest tests.unit.test_hermes_plugin_adapter
python3 -m py_compile \
  scripts/m8_fake_model_integration.py \
  plugins/menu-planner/__init__.py \
  plugins/menu-planner/adapter.py \
  plugins/menu-planner/context.py \
  plugins/menu-planner/handlers.py \
  plugins/menu-planner/modes.py \
  plugins/menu-planner/tools.py \
  plugins/menu-planner/results.py \
  plugins/menu-planner/toolsets.py \
  plugins/menu-planner/policy.py \
  plugins/menu-planner/runtime_skills.py \
  tests/unit/test_hermes_plugin_adapter.py
git diff --check
```

Additional local sanity checks:

```sh
awk 'length($0) > 88 { print FILENAME ":" FNR ":" length($0) }' \
  scripts/m8_fake_model_integration.py \
  tests/unit/test_hermes_plugin_adapter.py \
  docs/experiments/m8-bounded-hermes-workflow-transcript.json
rg -n "<secret marker regex>" \
  docs/experiments/m8-bounded-hermes-workflow-transcript.json \
  fixtures/hermes \
  scripts/m8_fake_model_integration.py
find plugins/menu-planner scripts tests -type d -name __pycache__ -print
```

## Contract, Security And Integration Metrics

- Unit/contract coverage for the plugin adapter: 46 tests passing.
- Tool schema validation: every tool accepts valid args and rejects invalid
  args through the policy checks.
- Tool result contract: structured success/error fixtures pass.
- Toolset visibility: user role cannot see administrative tools.
- Pre-message policy: blocks admin/runtime/secret attempts and unsafe gateway
  messages.
- Pre-tool policy: blocks inactive tools, unknown/admin tools, user mismatch,
  missing correlation/idempotency/confirmation data and secret access.
- Prompt injection tests: terminal, SQL, arbitrary commit, admin tools and
  memory-as-authority attempts are blocked.
- Handler bypass tests: handlers repeat policy and reject unsafe calls even
  when hooks are bypassed.
- Context sourcing tests: Application API state wins over Hermes memory.
- Domain boundary test: plugin package does not import Domain Core,
  application, infrastructure, bootstrap, DB, migration, ORM or SQL modules.
- Provider-free workflow: one guided fake workflow passes and writes a
  structured transcript without secrets.

## What Was Intentionally Not Implemented

- Telegram Alpha.
- Telegram inline callbacks, buttons or allowlist UX.
- Production model/provider rollout.
- Real store integration, scraper, live catalog, live prices or availability.
- Custom Hermes image.
- Mutable plugin installation inside a running container.
- Direct DB access from Hermes.
- Admin tools in user toolsets.
- Final deployment hardening.

## Gate M8 Result

Gate M8 result: passed with recorded deviations.

The Hermes plugin boundary is implemented and tested as a provider-free,
host-file, Application-API-backed adapter. It is ready as a foundation for a
separate Telegram Alpha planning step, but Telegram Alpha must not start
automatically.

Recorded deviations:

- The bounded workflow is exercised by the provider-free plugin/fake-runner,
  not by a live Telegram transport.
- Full Docker-backed `scripts/dev.sh test`, `scripts/dev.sh lint`,
  `scripts/dev.sh typecheck` and `scripts/dev.sh smoke` were not rerun during
  the report step; targeted plugin tests, integration runner, Python compile
  and `git diff --check` were run instead.

## Gate M8 Checklist

[x] M8 Codex skill exists and was used for implementation tasks.
[x] M8 brief exists and was used for routine tasks.
[x] ADR-0011 or equivalent decision note fixes Hermes plugin strategy.
[x] Actual Hermes version/API behavior was inspected and recorded.
[x] Plugin packaging preserves ready-made image boundary.
[x] No custom Hermes image or mutable container installation was added.
[x] Hermes plugin/tools call Application HTTP API and do not import Domain Core.
[x] Every tool has strict input schema.
[x] Every tool has structured success/error output schema.
[x] Tool results include next allowed actions where relevant.
[x] Toolsets are split by workflow state and role.
[x] User toolset excludes terminal/filesystem/browser/SQL/secrets/admin tools.
[x] Pre-message hook blocks disallowed/admin/oversized inputs.
[x] Pre-tool hook blocks tools outside current toolset/state/policy.
[x] Tool handlers/application services repeat critical checks independently of
    hooks.
[x] User agent cannot see administrative tools.
[x] Prompt injection cannot reach terminal, SQL, arbitrary commit or admin tool.
[x] Memory does not replace Application DB for critical state.
[x] Versioned Hermes runtime skills exist where accepted.
[x] Business rules do not live only in skills/prompts.
[x] Agentic and guided modes use same domain commands and schemas.
[x] Fake model/provider integration test is deterministic and provider-free.
[x] One bounded Hermes workflow passes without Telegram UX.
[x] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[x] No Telegram Alpha, real store integration, production model rollout or
    production deployment hardening added.
[x] `scripts/dev.sh test` passed or deviation recorded.
[x] `scripts/dev.sh lint` passed or deviation recorded.
[x] `scripts/dev.sh typecheck` passed or deviation recorded.
[x] `scripts/dev.sh smoke` passed or deviation recorded.
[x] M8 integration/eval command passed or skipped with reason.
[x] `git diff --check` passed.

Deviation for unchecked full-suite items: not rerun at report time; targeted
M8 plugin tests and integration checks passed.

## Reflection M8

### Какие возможности Hermes реально сократили код?

Hermes gives a useful plugin/tool/hook/skill boundary. The biggest reduction is
not in domain code, but in adapter shape: tools can be registered as a narrow
catalog, pre-message/pre-tool hooks give a natural defense-in-depth layer, and
runtime skills can be packaged as versioned assets instead of hidden prompt
text.

### Где Hermes дублирует application workflow и создает риск?

Toolsets, hooks and skills can easily start looking like a second workflow
engine. The safe split is to let Hermes decide conversation routing and tool
visibility only, while Application/Domain remain authoritative for workflow
state, permissions, validation, confirmation, idempotency and persistence.

### Можно ли еще сузить tools?

Yes. Telegram Alpha should likely expose a smaller guided subset first:
workflow status, menu draft preview and the specific confirmation path needed
for the alpha scenario. Recipe, replacement and shopping-list tools can remain
disabled until their user-facing flows are selected.

### Достаточно ли guided mode для слабой модели?

Guided mode is enough for the first Telegram Alpha because it selects the next
tool from workflow state and asks the model or fixture only for bounded
structured arguments. Agentic mode is useful to keep tested, but it should not
be the default for early user-facing flows.

### Какие решения нужны перед Telegram Alpha?

- Exact Telegram Alpha scenario and allowed user journey.
- Mapping from Telegram user/chat/session metadata to Application `user_id`.
- Confirmation UX: built-in Hermes slash confirmation, Application-owned
  `confirmation_id`, or another explicit round trip.
- Which plugin tools are exposed in the Telegram Alpha user toolset.
- Managed config and read-only mount path for enabling the Menu Planner plugin.
- Failure copy for blocked policy, stale confirmation and Application errors.
- Whether the first Alpha uses guided-only mode.
- Observability policy for transcripts, logs and sanitized error artifacts.

## Remaining Assumptions

- The target plugin mount remains `/opt/data/plugins/menu-planner:ro` unless
  later Hermes evidence selects a different reproducible path.
- Managed config will explicitly enable only the intended Menu Planner plugin
  and not expose broad project plugin discovery by default.
- The provider-free fake runner is the M8 integration gate; live Telegram
  transport is a later stage.
- Application HTTP API endpoints used by the adapter remain the boundary for
  real domain operations.
- No production model/provider is selected by M8.

## Decisions Before Telegram Alpha

Do not start Telegram Alpha without a separate user request.

Before Telegram Alpha, decide and record:

- Telegram identity mapping;
- confirmation callback/command strategy;
- exact alpha toolset;
- guided vs agentic default;
- plugin mount and managed config update;
- transcript/log retention and redaction;
- user-facing error/clarification copy.
