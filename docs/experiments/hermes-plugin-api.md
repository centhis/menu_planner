# Hermes plugin API

Date: 2026-07-08

Purpose: close the research half of Stage 0 step 20 by recording the observed
plugin API of the ready-made Hermes image before creating a probe plugin.

Image: `nousresearch/hermes-agent:v2026.6.19`

Hermes version: `Hermes Agent v0.17.0 (2026.6.19) · upstream 2bd1977d`

## Investigation Commands

Read-only commands used:

```bash
docker run --rm --entrypoint sh nousresearch/hermes-agent:v2026.6.19 -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes plugins --help'

docker run --rm --entrypoint sh nousresearch/hermes-agent:v2026.6.19 -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes plugins list --help'

docker run --rm --entrypoint sh nousresearch/hermes-agent:v2026.6.19 -lc \
  'grep/sed read-only snippets from /opt/hermes/hermes_cli/plugins.py'
```

No Dockerfile, package installation, `docker cp`, or container mutation was
used.

## Findings

### 1. Plugin Search Paths

Source evidence: `/opt/hermes/hermes_cli/plugins.py`.

Observed discovery sources:

1. Bundled plugins: `<repo>/plugins`, resolved in this image as
   `/opt/hermes/plugins`.
2. User plugins: `get_hermes_home() / "plugins"`, which is `/opt/data/plugins`
   in this Docker deployment.
3. Project plugins: `Path.cwd() / ".hermes" / "plugins"`, only when
   `HERMES_ENABLE_PROJECT_PLUGINS` is enabled.
4. Python entry-point plugins under the `hermes_agent.plugins` group.

For this project, the Stage 0 probe plugin should use the observed user-plugin
path and be mounted read-only at:

```text
/opt/data/plugins/menu-planner-probe
```

### 2. Manifest Format

Directory plugins require:

```text
plugin.yaml
__init__.py
```

Source evidence: `/opt/hermes/hermes_cli/plugins.py` says each directory plugin
must contain a manifest and an `__init__.py` with `register(ctx)`.

Observed manifest fields parsed into `PluginManifest`:

```text
name
version
description
author
requires_env
provides_tools
provides_hooks
kind
```

Valid `kind` values:

```text
standalone
backend
exclusive
platform
model-provider
```

The probe plugin should be `kind: standalone`.

### 3. Entry Point

Directory plugin entry point:

```python
def register(ctx) -> None:
    ...
```

Source evidence: `PluginManager._load_plugin()` imports the directory module
and calls `register(ctx)` when present.

### 4. Tool Registration

Source evidence: `PluginContext.register_tool()` in
`/opt/hermes/hermes_cli/plugins.py`.

Observed signature:

```python
ctx.register_tool(
    name: str,
    toolset: str,
    schema: dict,
    handler: Callable,
    check_fn: Callable | None = None,
    requires_env: list | None = None,
    is_async: bool = False,
    description: str = "",
    emoji: str = "",
    override: bool = False,
)
```

It delegates to `tools.registry.register()`.

`tools.registry.dispatch()` calls handlers as:

```python
handler(args, **kwargs)
```

The handler return type is expected to be a string. Existing tools return JSON
strings for structured results, and dispatch wraps exceptions as JSON errors.

### 5. Hook Registration

Source evidence: `PluginContext.register_hook()` and `VALID_HOOKS` in
`/opt/hermes/hermes_cli/plugins.py`.

Observed hook registration:

```python
ctx.register_hook("pre_tool_call", callback)
```

Observed valid hooks include:

```text
pre_tool_call
post_tool_call
transform_terminal_output
transform_tool_result
transform_llm_output
pre_llm_call
post_llm_call
pre_api_request
post_api_request
api_request_error
on_session_start
on_session_end
on_session_finalize
on_session_reset
subagent_start
subagent_stop
pre_gateway_dispatch
pre_approval_request
post_approval_response
```

The minimal Stage 0 probe plugin does not need hooks.

### 6. Toolset Assignment

Toolset is assigned by the `toolset` argument to `ctx.register_tool`.

Source evidence:

```python
ctx.register_tool(name=..., toolset="spotify", ...)
```

from the bundled Spotify plugin.

`hermes tools --help` describes toolsets as plain names and MCP tools as
`server:tool` notation. The probe toolset will be:

```text
menu_planner_probe
```

### 7. Explicit Enablement

Hermes v0.17 uses opt-in plugin loading for standalone plugins.

Source evidence:

```text
Everything else (standalone, user-installed backends, entry-point plugins) is
opt-in via plugins.enabled.
```

The probe plugin must be listed in `plugins.enabled` before it loads. In this
repository that is done through the read-only managed config bind mount:

```text
config/hermes-managed-config.yaml -> /etc/hermes/config.yaml
```

### 8. Restart / Recreate

Plugin discovery happens in process. After adding a host-mounted plugin or
changing the managed config, the Hermes container must be restarted or
recreated for the normal service processes to load the new plugin.

Stage 0 uses:

```bash
docker compose up -d --force-recreate hermes
```

### 9. Available Dependencies

Read-only check with the image venv showed:

```text
yaml yes
pydantic yes
fastapi yes
click yes
jsonschema yes
requests yes
httpx yes
typer no
```

The probe plugin uses only Python stdlib `json`.

### 10. Correlation / Session Identifiers

Source evidence from bundled plugins shows hook callbacks may receive metadata
such as:

```text
session_id
task_id
turn_id
platform
parent_session_id
parent_turn_id
child_session_id
```

Tool handlers receive `args` plus arbitrary `**kwargs` from dispatch. The
minimal probe plugin will not depend on Hermes internal IDs; it accepts a
caller-supplied `request_id` and returns it as `operation_id`.

## Probe Plugin Contract

The Stage 0 probe plugin should:

- live at `plugins/menu-planner-probe` on the host;
- be mounted read-only to `/opt/data/plugins/menu-planner-probe`;
- declare `name: menu-planner-probe`;
- register one tool named `menu_planner_probe_echo`;
- use toolset `menu_planner_probe`;
- accept string `request_id` and string `payload`;
- return JSON success:

```json
{
  "success": true,
  "operation_id": "request-id",
  "data": {
    "payload": "payload"
  }
}
```

- return JSON validation error instead of raising for invalid input.

## Probe Plugin Verification

Commands run after adding the probe plugin and recreating the Hermes service:

```bash
docker compose config --no-interpolate
docker compose up -d --force-recreate hermes
docker inspect hermes --format '{{range .Mounts}}{{println .Type "|" .Source "|" .Destination "|" .RW}}{{end}}'
docker compose exec -T hermes sh -lc 'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes plugins list --enabled --plain'
docker compose exec -T hermes /opt/hermes/.venv/bin/python -c '... discover_plugins(); registry.dispatch(...) ...'
```

Observed mount evidence:

```text
bind | /home/centhis/menu_planner/plugins/menu-planner-probe | /opt/data/plugins/menu-planner-probe | false
```

Observed enabled plugin evidence:

```text
enabled      user     0.1.0    menu-planner-probe
```

Observed tool registration and dispatch evidence:

```text
tool_entry True menu_planner_probe
success {"data": {"payload": "hello"}, "operation_id": "stage20-success-001", "success": true}
validation {"error": {"code": "validation_error", "message": "payload must be a string"}, "operation_id": "stage20-error-001", "success": false}
```

## Agent-Turn Verification

Follow-up date: 2026-07-08.

After the operator completed `openai-codex` authorization, the probe was also
checked through a real Hermes one-shot agent turn, not only through direct
registry dispatch.

Command:

```bash
docker compose exec -T hermes sh -lc '
  export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH
  hermes --ignore-rules -t menu_planner_probe -z \
    "Call the tool named menu_planner_probe_echo exactly once with request_id stage0-agent-turn-20260708-001 and payload hello-from-agent-turn. Then reply with only the JSON returned by the tool."
'
```

Observed output:

```json
{"data":{"payload":"hello-from-agent-turn"},"operation_id":"stage0-agent-turn-20260708-001","success":true}
```

Result: PASS. Hermes can expose the host-mounted probe tool to the model/tool
loop when the `menu_planner_probe` toolset is selected for the invocation.

The direct hook probe was also repeated with synthetic Telegram metadata. It
confirmed:

- `pre_tool_call` receives `session_id`, `task_id`, `turn_id`,
  `tool_call_id`, `api_request_id`, and `platform`.
- `post_tool_call` receives the same IDs plus the tool result.
- `get_pre_tool_call_block_message()` can return the probe block message.

## Open Questions For Later Capability Tests

- Tool enable/disable behavior for an already-running long-lived agent session
  remains untested. The Stage 0 checks verified CLI-visible toolset toggles and
  a fresh one-shot invocation with `-t menu_planner_probe`.
- Real Telegram user identifiers were not observed in probe tool kwargs. Menu
  Planner domain `operation_id` and `user_id` must remain application-owned.
