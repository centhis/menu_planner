# Stage 10.5 Live Telegram Readiness

Date: 2026-07-12

## Scope

This note records Stage 10.5 step 3 readiness checks before building the live
Telegram UX sandbox screens.

Safety constraints followed:

- `.env`, `auth.json`, token files and credential files were not opened;
- Telegram bot token and authorized user id are not recorded here;
- runtime environment evidence is sanitized to configured/not configured;
- no Hermes image was built or modified;
- no files were edited inside the running container.

## Container Status

`docker compose ps` showed:

- `hermes`: running from `nousresearch/hermes-agent:v2026.6.19`;
- `menu-planner-app`: running from `menu-planner-app:local`;
- `menu-planner-postgres`: running and healthy.

`docker compose config --services` showed:

- `hermes`;
- `postgres`;
- `app`.

## Runtime Telegram Configuration

Sanitized Docker environment inspection showed:

- `TELEGRAM_BOT_TOKEN=<set>`;
- `TELEGRAM_ALLOWED_USERS=<set>`;
- `TELEGRAM_HOME_CHANNEL=` empty;
- `TELEGRAM_PROXY` configured;
- Hermes dashboard auth values configured but redacted.

This proves the running Hermes container has a token and allowlist value
configured, without recording their values.

## Menu Planner Plugin Or UX Sandbox Adapter

Host-side Menu Planner Hermes plugin package exists:

```text
plugins/menu-planner/plugin.yaml
```

It declares Menu Planner tools and hooks.

Current `compose.yaml` does not mount `plugins/menu-planner` into Hermes and
the current managed Hermes config enables only dashboard basic auth. Therefore
the live Menu Planner plugin is not proven loaded in the running Hermes
container during this step.

Stage 10.5 can proceed in one of two safe ways:

- mount and enable the existing Menu Planner plugin reproducibly in a later
  step; or
- build a narrow UX sandbox adapter first, then wire it to live Telegram.

No mutable container install, `docker cp`, custom Hermes image or in-container
file edit was performed.

## Live Telegram Smoke

Initial command:

```sh
docker exec hermes sh -lc 'hermes send ...'
```

Result:

- failed before network send because `hermes` was not in the non-interactive
  shell path.

CLI path check found:

- `/opt/hermes/.venv/bin/hermes`;
- `/opt/hermes/bin/hermes`.

Live smoke command:

```sh
docker exec hermes sh -lc '
  /opt/hermes/.venv/bin/hermes send \
    --quiet \
    --to "telegram:${TELEGRAM_ALLOWED_USERS%%,*}" \
    "Menu Planner Stage 10.5 live readiness smoke: sanitized ping. No action needed."
'
```

Result:

- command exited successfully with no output;
- no token or user id was printed;
- message text contained no private data and no action request.

Manual confirmation still needed:

- confirmed by the user in chat: the Telegram message was visible in the
  authorized Telegram chat.

## Readiness Result

Ready:

- Hermes container is running;
- Telegram token and allowlist are configured in the running container;
- a sanitized live send command exited successfully;
- the user confirmed that the live Telegram smoke message was received;
- no secret value is recorded in this report.

Not yet ready:

- Menu Planner plugin is not proven loaded in live Hermes runtime;
- UX sandbox adapter is not yet available;
- inline button and callback round-trip are not yet tested;
- user-visible sandbox screen and callback smoke are still pending.

## Next Step

Stage 10.5 step 4 should build or wire the live Telegram UX sandbox shell.

Before closing Stage 10.5, the user must see the sandbox in Telegram and click
at least one live inline button, with sanitized evidence recorded.
