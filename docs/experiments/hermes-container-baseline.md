# Hermes container baseline

Date: 2026-07-08

Purpose: record the observed Hermes container baseline for Stage 0 step 16
without changing the image or reading secrets.

## Compose

- Working directory: `/home/centhis/menu_planner`
- Compose file: `compose.yaml`
- Compose project: `menu_planner`
- Service: `hermes`
- Container: `hermes`
- Container status during baseline: `running`
- Image: `nousresearch/hermes-agent:v2026.6.19`
- Tag: `v2026.6.19`
- Image ID: `sha256:9f367c7756ef087661a361536a89f438d57a122b958dc23d82d456b1433e6e9e`
- Repo digest:
  `nousresearch/hermes-agent@sha256:9f367c7756ef087661a361536a89f438d57a122b958dc23d82d456b1433e6e9e`
- Upstream revision label:
  `2bd1977d8fad185c9b4be47884f7e87f1add0ce3`

Evidence:

```bash
docker compose ps -a
docker compose config --services
docker compose config --images
docker compose config --volumes
docker image inspect nousresearch/hermes-agent:v2026.6.19 \
  --format 'ID={{.Id}} ...'
```

Observed Compose outputs:

```text
services: hermes
images: nousresearch/hermes-agent:v2026.6.19
volumes: hermes-data
```

## Runtime

- Container user from image metadata: `root`
- Runtime identity from `docker compose exec`: `uid=0(root) gid=0(root) groups=0(root)`
- Runtime `HOME` from `docker compose exec`: `/root`
- `HERMES_HOME`: `/opt/data`
- Working directory: `/opt/hermes`
- Image entrypoint: `["/init","/opt/hermes/docker/main-wrapper.sh"]`
- Image CMD: absent in image config
- Compose command:
  `["/opt/menu-planner/hermes-codex-start.sh","gateway","run"]`
- Hermes executable path after explicit PATH bootstrap: `/opt/hermes/bin/hermes`
- Hermes version:
  `Hermes Agent v0.17.0 (2026.6.19) · upstream 2bd1977d`
- Python version reported by Hermes: `3.13.5`
- OpenAI SDK version reported by Hermes: `2.24.0`

Evidence:

```bash
docker compose exec -T hermes sh -lc '
set -eu
echo "== identity =="
id
echo "== current directory =="
pwd
echo "== home =="
printf "%s\n" "$HOME"
echo "== hermes executable =="
command -v hermes || true
echo "== hermes version =="
hermes --version || true
echo "== hermes help =="
hermes --help || true
'
```

Observed output:

```text
== identity ==
uid=0(root) gid=0(root) groups=0(root)
== current directory ==
/opt/hermes
== home ==
/root
== hermes executable ==
== hermes version ==
sh: 11: hermes: not found
== hermes help ==
sh: 13: hermes: not found
```

Follow-up read-only PATH check:

```bash
docker compose exec -T hermes sh -lc '
printf "PATH=%s\n" "$PATH"
printf "HERMES_HOME=%s\n" "${HERMES_HOME:-}"
ls -l /opt/hermes/bin/hermes /opt/hermes/hermes 2>/dev/null || true
'
```

Observed output:

```text
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HERMES_HOME=/opt/data
/opt/hermes/bin/hermes
/opt/hermes/hermes
```

Hermes version was verified with explicit PATH:

```bash
docker compose exec -T hermes sh -lc '
export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH
command -v hermes || true
hermes --version || true
'
```

Observed output:

```text
/opt/hermes/bin/hermes
Hermes Agent v0.17.0 (2026.6.19) · upstream 2bd1977d
Project: /opt/hermes
Python: 3.13.5
OpenAI SDK: 2.24.0
```

`hermes --help` was also verified with explicit PATH in a read-only disposable
container for the same image. It lists the top-level command set including
`gateway`, `auth`, `hooks`, `skills`, `plugins`, `tools`, `mcp`, `sessions`,
`dashboard`, and `logs`.

## Current Mounts

| Type | Host/volume | Container path | Writable |
|---|---|---|---|
| bind | `/home/centhis/menu_planner/config/hermes-managed-config.yaml` | `/etc/hermes/config.yaml` | `false` |
| volume | `/var/lib/docker/volumes/menu_planner_hermes-data/_data` | `/opt/data` | `true` |
| bind | `/home/centhis/menu_planner/scripts/hermes-codex-start.sh` | `/opt/menu-planner/hermes-codex-start.sh` | `false` |

Evidence:

```bash
docker inspect hermes \
  --format '{{range .Mounts}}{{println .Type "|" .Source "|" .Destination "|" .RW}}{{end}}'
```

## Image Metadata

Image metadata was collected without reporting `.Config.Env`.

```bash
docker image inspect nousresearch/hermes-agent:v2026.6.19 \
  --format 'USER={{.Config.User}}'
docker image inspect nousresearch/hermes-agent:v2026.6.19 \
  --format 'WORKDIR={{.Config.WorkingDir}}'
docker image inspect nousresearch/hermes-agent:v2026.6.19 \
  --format 'ENTRYPOINT={{json .Config.Entrypoint}}'
docker image inspect nousresearch/hermes-agent:v2026.6.19 \
  --format '{{if .Config.Cmd}}CMD={{json .Config.Cmd}}{{else}}CMD=<absent>{{end}}'
```

Observed values:

```text
USER=root
WORKDIR=/opt/hermes
ENTRYPOINT=["/init","/opt/hermes/docker/main-wrapper.sh"]
CMD=<absent>
```

## Unknowns

These were intentionally left for Stage 0 step 17 at the time this baseline
was created. Step 17 results are recorded in
`docs/experiments/hermes-mount-map.md`.

- Configuration path: partially observed as managed mount
  `/etc/hermes/config.yaml`; full Hermes user configuration path not finalized
  by step 16.
- Plugin path: unknown in this baseline.
- Skills path: unknown in this baseline.
- Session path: unknown in this baseline.
- Memory path: unknown in this baseline.
- Logs path: unknown in this baseline.

## Security Notes

- Real `.env` values, auth files, tokens, and credentials were not opened or
  copied into this report.
- Docker image `.Config.Env` was not included in the report.
- The report contains only observed non-secret container metadata and command
  outputs.
