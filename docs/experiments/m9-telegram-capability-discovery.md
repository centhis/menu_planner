# M9 Telegram capability discovery

Date: 2026-07-12

## Scope

This note records Stage 10 step 3 evidence for the installed Hermes Telegram
Gateway before implementing Menu Planner Telegram Alpha code.

The inspection was read-only:

- no `.env`, `auth.json`, token or credential file was opened;
- no real Telegram token or user id was printed;
- no Hermes image was built or modified;
- no package was installed in the Hermes container;
- no code was copied into a container;
- no running container files were edited.

One-shot `docker run` commands used the ready-made image and produced normal
s6 startup logs from temporary containers. Those logs did not include secret
values.

## Runtime And Compose Evidence

`docker compose ps` showed the current Hermes service:

- service: `hermes`;
- image: `nousresearch/hermes-agent:v2026.6.19`;
- command: `/init /opt/hermes/d...`;
- ports: `8642` and `9119` published;
- status: running.

`docker compose config --services` listed:

- `postgres`;
- `app`;
- `hermes`.

The checked `compose.yaml` configures the Hermes service with:

- image `nousresearch/hermes-agent:v2026.6.19`;
- command `/opt/menu-planner/hermes-codex-start.sh gateway run`;
- `hermes-data:/opt/data`;
- read-only managed config at `/etc/hermes/config.yaml`;
- Telegram env surface:
  - `TELEGRAM_BOT_TOKEN`;
  - `TELEGRAM_ALLOWED_USERS`;
  - `TELEGRAM_HOME_CHANNEL`;
  - `TELEGRAM_PROXY`.

Only placeholder variable names were inspected. Values were not printed.

The current managed config enables only:

```yaml
plugins:
  enabled:
    - dashboard_auth/basic
```

Implication: M9 must still enable the Menu Planner plugin through a
reproducible host config or mount path before live Telegram Alpha.

## Hermes Version

`docker run --rm nousresearch/hermes-agent:v2026.6.19 hermes --version`
returned:

- Hermes Agent `v0.17.0 (2026.6.19)`;
- upstream revision `2bd1977d`;
- project path `/opt/hermes`;
- Python `3.13.5`;
- OpenAI SDK `2.24.0`.

## Gateway CLI Surface

`hermes gateway --help` exposes:

- `run`;
- `start`;
- `stop`;
- `restart`;
- `status`;
- `install`;
- `uninstall`;
- `list`;
- `setup`;
- `migrate-legacy`;
- `enroll`.

`hermes gateway setup --help` only showed generic help for the setup command.
It did not expose a non-interactive Telegram callback probe.

## Telegram Configuration Surface

The installed code maps Telegram config/env into Gateway config:

- `gateway/config.py` maps `telegram.allow_from` to
  `TELEGRAM_ALLOWED_USERS` when the environment variable is not already set;
- `gateway/config.py` maps `TELEGRAM_BOT_TOKEN` to an enabled Telegram
  platform config;
- `TELEGRAM_HOME_CHANNEL` can configure a Telegram home channel;
- `TELEGRAM_PROXY` is read by the Telegram network path.

The Telegram adapter itself falls back to `TELEGRAM_ALLOWED_USERS` for
callback authorization. If no allowlist is present, it fails closed unless
`GATEWAY_ALLOW_ALL_USERS` is explicitly set.

Implication: M9 should keep the one-user allowlist in runtime config and record
only sanitized "set/not set" evidence.

## Incoming Message Identity Surface

`gateway/platforms/telegram.py` builds `MessageEvent` from Telegram messages
with:

- `chat_id`;
- `chat_name`;
- `chat_type` as `dm`, `group` or `channel`;
- Telegram `from_user.id` as `source.user_id` when available;
- user full name as display metadata;
- `thread_id` for real topic/forum messages;
- Telegram `message_id`.

Text messages are buffered and coalesced before dispatch when Telegram splits
long messages. Commands dispatch directly.

Implications for M9:

- Application `user_id` mapping should use Telegram numeric user id from the
  source, not display name or free text.
- Alpha message-size and rate policies must run in the Menu Planner boundary,
  because Hermes may aggregate split Telegram text before dispatch.
- Topic/thread data can be retained as transport/session metadata but must not
  replace Application `WorkflowRun`.

## Inline Button And Callback Evidence

The installed Telegram adapter imports:

- `InlineKeyboardButton`;
- `InlineKeyboardMarkup`;
- `CallbackQueryHandler`.

The adapter registers:

```text
CallbackQueryHandler(self._handle_callback_query)
```

Observed built-in callback namespaces:

- `ea:` for exec approval callbacks;
- `sc:` for slash confirmation callbacks;
- `cl:` for clarify callbacks;
- `mp:`, `mpg:`, `mm:`, `mc:`, `mb`, `mx`, `mg:` for model picker callbacks;
- `gt:` for Gmail triage callbacks.

Slash confirmation uses callback data:

```text
sc:once:<confirm_id>
sc:always:<confirm_id>
sc:cancel:<confirm_id>
```

Clarify uses callback data:

```text
cl:<clarify_id>:<idx>
cl:<clarify_id>:other
```

The installed code explicitly notes that Telegram caps `callback_data` at
64 bytes and keeps `cl:<id>:<idx>` short.

Callback authorization checks `query.from_user.id` against the same Telegram
authorization path before resolving built-in `ea:`, `sc:` or `cl:` callbacks.

Repeated built-in callbacks are handled by state lookup:

- missing approval state returns "already resolved";
- missing slash-confirm state returns "already resolved";
- missing clarify state returns "already resolved".

## Callback Support Status

Verified for M9:

- installed Telegram adapter supports inline keyboard buttons;
- installed Telegram adapter registers a callback query handler;
- built-in slash confirmation callbacks exist;
- built-in clarify callbacks exist;
- callback authorization uses Telegram caller id;
- callback data must fit a 64-byte Telegram limit.

Not verified in step 3:

- a live Telegram button tap round trip;
- a project-owned Menu Planner callback namespace;
- arbitrary plugin-owned callback dispatch;
- exact Menu Planner `confirmation_id` round trip through live Telegram;
- synthetic Telegram E2E harness inside Hermes.

M9 should therefore start from built-in `sc:` confirmation or a project-owned
synthetic gateway fixture until live callback behavior is proven.

## Synthetic E2E Surface

No ready non-interactive `hermes gateway setup` or built-in fake Telegram E2E
command was discovered in this step.

The installed source has structured `MessageEvent` construction and built-in
callback handlers that can be represented by project fixtures, but using those
fixtures is a project test strategy rather than a Hermes-provided fake Telegram
provider.

## Commands Run

```sh
docker compose ps
docker compose config --services
sed -n '1,240p' compose.yaml
sed -n '1,200p' config/hermes-managed-config.yaml
docker run --rm nousresearch/hermes-agent:v2026.6.19 hermes --version
docker run --rm nousresearch/hermes-agent:v2026.6.19 hermes gateway --help
docker run --rm nousresearch/hermes-agent:v2026.6.19 hermes gateway setup --help
```

Additional one-shot image inspections used `grep` and `sed` against:

```text
/opt/hermes/gateway/platforms/telegram.py
/opt/hermes/gateway/config.py
/opt/hermes/gateway/platforms/ADDING_A_PLATFORM.md
```

## Unknowns Carried Forward

- Whether a live Telegram callback tap can round-trip an Application-owned
  `confirmation_id` without using arbitrary project-owned callback namespaces.
- Whether M9 should rely on Hermes built-in `sc:` callbacks only or add a
  project-owned callback adapter after further proof.
- Whether a live Telegram E2E test is available in the current environment or
  M9 should use a synthetic Telegram gateway fixture with a recorded deviation.
- Exact Application `WorkflowRun` recovery API to use after restart.
