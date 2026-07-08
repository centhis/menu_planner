# Hermes capability spike

Date: 2026-07-08

Purpose: final Stage 0 Hermes capability report. This document summarizes the
container baseline, mount map, plugin probe, runtime state, and reproducibility
checks. Detailed command evidence remains in the linked experiment reports.

## Environment

- Ubuntu: `Ubuntu 24.04.4 LTS`
- architecture: `x86_64`
- Docker: `Docker version 29.6.1, build 8900f1d`
- Docker Compose: `Docker Compose version v5.2.0`
- Hermes image: `nousresearch/hermes-agent:v2026.6.19`
- Hermes digest:
  `nousresearch/hermes-agent@sha256:9f367c7756ef087661a361536a89f438d57a122b958dc23d82d456b1433e6e9e`
- Hermes version:
  `Hermes Agent v0.17.0 (2026.6.19) · upstream 2bd1977d`
- Codex version: `codex-cli 0.142.5`

Primary evidence:

- `docs/experiments/codex-baseline.md`
- `docs/experiments/hermes-container-baseline.md`
- `docs/experiments/hermes-reproducibility.md`

## Deployment constraints

- ready image only: PASS. Hermes uses `nousresearch/hermes-agent:v2026.6.19`.
- Dockerfile absent: PASS. `find . -iname 'Dockerfile*' -print` produced no
  output.
- build absent: PASS. `rg -n '^\s*build\s*:' compose.yaml` found no matches.
- project files mounted: PASS. Managed config, startup wrapper, and probe
  plugin are bind mounted read-only.
- runtime state externalized: PASS. Hermes mutable state is rooted in the
  Docker named volume `menu_planner_hermes-data` mounted at `/opt/data`.

No Dockerfile, `docker build`, `docker compose build`, `docker cp`, package
installation, `docker commit`, or manual in-container edits were used.

## Capability matrix

| Capability | Result | Evidence | Decision |
|---|---|---|---|
| Plugin discovery | PASS | `hermes plugins list --enabled --plain` shows `menu-planner-probe` as enabled user plugin | Host-mounted project plugins can be discovered through `/opt/data/plugins/<name>` |
| Plugin enablement | PASS / explicit | Hermes source says standalone/user plugins are opt-in through `plugins.enabled`; managed config enables `menu-planner-probe` | Keep project-owned plugin enablement in read-only managed config |
| Tool registration | PASS | `registry.get_entry("menu_planner_probe_echo")` returned a tool in `menu_planner_probe` | Hermes plugin tools are viable integration points |
| Structured arguments | PASS | `registry.dispatch()` received `request_id` and `payload` exactly | Tool handlers may accept structured JSON-like args |
| Structured success | PASS | Probe returned `{"success": true, "operation_id": "...", "data": ...}` | Domain tools should return structured JSON strings |
| Structured errors | PASS | Probe returned `{"success": false, "error": {"code": "validation_error", ...}}` without raising | Validation errors should be explicit machine-readable tool results |
| Pre-tool hook | PASS | `invoke_hook("pre_tool_call", ...)` returned probe payload | Hooks can observe tool calls |
| Post-tool hook | PASS | `invoke_hook("post_tool_call", ...)` returned probe payload with `result_seen=true` | Hooks can observe tool results |
| Hook blocking | PASS | `get_pre_tool_call_block_message()` returned probe block message | Hooks can enforce policy, but critical domain checks still belong in handlers |
| Agent-turn tool call | PASS | `hermes --ignore-rules -t menu_planner_probe -z ...` returned the probe tool JSON with `operation_id=stage0-agent-turn-20260708-001` | A model/tool loop can call a host-mounted project plugin tool |
| Codex-backed inference | PASS | `hermes auth status openai-codex` showed `logged in`; `hermes --ignore-rules -z "Reply exactly: stage0-model-ok"` returned `stage0-model-ok` | Codex auth works for the current configured model; provider/model matrix remains a later decision |
| Toolsets | PASS / unsafe default | `hermes tools list --platform telegram` shows `menu_planner_probe` enabled, but also built-in `terminal`, `file`, `browser`, and `code_execution` enabled | Toolset mechanics work; the Telegram user platform must be restricted before production use |
| Sessions | PARTIAL | `/opt/data/state.db` and `/opt/data/sessions` exist in named volume | Runtime state is externalized; real agent-session behavior needs later app tests |
| Correlation IDs | PARTIAL | Hook kwargs carried `session_id`, `task_id`, `turn_id`, `tool_call_id`, `api_request_id`, `platform`; no `user_id` observed | Domain `operation_id` must be application-owned |
| Hermes skills | PASS / partial | `hermes skills list --source builtin --enabled-only` lists bundled skills; source uses `/opt/data/skills` and `SKILL.md` | Skills are available; project skill mount is not selected yet |
| Telegram Gateway | PASS / transport | `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS` are set in the container; `hermes send --quiet --to telegram:<allowed-user>` returned `telegram_send=pass` | Telegram transport is configured; business UX still needs a Menu Planner-specific flow |
| Telegram callbacks | PARTIAL | Source shows `CallbackQueryHandler`, `InlineKeyboardButton`, built-in `sc:*` slash-confirm callbacks, `cl:*` clarify callbacks, and authorization checks using `query.from_user.id`; no custom plugin-owned callback namespace was found | Built-in Hermes callback flows are available as candidates; Menu Planner confirmation mapping is still an architecture decision |
| State persistence | PASS | Runtime marker in `/opt/data/config.yaml` survived `docker compose down` and `docker compose up -d` | Preserve `menu_planner_hermes-data` for Hermes runtime continuity |

Detailed evidence:

- `docs/experiments/hermes-plugin-api.md`
- `docs/experiments/hermes-runtime-state.md`
- `docs/experiments/hermes-reproducibility.md`

## Mount map

| Purpose | Host | Container | Mode |
|---|---|---|---|
| Hermes runtime state | Docker volume `menu_planner_hermes-data` | `/opt/data` | `rw` |
| Managed Hermes config | `./config/hermes-managed-config.yaml` | `/etc/hermes/config.yaml` | `ro` |
| Startup wrapper | `./scripts/hermes-codex-start.sh` | `/opt/menu-planner/hermes-codex-start.sh` | `ro` |
| Probe plugin | `./plugins/menu-planner-probe` | `/opt/data/plugins/menu-planner-probe` | `ro` |
| Production Menu Planner plugin | not selected yet | not selected yet | future `ro` |
| Project Hermes skills | not selected yet | not selected yet | future `ro` |
| Domain source | not mounted | not selected yet | future decision |

Runtime paths observed under `/opt/data`:

- `/opt/data/config.yaml`
- `/opt/data/.env` (secret-capable path; missing in observed container)
- `/opt/data/state.db`
- `/opt/data/sessions`
- `/opt/data/logs`
- `/opt/data/memories`
- `/opt/data/skills`
- `/opt/data/plugins`

Detailed evidence: `docs/experiments/hermes-mount-map.md`.

## Missing capabilities

- Live Telegram callback tap was not performed by this run. Source evidence
  confirms built-in callback handlers, but no operator click was round-tripped
  through a Menu Planner confirmation.
- Existing already-running agent-session behavior after toolset toggles is
  unknown.
- The current Telegram platform default toolsets include broad built-in tools
  such as terminal, file, browser, and code execution. This is acceptable only
  as a Stage 0 runtime observation, not as a production user toolset.
- Project production plugin, project skills, and domain source mount targets
  are not selected yet.
- Provider/model selection beyond the current `openai-codex` +
  `gpt-5.4-mini` smoke test is not decided. Older logs showed unsupported
  model errors for other model IDs when used through ChatGPT-backed Codex.

## Required adapters

- Menu Planner production plugin: needed to expose application tools while
  delegating business rules to the domain core.
- Domain operation adapter: needed to convert Hermes tool args into
  application-owned operation IDs, validation results, confirmations, and
  idempotent commits.
- Telegram confirmation adapter: needed to decide whether Menu Planner uses
  Hermes built-in `slash_confirm` / `clarify` callback flows, text
  confirmations, or a custom adapter.
- Provider selection adapter/config: needed to switch between Codex-backed
  OpenAI access, direct OpenAI API keys, Anthropic, and future local providers.

## Documentation conflicts

- Hermes v0.17 runtime behavior showed standalone/user plugins are opt-in via
  `plugins.enabled`; env vars alone are insufficient for bundled
  `dashboard_auth/basic`.
- Binding dashboard to `0.0.0.0` requires a registered dashboard auth provider.
  Bypassing dashboard or the image entrypoint was rejected as a target
  solution.
- Telegram platform setup, outbound bot delivery, and built-in callback source
  support are now separately recorded. A Menu Planner-specific callback
  round-trip is still a later test.

## Security observations

- Real `.env`, `auth.json`, token, and credential contents were not opened or
  copied into reports.
- Dashboard exposed on `0.0.0.0` is gated by `dashboard_auth/basic`; local
  `.env` must provide username, password, and a session secret of at least
  16 bytes.
- `docker compose down -v` was not run because it deletes named volumes.
- `/opt/data/.env` is a secret-capable path and must be handled as a secret if
  it appears.
- Do not mount `~/.codex` or host `auth.json` into Hermes without a separate
  explicit capability-spike decision.
- Current Telegram platform toolsets include broad built-ins (`terminal`,
  `file`, `browser`, `code_execution`). Before exposing Menu Planner to a
  normal user workflow, configure a minimal platform/toolset boundary and
  re-run the toolset check.

## Open questions

- OQ-001: Hermes OpenAI access through Codex authorization and provider/model
  matrix.
- OQ-002: Dashboard role and long-term dashboard auth provider.
- OQ-003: Telegram inline callback support and Menu Planner confirmation
  mapping.

Source: `docs/decisions/open-questions.md`.

## Final recommendation

Stage 0 Hermes container capability work is sufficient to proceed to the next
decision step, with constraints:

- keep using the ready-made Hermes image through Docker Compose;
- keep project code/config as read-only host bind mounts;
- keep mutable Hermes runtime state in named volumes;
- use `menu-planner-probe` only as Stage 0 diagnostic code;
- design production Menu Planner behavior around deterministic domain tools,
  not direct model state mutation;
- treat Hermes built-in Telegram callbacks as available capability evidence,
  but do not choose the Menu Planner confirmation UX until the architecture
  decision step;
- restrict Telegram platform toolsets before any real user workflow.
