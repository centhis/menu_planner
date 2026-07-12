# M8 Hermes runtime API discovery

Date: 2026-07-12

## Scope

This note records fresh local evidence for Stage 9 step 3 before implementing
Menu Planner Hermes plugin code.

The inspection used the ready-made Hermes image only. It did not install
packages, copy code into a container, edit running container files, build a
custom Hermes image, or change Docker daemon settings.

## Runtime identity

`docker compose ps` showed the local `hermes` service running from:

- image: `nousresearch/hermes-agent:v2026.6.19`;
- published ports: `8642` and `9119`;
- container command as reported by Compose: `"/init /opt/hermes/d..."`.

`docker image inspect nousresearch/hermes-agent:v2026.6.19` showed:

- image digest: `sha256:9f367c7756ef087661a361536a89f438d57a122b958dc23d82d456b1433e6e9e`;
- source revision label: `2bd1977d8fad185c9b4be47884f7e87f1add0ce3`;
- created: `2026-06-19T19:47:25.439974023Z`;
- entrypoint: `["/init", "/opt/hermes/docker/main-wrapper.sh"]`;
- workdir: `/opt/hermes`;
- relevant image env defaults: `HERMES_HOME=/opt/data`,
  `HERMES_WRITE_SAFE_ROOT=/opt/data`, `HERMES_DISABLE_LAZY_INSTALLS=1`.

`hermes --version` inside a one-shot container returned:

- `Hermes Agent v0.17.0 (2026.6.19)`;
- upstream revision: `2bd1977d`;
- project path: `/opt/hermes`;
- Python: `3.13.5`;
- OpenAI SDK: `2.24.0`.

## Compose and managed config

The repository Compose service mounts:

- `hermes-data:/opt/data`;
- `scripts/hermes-codex-start.sh` to
  `/opt/menu-planner/hermes-codex-start.sh` as read-only;
- `config/hermes-managed-config.yaml` to `/etc/hermes/config.yaml` as
  read-only.

The managed config currently enables only the dashboard auth plugin:

```yaml
model:
  provider: openai-codex
  default: gpt-5.4-mini

plugins:
  enabled:
    - dashboard_auth/basic
```

Implication for M8: the Menu Planner plugin must be enabled explicitly through
managed config or another reproducible host-file configuration path. Enabling a
plugin by mutable container state is not acceptable.

## CLI surfaces

Relevant CLI help exists in the installed image:

- `hermes plugins --help`: `install`, `update`, `remove`, `list`, `enable`,
  `disable`;
- `hermes tools --help`: `list`, `disable`, `enable`, `post-setup`;
- `hermes skills --help`: `browse`, `search`, `install`, `inspect`, `list`,
  `check`, `update`, `audit`, `uninstall`, `snapshot`, `config`, and related
  maintenance commands;
- `hermes config --help`: `show`, `edit`, `set`, `path`, `env-path`, `check`,
  `migrate`;
- `hermes gateway --help`: `run`, `start`, `stop`, `restart`, `status`,
  `install`, `uninstall`, `list`, `setup`, `migrate-legacy`, `enroll`.

`hermes tools --help` also documents tool naming:

- built-in toolsets use plain names;
- MCP tools use `server:tool`.

## Plugin discovery and manifest

The installed `/opt/hermes/hermes_cli/plugins.py` documents and implements:

- bundled plugin discovery;
- user plugins under `~/.hermes/plugins/<name>`;
- project plugins under `./.hermes/plugins/<name>`, gated by
  `HERMES_ENABLE_PROJECT_PLUGINS`;
- Python entrypoints in group `hermes_agent.plugins`.

A directory plugin needs:

- `plugin.yaml`;
- `__init__.py` with a `register(ctx)` function.

The manifest object includes:

- `name`;
- `version`;
- `description`;
- `author`;
- `requires_env`;
- `provides_tools`;
- `provides_hooks`;
- `source`;
- `path`;
- `kind`;
- `key`.

Observed valid plugin kinds include:

- `standalone`;
- `backend`;
- `exclusive`;
- `platform`;
- `model-provider`.

## Tool registration and return contract

`PluginContext.register_tool(...)` has the installed signature:

```python
register_tool(
    name,
    toolset,
    schema,
    handler,
    check_fn=None,
    requires_env=None,
    is_async=False,
    description="",
    emoji="",
    override=False,
)
```

The actual registry lives at `/opt/hermes/tools/registry.py`, not at the older
`/opt/hermes/hermes_cli/tools/registry.py` path.

`ToolEntry` additionally supports:

- `max_result_size_chars`;
- `dynamic_schema_overrides`.

The registry exposes tools to the model as OpenAI function tool definitions.
The installed dispatch path expects handlers to return JSON strings. The
bundled Spotify plugin confirms this pattern:

```python
def _handle_spotify_playback(args: dict, **kw) -> str:
    ...
```

It returns values through registry helpers:

- `tool_result(data=None, **kwargs)`;
- `tool_error(message, **extra)`.

Implication for M8: Menu Planner tool handlers should return structured JSON
strings via the registry helper convention, keep schemas strict, and avoid
returning raw Python objects.

## Hooks

The installed `VALID_HOOKS` includes:

- `pre_tool_call`;
- `post_tool_call`;
- `transform_terminal_output`;
- `transform_tool_result`;
- `transform_llm_output`;
- `pre_llm_call`;
- `post_llm_call`;
- `pre_api_request`;
- `post_api_request`;
- `api_request_error`;
- `on_session_start`;
- `on_session_end`;
- `on_session_finalize`;
- `on_session_reset`;
- `subagent_start`;
- `subagent_stop`;
- `pre_gateway_dispatch`;
- `pre_approval_request`;
- `post_approval_response`.

`pre_gateway_dispatch` is fired for user-originated gateway messages before
normal dispatch and before gateway auth handling. Hook kwargs are:

- `event`;
- `gateway`;
- `session_store`.

Recognized return values are:

- `{"action": "skip", "reason": "..."}`: drop the message because the plugin
  handled it;
- `{"action": "rewrite", "text": "..."}`: replace `event.text` and continue;
- `{"action": "allow"}` or `None`: continue normally.

`pre_tool_call` can block execution by returning:

```json
{"action": "block", "message": "..."}
```

Hook kwargs include:

- `tool_name`;
- `args`;
- `task_id`;
- `session_id`;
- `tool_call_id`;
- `turn_id`;
- `api_request_id`;
- `middleware_trace`.

The model tool path documents a single-fire contract: `pre_tool_call` fires
exactly once per tool execution unless the caller has explicitly already
checked it. If blocked, the tool result becomes `{"error": block_message}` and
`post_tool_call` is emitted with `status="blocked"` and
`error_type="plugin_block"`.

`pre_approval_request` and `post_approval_response` are observers. Their return
values are ignored; blocking belongs in `pre_tool_call`.

## Runtime skills

`PluginContext.register_skill(name, path, description="")` registers a
read-only skill provided by the plugin.

The installed source says plugin skills are resolved through explicit
`skill_view` as:

```text
<plugin_name>:<skill_name>
```

They do not enter the flat `~/.hermes/skills` directory and are not listed in
the system prompt index automatically.

Bundled skills are present under `/opt/hermes/skills`, and several bundled
plugins also include `SKILL.md` files.

Implication for M8: a Menu Planner runtime skill can be packaged with the
plugin, but tests must verify how the target agent/session loads it. It should
not be assumed to affect the prompt without explicit loading or configuration.

## Model provider and fake/local test options

The image includes `/opt/hermes/plugins/model-providers/README.md`.

Provider profiles are self-contained plugins under:

```text
plugins/model-providers/<provider>/
```

Each provider profile has `__init__.py` and `plugin.yaml`; discovery also scans
`$HERMES_HOME/plugins/model-providers/`. A custom provider profile calls
`providers.register_provider(profile)`.

No deterministic fake model provider suitable for M8 tests was identified in
the inspected CLI help or model-provider README. This remains an open M8
implementation question. If Hermes integration tests need deterministic model
behavior, the project still needs to choose between:

- a project-owned fake provider profile mounted through host files;
- a fake model boundary outside Hermes;
- a narrower Hermes test that exercises plugin tools/hooks without invoking a
  real model.

## Open items after discovery

The following details are still intentionally unresolved:

- exact host file layout for the Menu Planner plugin package;
- exact managed config entries needed to enable only the intended user
  toolsets;
- whether project plugins via `./.hermes/plugins` are preferable to
  `$HERMES_HOME/plugins` for this Compose layout;
- deterministic fake model/provider strategy for end-to-end Hermes tests;
- the bounded non-Telegram workflow command used as the first M8 smoke.

## Commands run

- `docker compose ps`
- `docker image inspect nousresearch/hermes-agent:v2026.6.19`
- `docker run --rm --entrypoint /opt/hermes/bin/hermes
  nousresearch/hermes-agent:v2026.6.19 --version`
- `docker run --rm --entrypoint /opt/hermes/bin/hermes
  nousresearch/hermes-agent:v2026.6.19 plugins --help`
- `docker run --rm --entrypoint /opt/hermes/bin/hermes
  nousresearch/hermes-agent:v2026.6.19 tools --help`
- `docker run --rm --entrypoint /opt/hermes/bin/hermes
  nousresearch/hermes-agent:v2026.6.19 skills --help`
- `docker run --rm --entrypoint /opt/hermes/bin/hermes
  nousresearch/hermes-agent:v2026.6.19 config --help`
- `docker run --rm --entrypoint /opt/hermes/bin/hermes
  nousresearch/hermes-agent:v2026.6.19 gateway --help`
- `docker run --rm --entrypoint sed
  nousresearch/hermes-agent:v2026.6.19 -n ... /opt/hermes/hermes_cli/plugins.py`
- `docker run --rm --entrypoint sed
  nousresearch/hermes-agent:v2026.6.19 -n ... /opt/hermes/tools/registry.py`
- `docker run --rm --entrypoint sed
  nousresearch/hermes-agent:v2026.6.19 -n ... /opt/hermes/model_tools.py`
- `docker run --rm --entrypoint sed
  nousresearch/hermes-agent:v2026.6.19 -n ...
  /opt/hermes/gateway/run.py`
- `docker run --rm --entrypoint find
  nousresearch/hermes-agent:v2026.6.19 /opt/hermes/plugins ...`
- `docker run --rm --entrypoint sed
  nousresearch/hermes-agent:v2026.6.19 -n ...
  /opt/hermes/plugins/spotify/__init__.py`
- `docker run --rm --entrypoint sed
  nousresearch/hermes-agent:v2026.6.19 -n ...
  /opt/hermes/plugins/spotify/tools.py`
- `docker run --rm --entrypoint sed
  nousresearch/hermes-agent:v2026.6.19 -n ...
  /opt/hermes/plugins/model-providers/README.md`

One attempted read of the old registry path failed with:

```text
sed: can't read /opt/hermes/hermes_cli/tools/registry.py: No such file or directory
```

The corrected current path is `/opt/hermes/tools/registry.py`.
