# Open Questions

## OQ-001: Hermes OpenAI access through Codex authorization

Status: partially resolved by ADR-0001; local models deferred, production
provider/model matrix still pending
Date: 2026-07-08

Question: How should this repository reproduce and configure the ready-made
Hermes image's Codex authorization capability while preserving the option to
switch later to direct OpenAI API keys or other model providers?

Known facts:

- Codex can authenticate to OpenAI via ChatGPT sign-in or API-key sign-in.
- Codex state is rooted at `CODEX_HOME`; file-based credentials live in
  `$CODEX_HOME/auth.json`.
- `auth.json`, `CODEX_ACCESS_TOKEN`, and real API key values are secrets and
  must not be committed or displayed.
- `.env.example` may contain empty placeholders such as `OPENAI_API_KEY=` for
  provider switching; local `.env` contains real values when that provider is
  selected.
- This repository now records local non-secret image/source evidence and a
  startup wrapper.
- On 2026-07-08, the local Hermes container reported
  `openai-codex: logged in`.
- A Hermes one-shot model smoke using the configured defaults returned
  `stage0-model-ok`.
- Sanitized config output showed managed config keys `model.default`,
  `model.provider`, and `plugins.enabled`; the observed current model settings
  were `provider=openai-codex` and `default=gpt-5.4-mini`.
- Older gateway logs showed `BadRequestError` for other model IDs when used
  through ChatGPT-backed Codex. This is a model-selection issue, not an auth
  failure.

Decision:

- ADR-0001 defers local models to a later stage.
- Immediate post-Stage-0 work may use the verified cloud-capable Hermes
  provider path for capability and integration work.
- The passing `openai-codex` smoke test does not select a production model or
  final provider matrix.

Needed evidence:

- Which Hermes configuration selects between Codex-backed OpenAI access, direct
  OpenAI API key access, Anthropic, and future local providers.
- Which concrete model IDs are supported by the selected ChatGPT-backed Codex
  account and should be allowed in this project.

Until resolved:

- Do not mount `~/.codex` or any `auth.json` into the Hermes container except
  as an explicit, documented capability-spike step with user approval.
- Keep provider credentials in `.env.example` as empty placeholders only.
- Keep provider/model switching as an explicit configuration decision; do not
  infer a production model from a passing Stage 0 smoke test.

## OQ-002: Dashboard role in the target Hermes deployment

Status: resolved by ADR-0001 for direction; exact production-grade auth
provider pending later selection
Date: 2026-07-08

Question: Should the Hermes dashboard remain part of the normal Menu Planner
deployment, and how should it be gated relative to Codex device-code
authorization?

Assessment:

- The dashboard is not required for the domain core itself. Profile, menu,
  recipe, shopping-list, validation, confirmation, commit, versioning, and
  idempotency must live outside Hermes dashboard concerns.
- The dashboard is relevant to Stage 0 and operations because it exposes actual
  Hermes runtime behavior: provider/auth status, sessions, logs, tools,
  plugins, skills, MCP, and gateway state.
- The project goal is to use Hermes as the main agent runtime, not merely to run
  a foreground `gateway run` process. Disabling the dashboard by bypassing the
  image entrypoint hides part of the runtime surface that Stage 0 is supposed
  to investigate.
- Dashboard security matters. Binding the dashboard to `0.0.0.0` without a
  registered dashboard auth provider is rejected by Hermes itself. Passing
  `--insecure` is not a suitable target solution on an untrusted network.
- The selected Stage 0 approach is to keep the normal image entrypoint and s6
  dashboard service, bind dashboard to `0.0.0.0`, publish port `9119`, and
  enable the bundled `dashboard_auth/basic` provider through a read-only
  managed config bind mount.
- Hermes v0.17 makes bundled plugins opt-in through `plugins.enabled`, so
  passing `HERMES_DASHBOARD_BASIC_AUTH_*` alone is not enough. The provider must
  also be enabled before the s6 dashboard service starts.
- The startup problem is sequencing: Codex device-code auth should complete
  before dashboard/gateway services produce unrelated errors. The target
  solution should preserve dashboard availability after auth, not remove it.

Rejected target approach:

- Replacing the image entrypoint with a foreground shell wrapper solely to stop
  s6/dashboard log noise. This is acceptable only as a short diagnostic
  experiment and must not be treated as the target project configuration
  without explicit user approval.

Selected target direction for Stage 0:

- Keeping the normal image entrypoint for the main Hermes service so bundled
  services, including dashboard, remain observable.
- Exposing dashboard through the published `9119` port with the bundled
  `dashboard_auth/basic` provider enabled and configured.
- A one-shot Codex auth bootstrap step/service that shares the Hermes data
  volume remains a possible later improvement if gateway/dashboard sequencing
  needs to be stricter.

Decision:

- ADR-0001 keeps the dashboard available for development and operations.
- Current basic auth is temporary for Stage 0/dev use.
- Before production exposure, dashboard authentication must be replaced with a
  more production-grade mechanism.

Follow-up:

- Select the concrete production-grade dashboard auth mechanism before
  production exposure, for example a stronger Hermes auth provider, OAuth,
  reverse proxy auth, or another approved mechanism.

## OQ-003: Telegram inline callback support for confirmations

Status: resolved for preferred direction by ADR-0001; live Menu Planner
confirmation round-trip still pending
Date: 2026-07-08

Question: Does the installed Hermes Telegram Gateway expose inline buttons,
callback data, and Telegram user IDs to plugins in a way that can support Menu
Planner confirmation flows?

Known facts:

- Hermes v0.17 gateway setup exposes Telegram through `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_ALLOWED_USERS`, and `TELEGRAM_HOME_CHANNEL`.
- Hermes command registration can surface plugin slash commands and skills in
  Telegram bot menus.
- The current local container has `TELEGRAM_BOT_TOKEN` and
  `TELEGRAM_ALLOWED_USERS` set. `TELEGRAM_HOME_CHANNEL` is optional and was not
  set during the check.
- `hermes send --quiet --to telegram:<allowed-user>` returned
  `telegram_send=pass` without printing the chat ID.
- Source search in `/opt/hermes/gateway/platforms/telegram.py` found
  `CallbackQueryHandler`, `InlineKeyboardButton`, and `InlineKeyboardMarkup`.
- Telegram callback handling includes built-in namespaces:
  - `ea:*` for exec approval;
  - `sc:*` for slash confirmation;
  - `cl:*` for clarify choices;
  - `mp:*`, `mm:*`, and related prefixes for model picker callbacks.
- The callback handler checks authorization using `query.from_user.id` plus
  chat/thread context before resolving approval, slash-confirm, or clarify
  state.
- No generic project/plugin-owned callback namespace was found for arbitrary
  Menu Planner payloads.

Decision:

- ADR-0001 selects Hermes built-in slash confirmation callbacks, the `sc:*`
  flow, as the preferred Menu Planner confirmation mechanism.
- Domain `confirmation_id` remains application-owned.
- Telegram callbacks must route through Domain Core confirmation checks and
  must not commit state directly.

Needed evidence:

- A live Telegram button tap for the chosen experiment, proving which user ID,
  chat ID, message ID, thread ID, and callback payload are available at the
  application boundary.
- Whether a Menu Planner `confirmation_id` can be round-tripped without
  bypassing domain confirmation rules.

Until resolved:

- Do not assume arbitrary plugin-owned Telegram callback payloads are available.
- Keep domain confirmation IDs application-owned and independent of Hermes
  internal session or turn IDs.
