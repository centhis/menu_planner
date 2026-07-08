# Hermes neutral bind mount probe

Date: 2026-07-08

Purpose: close Stage 0 step 18 by proving that a host file can be mounted into
the ready-made Hermes container through Docker Compose as read-only.

## Probe File

Host file:

```text
tests/capability/mount-probe/mounted.txt
```

Contents:

```text
menu-planner-mount-probe
```

## Temporary Compose Mount

Temporary mount added only for this experiment:

```yaml
- ./tests/capability/mount-probe:/mnt/menu-planner-probe:ro
```

`docker compose config --no-interpolate` showed:

```text
source: /home/centhis/menu_planner/tests/capability/mount-probe
target: /mnt/menu-planner-probe
read_only: true
```

The container was recreated after adding the temporary mount:

```bash
docker compose up -d --force-recreate hermes
```

## Read Check

Command:

```bash
docker compose exec -T hermes \
  cat /mnt/menu-planner-probe/mounted.txt
```

Observed output:

```text
menu-planner-mount-probe
```

## Read-Only Check

Command:

```bash
docker compose exec -T hermes sh -lc '
echo forbidden-write \
  > /mnt/menu-planner-probe/should-not-exist.txt
'
```

Observed output:

```text
sh: 1: cannot create /mnt/menu-planner-probe/should-not-exist.txt: Read-only file system
```

Host-side check:

```bash
test ! -e tests/capability/mount-probe/should-not-exist.txt
```

Result: passed.

## Cleanup

The temporary mount was removed from `compose.yaml`, and the container was
recreated again:

```bash
docker compose up -d --force-recreate hermes
```

Final `docker inspect hermes` mounts no longer include
`/mnt/menu-planner-probe`. Current mounts are:

```text
/opt/menu-planner/hermes-codex-start.sh  ro
/etc/hermes/config.yaml                  ro
/opt/data                                rw
```

## Result

PASS: Docker Compose can mount a host directory into the ready-made Hermes
container read-only. The file is readable from inside the container, writes are
blocked by the mount, and final Compose/runtime state no longer includes the
temporary probe mount.

