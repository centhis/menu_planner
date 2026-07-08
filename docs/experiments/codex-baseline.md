# Codex baseline

Date: 2026-07-04

Purpose: record the actual Codex workspace baseline before Hermes
capability experiments.

## Environment

VM: `hermes`
Operating system: Ubuntu 24.04.4 LTS (`Linux hermes 6.8.0-124-generic x86_64`)
VS Code Remote-SSH: used by the operator, exact extension version not visible to Codex.
Codex extension version: not visible to Codex from the current workspace.
Codex CLI version: `codex-cli 0.142.5`
Codex CLI warning observed on startup: `could not create PATH aliases:
Read-only file system (os error 30)`.

## Authentication

Method: not inspected; credentials and tokens were not opened.
Result: Codex session is active and can read/write inside the workspace.

## Model provider access for Hermes

Purpose: record the Stage 0 preference for OpenAI access through Codex
authorization while keeping the deployment design provider-switchable.

Official Codex manual evidence, fetched from
`https://developers.openai.com/codex/codex-manual.md` on 2026-07-07:

- Codex supports two OpenAI sign-in methods: ChatGPT sign-in and API-key
  sign-in.
- `CODEX_HOME` defaults to `~/.codex` and is the root for Codex state,
  including config and auth.
- With file-based credential storage, Codex stores credentials in
  `$CODEX_HOME/auth.json`; this file contains access tokens and must be
  treated like a password.
- Codex custom model providers can use OpenAI authentication with
  `requires_openai_auth = true`; in that mode Codex ignores `env_key`.
- Codex access tokens are for trusted Codex local workflows. The manual says
  general OpenAI API calls should continue to use Platform API keys.

Project direction:

- Stage 0 should use OpenAI access through Hermes Codex authorization first.
- The user reported that Hermes Codex authorization was already checked in a
  neighboring working directory. This repository still needs a reproducible
  evidence record before marking the local capability spike complete.
- `.env.example` may list `OPENAI_API_KEY` and other provider credentials as
  optional placeholders for later provider switching.
- Do not copy or display `auth.json`.
- Do not commit Codex credentials.
- Do not put `CODEX_ACCESS_TOKEN` or `auth.json` contents in `.env.example`.
- Treat "Hermes uses OpenAI through Codex authorization" as a capability spike
  that is externally confirmed by the user and still needs local reproduction
  in this repository: exact image, container user, `HOME`, `CODEX_HOME`, config
  path, and non-secret command output.
- If a later Hermes configuration selects direct OpenAI API access, then
  `OPENAI_API_KEY` belongs in local `.env`, not in Git.

## Sandbox

approval_policy: managed approvals; commands can request escalation with user confirmation.
sandbox_mode: `workspace-write`
Writable roots:

- `/home/centhis/menu_planner`
- `/tmp`

Network access: restricted.

Sandboxed shell commands currently run without approval for workspace reads.
Write boundary probe:

- write inside `/home/centhis/menu_planner` works;
- write inside `/tmp` works;
- write to `/home/centhis/.codex-sandbox-denied-probe` was denied with
  `Read-only file system`.

`apply_patch` probe: add, update, and delete succeeded for a temporary file in
`docs/experiments/`.

## MCP

Configured MCP servers according to `codex mcp list`:

| Name | URL | Status | Auth |
|---|---|---|---|
| `openaiDeveloperDocs` | `https://developers.openai.com/mcp` | `enabled` | `Unsupported` |

MCP resources/templates visible through Codex resource listing:

- resources: none
- resource templates: none

MCP tools visible through Codex tool discovery:

- `mcp__openaiDeveloperDocs.search_openai_docs`
- `mcp__openaiDeveloperDocs.list_openai_docs`
- `mcp__openaiDeveloperDocs.fetch_openai_doc`
- `mcp__openaiDeveloperDocs.list_api_endpoints`

## Instructions

Global AGENTS: provided to the Codex session as working agreements; no global
filesystem `AGENTS.md` path was inspected.

Project AGENTS:

- `/home/centhis/menu_planner/AGENTS.md`

Additional project rule file inspected:

- `/home/centhis/menu_planner/.codex/rules/project.rules`

## Rules

docker build: forbidden.
docker compose build: forbidden.
docker compose restart: prompt / explicit user approval required.
git reset --hard: forbidden.

Related Docker boundary:

- Hermes must be run from a ready Docker image through Docker Compose.
- Custom Hermes images, `docker commit`, `docker cp` installation, package
  installation inside the Hermes container, and editing files inside a running
  container are forbidden.
- Host-side files may be edited and mounted through bind mounts.
- `docker compose exec` is allowed only for diagnostics and requires approval.

## Skills

Project skills:

- `verified-small-change`
- `hermes-container-spike`

System skills visible in this session:

- `imagegen`
- `openai-docs`
- `plugin-creator`
- `skill-creator`
- `skill-installer`

## Result

PASS

## Open problems

- Exact VS Code Remote-SSH extension version was not visible from the Codex
  process.
- Exact Codex IDE extension version was not visible from the Codex process.
- Authentication method was not inspected because credentials and token files
  must not be opened.
- `codex` CLI startup attempts to create PATH aliases in a read-only location
  and continues after warning.
