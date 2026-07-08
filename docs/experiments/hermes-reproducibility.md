# Hermes reproducibility check

Date: 2026-07-08

Purpose: close Stage 0 step 23 by proving the current Hermes setup starts from
the ready-made image plus repository files and local `.env`, without manual
container mutation.

## Scope

This check used the existing `compose.yaml` and the ready-made image:

```text
nousresearch/hermes-agent:v2026.6.19
```

No Dockerfile, `docker build`, `docker compose build`, `docker cp`, package
installation, or in-container file editing was used.

Real `.env`, auth files, tokens, and credentials were not opened or displayed.
The transient Codex device code printed in logs was not copied into this
report.

## Preflight

Dockerfile absence:

```bash
find . -iname 'Dockerfile*' -print
```

Observed:

```text
(no output)
```

Compose build absence:

```bash
rg -n '^\s*build\s*:' compose.yaml
```

Observed:

```text
(no matches; rg exit code 1)
```

Compose model:

```bash
docker compose config --services
docker compose config --images
docker compose config --volumes
```

Observed:

```text
services: hermes
images: nousresearch/hermes-agent:v2026.6.19
volumes: hermes-data
```

Image after pull:

```bash
docker image inspect nousresearch/hermes-agent:v2026.6.19 \
  --format 'ID={{.Id}} DIGESTS={{json .RepoDigests}}'
```

Observed:

```text
ID=sha256:9f367c7756ef087661a361536a89f438d57a122b958dc23d82d456b1433e6e9e
DIGESTS=["nousresearch/hermes-agent@sha256:9f367c7756ef087661a361536a89f438d57a122b958dc23d82d456b1433e6e9e"]
```

## Reproduction Sequence

Commands:

```bash
docker compose down
docker compose pull
docker compose up -d
docker compose ps hermes
docker compose logs --tail=100 hermes
```

Observed `down`:

```text
Container hermes Removed
Network menu_planner_default Removed
```

Observed `pull`:

```text
Image nousresearch/hermes-agent:v2026.6.19 Pulling
Image nousresearch/hermes-agent:v2026.6.19 Pulled
```

Observed `up -d`:

```text
Network menu_planner_default Created
Container hermes Created
Container hermes Started
```

Observed `ps`:

```text
hermes  nousresearch/hermes-agent:v2026.6.19  Up  0.0.0.0:8642->8642/tcp, 0.0.0.0:9119->9119/tcp
```

Observed safe log excerpts:

```text
Syncing bundled skills into ~/.hermes/skills/ ...
Done: 0 new, 0 updated, 73 unchanged. 73 total bundled.
s6-rc: info: service main-hermes successfully started
s6-rc: info: service dashboard successfully started
HERMES_DASHBOARD_READY port=9119
[hermes] HERMES_USE_CODEX_AUTH=1; checking openai-codex auth...
[hermes] Starting Hermes device-code authorization.
Waiting for sign-in... (press Ctrl+C to cancel)
```

Expected current warnings:

```text
openai-codex: logged out
No user allowlists configured
No messaging platforms enabled
raft CLI not found in PATH
```

These do not indicate a reproducibility failure for Stage 0: Codex device
authorization and Telegram platform configuration are separate operator/runtime
steps already tracked in earlier open questions and capability reports.

## Follow-Up After Operator Auth And Telegram Setup

Follow-up date: 2026-07-08.

After the operator configured `openai-codex` auth and the Telegram bot, the
same ready image and Compose service were checked again. Real `.env` values,
tokens, and credential files were not opened or displayed.

Runtime flags were checked as set/not-set only:

```text
HERMES_USE_CODEX_AUTH=set
TELEGRAM_BOT_TOKEN=set
TELEGRAM_ALLOWED_USERS=set
TELEGRAM_HOME_CHANNEL=not-set
TELEGRAM_PROXY=set
```

Auth check:

```bash
docker compose exec -T hermes sh -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes auth status openai-codex'
```

Observed:

```text
openai-codex: logged in
```

Model smoke:

```bash
docker compose exec -T hermes sh -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes --ignore-rules -z "Reply exactly: stage0-model-ok"'
```

Observed:

```text
stage0-model-ok
```

Telegram outbound smoke used the first configured allowed user as a target
without printing the ID:

```bash
docker compose exec -T hermes sh -lc '
  target="${TELEGRAM_ALLOWED_USERS%%,*}"
  hermes send --quiet --to "telegram:$target" \
    "Menu Planner Stage 0 Telegram delivery smoke: OK"
'
```

Observed:

```text
telegram_send=pass
```

Fresh logs after the final restart showed:

```text
[hermes] HERMES_USE_CODEX_AUTH=1; checking openai-codex auth...
openai-codex: logged in
[hermes] openai-codex auth is configured.
HERMES_DASHBOARD_READY port=9119
```

The previous warnings `No user allowlists configured` and
`No messaging platforms enabled` were no longer observed in the fresh log
window after Telegram configuration.

## Post-start Checks

### Hermes is running

```bash
docker compose ps hermes
```

Observed:

```text
STATUS: Up
PORTS: 8642, 9119
```

### Probe plugin is discovered

```bash
docker compose exec -T hermes sh -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes plugins list --enabled --plain'
```

Observed:

```text
enabled      bundled  1.0.0    basic
enabled      user     0.1.0    menu-planner-probe
```

### Probe toolset is enabled

```bash
docker compose exec -T hermes sh -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes tools list --platform cli | grep menu_planner_probe || true'
```

Observed:

```text
✓ enabled  menu_planner_probe  🔌 Menu Planner Probe
```

### Hermes skills are available

```bash
docker compose exec -T hermes sh -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes skills list --source builtin --enabled-only | head -10'
```

Observed enabled built-in skills included:

```text
dogfood
yuanbao
claude-code
codex
hermes-agent
opencode
```

### Mounts work

```bash
docker inspect hermes \
  --format '{{range .Mounts}}{{println .Type "|" .Name "|" .Source "|" .Destination "|" .RW}}{{end}}'
```

Observed:

```text
bind |  | /home/centhis/menu_planner/plugins/menu-planner-probe | /opt/data/plugins/menu-planner-probe | false
volume | menu_planner_hermes-data | /var/lib/docker/volumes/menu_planner_hermes-data/_data | /opt/data | true
bind |  | /home/centhis/menu_planner/scripts/hermes-codex-start.sh | /opt/menu-planner/hermes-codex-start.sh | false
bind |  | /home/centhis/menu_planner/config/hermes-managed-config.yaml | /etc/hermes/config.yaml | false
```

### Config applies

```bash
docker compose exec -T hermes sh -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; hermes plugins list --enabled --plain'
```

Evidence:

- `dashboard_auth/basic` appears as enabled bundled plugin;
- `menu-planner-probe` appears as enabled user plugin.

That confirms the read-only managed config overlay applies at startup.

### State is in the expected volume

```bash
docker compose exec -T hermes sh -lc \
  'export PATH=/opt/hermes/bin:/opt/hermes/.venv/bin:$PATH; printf "config_path="; hermes config path; printf "env_path="; hermes config env-path; stat -c "%n|%F|%s|%a|%U:%G" /opt/data /opt/data/config.yaml /opt/data/state.db /opt/data/sessions /opt/data/logs /opt/data/memories /opt/data/skills'
```

Observed:

```text
config_path=/opt/data/config.yaml
env_path=/opt/data/.env
/opt/data|directory|4096|700|hermes:hermes
/opt/data/config.yaml|regular file|16523|640|hermes:hermes
/opt/data/state.db|regular file|126976|644|hermes:hermes
/opt/data/sessions|directory|4096|700|hermes:hermes
/opt/data/logs|directory|4096|700|hermes:hermes
/opt/data/memories|directory|4096|700|hermes:hermes
/opt/data/skills|directory|4096|700|hermes:hermes
```

## Conclusion

PASS: the current Stage 0 Hermes setup is reproducible with:

```bash
docker compose pull
docker compose up -d
```

Inputs required:

- repository files;
- local `.env` values for dashboard/auth/provider selection;
- Docker named volume `menu_planner_hermes-data` when preserving runtime state.

No manual installation or mutation inside the running container is required.

## Limits

- This check did not delete volumes with `docker compose down -v`.
- Initial reproduction intentionally stopped at the Codex device-code waiting
  state. The follow-up check above verified completed `openai-codex` auth and a
  one-shot inference after operator login.
- Initial reproduction did not configure Telegram. The follow-up check above
  verified Telegram env presence and outbound bot delivery.
- Live Telegram callback tap was not performed in this check.
