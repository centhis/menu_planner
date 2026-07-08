# Hermes mount map

Date: 2026-07-08

Purpose: close Stage 0 step 17 by recording the observed Hermes paths and
current mounts without changing the ready-made image or reading secrets.

## CLI Evidence

`docker compose exec -T hermes sh -lc 'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes --help'`
confirmed that the installed CLI exposes `plugins`, `skills`, `tools`, and
`gateway` commands.

The subcommands were checked individually:

```text
hermes plugins --help -> install, update, remove, list, enable, disable
hermes skills --help  -> browse, search, install, inspect, list, check, update, ...
hermes tools --help   -> list, disable, enable, post-setup
hermes gateway --help -> run, start, stop, restart, status, install, uninstall, ...
```

Baseline note: `docker compose exec ... sh` does not inherit the image PATH
containing `/opt/hermes/bin`, so these checks use explicit PATH bootstrap.

## Package Location

Command:

```bash
docker compose exec -T hermes sh -lc '
python3 - <<'"'"'PY'"'"'
import importlib.util

for name in ("hermes", "hermes_cli", "hermes_agent"):
    spec = importlib.util.find_spec(name)
    print(name, "=>", spec.origin if spec else "not found")
PY
'
```

Observed:

```text
hermes => not found
hermes_cli => /opt/hermes/hermes_cli/__init__.py
hermes_agent => not found
```

## Observed Paths

| Purpose | Path | Class | Evidence |
|---|---|---|---|
| Hermes home | `/opt/data` | named volume, rw runtime state | `get_hermes_home -> /opt/data`; Docker mount `menu_planner_hermes-data -> /opt/data` |
| User config | `/opt/data/config.yaml` | named volume, rw runtime state | `hermes config path`; `get_config_path -> /opt/data/config.yaml`; file exists |
| Hermes env file | `/opt/data/.env` | named volume, secret-capable runtime state | `hermes config env-path`; `get_env_path -> /opt/data/.env`; file currently missing |
| Managed config overlay | `/etc/hermes/config.yaml` | project bind mount, ro | Docker mount `./config/hermes-managed-config.yaml -> /etc/hermes/config.yaml` |
| User plugins | `/opt/data/plugins` | named volume, rw runtime state | `plugins.py` scans `get_hermes_home() / "plugins"`; directory exists |
| Probe plugin | `/opt/data/plugins/menu-planner-probe` | project bind mount, ro | Docker mount `./plugins/menu-planner-probe -> /opt/data/plugins/menu-planner-probe`; Hermes lists enabled user plugin `menu-planner-probe` |
| Bundled plugins | `/opt/hermes/plugins` | image content, read-only for this project | `plugins.py` `get_bundled_plugins_dir()` falls back to repo `plugins` dir |
| Project plugins | `./.hermes/plugins` inside container cwd | disabled unless explicitly enabled | `plugins.py` scans `Path.cwd() / ".hermes" / "plugins"` only when `HERMES_ENABLE_PROJECT_PLUGINS` is enabled |
| Hermes skills | `/opt/data/skills` | named volume, rw runtime state | `tools.skills_hub.SKILLS_DIR -> /opt/data/skills`; directory exists |
| Session database | `/opt/data/state.db` | named volume, rw runtime state | source references `get_hermes_home() / "state.db"`; file exists |
| Session files | `/opt/data/sessions` | named volume, rw runtime state | source references `get_hermes_home() / "sessions"`; directory exists |
| Logs | `/opt/data/logs` | named volume, rw runtime state | `logs.py` uses `get_hermes_home() / "logs" / filename`; directory exists |
| Built-in memory | `/opt/data/memories/MEMORY.md`, `/opt/data/memories/USER.md` | named volume, rw runtime state | `web_server.py` uses `get_hermes_home() / "memories"`; directory exists |
| Startup wrapper | `/opt/menu-planner/hermes-codex-start.sh` | project bind mount, ro | Docker mount from `./scripts/hermes-codex-start.sh` |

## Current Docker Mounts

Command:

```bash
docker inspect hermes \
  --format '{{range .Mounts}}{{println .Type "|" .Name "|" .Source "|" .Destination "|" .RW}}{{end}}'
```

Observed:

| Type | Host/volume | Container path | Writable |
|---|---|---|---|
| volume | `menu_planner_hermes-data` | `/opt/data` | `true` |
| bind | `/home/centhis/menu_planner/scripts/hermes-codex-start.sh` | `/opt/menu-planner/hermes-codex-start.sh` | `false` |
| bind | `/home/centhis/menu_planner/config/hermes-managed-config.yaml` | `/etc/hermes/config.yaml` | `false` |
| bind | `/home/centhis/menu_planner/plugins/menu-planner-probe` | `/opt/data/plugins/menu-planner-probe` | `false` |

## Requested Mount Map

| Purpose | Host path | Container path | Mode | Evidence |
|---|---|---|---|---|
| Managed configuration | `./config/hermes-managed-config.yaml` | `/etc/hermes/config.yaml` | `ro` | Docker inspect mount |
| Hermes user config | named volume `menu_planner_hermes-data` | `/opt/data/config.yaml` | `rw` | `hermes config path`; file exists |
| Hermes env/secrets path | named volume `menu_planner_hermes-data` | `/opt/data/.env` | `rw` | `hermes config env-path`; file currently missing |
| User plugins | named volume `menu_planner_hermes-data` | `/opt/data/plugins` | `rw` | source `get_hermes_home() / "plugins"`; directory exists |
| Bundled plugins | image filesystem | `/opt/hermes/plugins` | image-owned | source `get_bundled_plugins_dir()` |
| Project plugins | not mounted | unknown target for this project | unknown | no project plugin bind mount is present |
| Probe plugin | `./plugins/menu-planner-probe` | `/opt/data/plugins/menu-planner-probe` | `ro` | Docker inspect mount; `hermes plugins list --enabled --plain` |
| Hermes skills | named volume `menu_planner_hermes-data` | `/opt/data/skills` | `rw` | `tools.skills_hub.SKILLS_DIR`; directory exists |
| Domain code | not mounted | unknown | unknown | no `src/` bind mount is present |
| Sessions | named volume `menu_planner_hermes-data` | `/opt/data/state.db`, `/opt/data/sessions` | `rw` | source references and existing paths |
| Memory | named volume `menu_planner_hermes-data` | `/opt/data/memories` | `rw` | source references and existing directory |
| Logs | named volume `menu_planner_hermes-data` | `/opt/data/logs` | `rw` | `logs.py` source and existing directory |
| Startup wrapper | `./scripts/hermes-codex-start.sh` | `/opt/menu-planner/hermes-codex-start.sh` | `ro` | Docker inspect mount |

## Source Evidence

Configuration:

```text
hermes config path     -> /opt/data/config.yaml
hermes config env-path -> /opt/data/.env
get_hermes_home        -> /opt/data
get_config_path        -> /opt/data/config.yaml
get_env_path           -> /opt/data/.env
```

Plugin loader:

```text
/opt/hermes/hermes_cli/plugins.py:
- bundled plugins: get_bundled_plugins_dir()
- user plugins: get_hermes_home() / "plugins"
- project plugins: Path.cwd() / ".hermes" / "plugins" when enabled
```

Skills:

```text
/opt/hermes/tools/skills_hub.py:
tools.skills_hub.SKILLS_DIR -> /opt/data/skills
```

Sessions:

```text
source references:
- get_hermes_home() / "state.db"
- get_hermes_home() / "sessions"
observed:
- /opt/data/state.db exists
- /opt/data/sessions exists
```

Logs:

```text
/opt/hermes/hermes_cli/logs.py:
log_path = get_hermes_home() / "logs" / filename
observed:
- /opt/data/logs exists
```

Memory:

```text
/opt/hermes/hermes_cli/web_server.py:
mem_dir = get_hermes_home() / "memories"
files: MEMORY.md, USER.md
observed:
- /opt/data/memories exists
```

## Unknowns

- The production Menu Planner plugin mount path is not defined yet.
- The project `skills/hermes` bind mount is not present yet.
- Domain source code is not mounted into Hermes yet.
- Runtime state persistence across `docker compose down` is recorded in
  `docs/experiments/hermes-runtime-state.md`.
- Project plugin loading through `./.hermes/plugins` is present in Hermes
  source but disabled unless `HERMES_ENABLE_PROJECT_PLUGINS` is deliberately
  enabled.

## Security Notes

- Real `.env`, `auth.json`, token, and credential contents were not opened.
- `/opt/data/.env` path was recorded only as a path; it is currently absent in
  the observed container.
- File listings avoided reading secret-capable file contents.
