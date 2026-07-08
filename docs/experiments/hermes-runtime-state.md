# Hermes runtime state and volumes

Date: 2026-07-08

Purpose: close Stage 0 step 22 by separating read-only project inputs from
mutable Hermes runtime state, and by checking what survives container removal
without deleting named volumes.

## Scope

This experiment used only the ready-made Hermes image through Docker Compose.
No Dockerfile, image build, `docker cp`, package installation, or in-container
file editing was used.

Secret-bearing files were not opened. Real `.env`, `auth.json`, tokens, and
credentials were not read or displayed.

`docker compose down -v` was intentionally not run because it deletes named
volumes and requires a separate explicit approval.

## Current Mount Classification

Observed command:

```bash
docker inspect hermes \
  --format '{{range .Mounts}}{{println .Type "|" .Name "|" .Source "|" .Destination "|" .RW}}{{end}}'
```

Observed after `docker compose up -d hermes`:

```text
bind |  | /home/centhis/menu_planner/scripts/hermes-codex-start.sh | /opt/menu-planner/hermes-codex-start.sh | false
bind |  | /home/centhis/menu_planner/config/hermes-managed-config.yaml | /etc/hermes/config.yaml | false
bind |  | /home/centhis/menu_planner/plugins/menu-planner-probe | /opt/data/plugins/menu-planner-probe | false
volume | menu_planner_hermes-data | /var/lib/docker/volumes/menu_planner_hermes-data/_data | /opt/data | true
```

### Read-only project inputs

These are versioned project inputs and should remain bind mounted read-only:

| Host path | Container path | Status |
|---|---|---|
| `./config/hermes-managed-config.yaml` | `/etc/hermes/config.yaml` | present, `ro` |
| `./plugins/menu-planner-probe` | `/opt/data/plugins/menu-planner-probe` | present, `ro` |
| `./scripts/hermes-codex-start.sh` | `/opt/menu-planner/hermes-codex-start.sh` | present, `ro` |
| `./plugins/menu-planner` | target not selected yet | future production plugin |
| `./skills/hermes` | target not selected yet | future project skills |
| `./src` | target not selected yet | future domain code if mounted |

Do not store these project inputs in a Docker named volume unless there is a
separate migration decision. They should be reproducible from git.

### Writable runtime state

All observed mutable Hermes runtime state is rooted in the `hermes-data` named
volume mounted at `/opt/data`.

Safe stat-only command:

```bash
docker compose exec -T hermes sh -lc '
  export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH
  printf "config_path="; hermes config path
  printf "env_path="; hermes config env-path
  for p in \
    /opt/data \
    /opt/data/config.yaml \
    /opt/data/.env \
    /opt/data/state.db \
    /opt/data/sessions \
    /opt/data/logs \
    /opt/data/memories \
    /opt/data/skills \
    /opt/data/plugins \
    /opt/data/plugins/menu-planner-probe \
    /etc/hermes/config.yaml \
    /opt/menu-planner/hermes-codex-start.sh
  do
    if [ -e "$p" ]; then
      stat -c "%n|%F|%s|%a|%U:%G" "$p"
    else
      printf "%s|missing\n" "$p"
    fi
  done
'
```

Observed:

```text
config_path=/opt/data/config.yaml
env_path=/opt/data/.env
/opt/data|directory|4096|700|hermes:hermes
/opt/data/config.yaml|regular file|16523|640|hermes:hermes
/opt/data/.env|missing
/opt/data/state.db|regular file|126976|644|hermes:hermes
/opt/data/sessions|directory|4096|700|hermes:hermes
/opt/data/logs|directory|4096|700|hermes:hermes
/opt/data/memories|directory|4096|700|hermes:hermes
/opt/data/skills|directory|4096|700|hermes:hermes
/opt/data/plugins|directory|4096|755|hermes:hermes
/opt/data/plugins/menu-planner-probe|directory|4096|775|UNKNOWN:UNKNOWN
/etc/hermes/config.yaml|regular file|72|664|UNKNOWN:UNKNOWN
/opt/menu-planner/hermes-codex-start.sh|regular file|2146|775|UNKNOWN:UNKNOWN
```

Runtime state classes:

| Path | Class | Migration note |
|---|---|---|
| `/opt/data/config.yaml` | mutable Hermes user config | migrate with Hermes runtime state |
| `/opt/data/.env` | secret-capable runtime env file | migrate only through secret handling process; currently missing |
| `/opt/data/state.db` | session/runtime database | migrate when preserving Hermes sessions/state |
| `/opt/data/sessions` | session files | migrate with `state.db` |
| `/opt/data/logs` | runtime logs | optional operational migration |
| `/opt/data/memories` | Hermes memory files | migrate when preserving assistant memory |
| `/opt/data/skills` | Hermes seeded/installed skills | migrate only if user/runtime-installed skills are desired |
| `/opt/data/plugins` | Hermes user plugin root | do not rely on it for project plugin source; project probe is overmounted `ro` |

## Persistence Test

Marker: use a reversible Hermes-native config change, not manual file editing.

The marker was:

```bash
docker compose exec -T hermes sh -lc '
  export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH
  hermes tools disable --platform cli menu_planner_probe
  hermes tools list --platform cli | grep menu_planner_probe || true
'
```

Observed marker before stop:

```text
✓ Disabled: menu_planner_probe
  ✗ disabled  menu_planner_probe  🔌 Menu Planner Probe
```

Then:

```bash
docker compose down
```

Observed:

```text
Container hermes Removed
Network menu_planner_default Removed
```

After `down`, the named volume still existed:

```bash
docker inspect menu_planner_hermes-data \
  --format 'volume={{.Name}} mountpoint={{.Mountpoint}}'
```

Observed:

```text
volume=menu_planner_hermes-data mountpoint=/var/lib/docker/volumes/menu_planner_hermes-data/_data
```

Then:

```bash
docker compose up -d hermes
```

Observed marker after restart:

```text
  ✗ disabled  menu_planner_probe  🔌 Menu Planner Probe
/opt/data/config.yaml|regular file|16500|640|hermes:hermes
/opt/data/state.db|regular file|126976|644|hermes:hermes
/opt/data/sessions|directory|4096|700|hermes:hermes
/opt/data/logs|directory|4096|700|hermes:hermes
/opt/data/memories|directory|4096|700|hermes:hermes
/opt/data/skills|directory|4096|700|hermes:hermes
```

Conclusion: mutable Hermes state in `menu_planner_hermes-data` survives
container removal and `docker compose down` when volumes are not deleted.

Cleanup: the diagnostic toolset marker was restored:

```bash
docker compose exec -T hermes sh -lc '
  export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH
  hermes tools enable --platform cli menu_planner_probe
'
```

Observed:

```text
✓ Enabled: menu_planner_probe
  ✓ enabled  menu_planner_probe  🔌 Menu Planner Probe
```

## What Survives

| Operation | Data that survives | Evidence |
|---|---|---|
| `docker compose up -d --force-recreate hermes` | named volume `/opt/data`; read-only bind mounts | prior Stage 0 plugin and mount probes |
| `docker compose down` | named volume `menu_planner_hermes-data`; runtime marker in `/opt/data/config.yaml` | marker remained disabled after `up -d` |
| `docker compose down -v` | not tested; Docker removes project named volumes by design | intentionally not run |

## Migration Set

For a migration that preserves Hermes runtime behavior, carry:

- Docker named volume `menu_planner_hermes-data`, or an equivalent backup of
  `/opt/data`;
- especially `/opt/data/config.yaml`, `/opt/data/state.db`,
  `/opt/data/sessions`, `/opt/data/memories`;
- `/opt/data/.env` only through a secrets-safe process if it exists.

For a reproducible project deployment, carry from git:

- Compose files;
- managed config bind mount files;
- project plugin source;
- project skill source;
- application/domain source.

Do not migrate project source by copying it out of `/opt/data`; it belongs in
versioned host files and read-only bind mounts.

## Open Items

- Production plugin mount path for `plugins/menu-planner` is still not
  selected.
- Project skill mount path for `skills/hermes` is still not selected.
- Domain source mount path for `src` is still not selected.
- `docker compose down -v` deletion was not executed; treat named volume loss
  as known Docker behavior, not locally tested evidence.
