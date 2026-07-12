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

## OQ-004: Final product profile schema

Status: open; M4 uses only a technical vertical-slice assumption
Date: 2026-07-10

Question: Which fields, taxonomies, validation rules, and onboarding UX should
define the real user profile after the M4 deterministic architecture slice?

Known facts:

- Concept and domain documents intentionally mark profile fields as requiring a
  human decision.
- M4 needs a small structured profile payload to test validation, preview,
  confirmation, safe commit, versioning, audit, and restart read-back.
- ADR-0006 accepts an M4-only technical profile shape with `user_facts`,
  `strict_restrictions`, and `soft_preferences`.
- ADR-0006 explicitly does not select final product defaults or taxonomies.

Needed decisions before relying on profile data for menu workflows:

- Required profile fields for the actual MVP.
- Meaning of people count: household size, servings, guests, or meal
  participants.
- Supported country, city, locale, currency, and timezone behavior.
- Taxonomies for strict restrictions, allergies, diets, disliked ingredients,
  cuisines, equipment, budgets, calories, macros, and stores.
- Whether and how to model temporary wishes, confidence, source attribution,
  clarification history, expiration, and unverified dialogue claims.
- User-facing confirmation TTL and confirmation copy for profile changes.

Until resolved:

- Treat ADR-0006 fields as M4 technical assumptions only.
- Do not infer user-facing product semantics from M4 fixture values.
- Do not use M4 profile shape as the final menu-generation input contract
  without a follow-up decision.

## OQ-005: Intent Router thresholds, model candidate, and adapter mapping

Status: open for production adapters; ADR-0007 selects the conservative M5
baseline and fallback policy
Date: 2026-07-11

Question: Which confidence thresholds, model-backed router candidate, and
adapter-level routing/idempotency mappings should be selected after M5 eval
evidence exists?

Known facts:

- ADR-0007 places the M5 router boundary in the application layer for
  testability and safety.
- ADR-0007 selects a deterministic rule-based baseline as the Gate M5 target.
- ADR-0007 defers model-backed routing until provider/model choice,
  credentials handling, prompt/schema versioning, and raw-output policy are
  explicitly approved.
- Self-reported confidence is not sufficient evidence for execution safety.
- The hard M5 safety gate is zero dangerous state-changing/admin false
  automatic execution on the M5 eval set.
- M5 eval selected `rule_based_baseline` / `m5.rule_based_baseline.v1` for the
  next milestone boundary with zero failures on 12 synthetic eval cases.
- M5 confidence values are diagnostic only; workflow policy remains the
  execution authority.
- M5 fallback behavior is conservative: clarify ambiguous or incomplete input,
  deny administrative input, return unsupported for unknown/deferred intents,
  and route state-changing input to confirmation policy rather than commit.

Needed decisions before production adapters:

- Whether a model-backed router candidate is needed after the M5 deterministic
  baseline, and what additional eval evidence would justify it.
- Which model/provider/version, if any, may be used for router experiments.
- Production confidence thresholds by operation class, based on larger eval
  evidence.
- Whether production fallback below threshold should stay as M5 clarify/deny/
  unsupported behavior or route to a future guided UI.
- Adapter mapping from Hermes/Telegram/HTTP metadata to router request context.
- Adapter-level idempotency key mapping for later state-changing flows.
- Raw/model output retention and sanitization policy for eval artifacts.

Until resolved:

- Keep the M5 baseline runnable without Hermes, Telegram, external providers,
  network access, or secrets.
- Do not allow confidence alone to bypass workflow policy.
- Do not connect router output to direct commit.
- Do not select production Hermes/Telegram UX or idempotency mapping from M5
  eval implementation details.

## OQ-006: Product menu semantics, model generation, and menu activation

Status: open; ADR-0008 accepts only a technical M6A one-day fake-generator
slice
Date: 2026-07-11

Question: Which product menu semantics, model-backed generation choices, and
menu activation workflow should be selected after the M6A one-day fake slice is
measured?

Known facts:

- ADR-0008 starts M6A with a one-day deterministic fake generator.
- ADR-0008 allows `PlanningContext` only from confirmed profile data, explicit
  planning request parameters, and accepted deterministic technical defaults.
- ADR-0008 treats the M4 profile shape as a technical source only, not as the
  final product menu-generation input schema.
- ADR-0008 sets the initial technical repair-loop limit to two attempts.
- ADR-0008 allows safe preview only for a validated menu draft and does not
  select menu activation or safe commit.
- ADR-0008 defers model-backed generation until provider/model, prompt/schema,
  credentials, raw-output, eval/golden, and failure-handling policies are
  explicitly approved.

Needed decisions before production menu workflows:

- Final meal slot taxonomy and whether defaults such as breakfast/lunch/dinner
  are product-wide, locale-specific, or user-configurable.
- Final menu period semantics for one day, week, and month.
- Final product profile fields that can safely drive menu generation.
- Nutrition, budget, cuisine, store, product, substitution, recipe, and
  shopping-list semantics.
- Whether and when to add a model-backed generator experiment.
- Provider/model/version and prompt/schema versioning for any model-backed
  generation.
- Raw-output retention/sanitization policy for generation artifacts.
- Menu activation confirmation lifecycle, idempotency mapping, and safe commit
  workflow.
- Future Hermes/Telegram UX for menu preview, repair, and confirmation.

Until resolved:

- Keep M6A generation deterministic, fake, one-day-first, and runnable without
  Hermes, Telegram, external providers, network access, or secrets.
- Do not infer product menu semantics from M4 profile fixtures.
- Do not activate a menu, create recipes, build shopping lists, or match store
  products from M6A draft output.
- Do not choose production model/provider or prompt policy from fake-generator
  implementation details.

## OQ-007: Recipe semantics, replacement UX, and shopping boundary

Status: open; ADR-0009 accepts only a technical M6B fake-generator and
one-slot replacement slice
Date: 2026-07-11

Question: Which product recipe semantics, replacement UX, model-backed choices,
and dependent recalculation behavior should be selected after the M6B fake
slice is measured?

Known facts:

- ADR-0009 starts M6B from an accepted menu fixture or minimal confirmed-menu
  path, not from Hermes memory or raw Telegram text.
- ADR-0009 allows recipes after an accepted or confirmed menu boundary, with
  explicit pre-generation only as a technical path for validated drafts.
- ADR-0009 keeps recipe and replacement generation deterministic, fake,
  provider-free, and side-effect free for Gate M6B.
- ADR-0009 requires replacement to change exactly one meal slot and produce a
  new menu draft/version rather than mutating the source menu in place.
- ADR-0009 requires exact replacement diff and deterministic stale
  confirmation rejection.
- ADR-0009 explicitly excludes shopping lists, store catalog, product matching,
  prices, packages, aisle data, and purchase arithmetic from M6B.

Needed decisions before production recipe/replacement workflows:

- Final recipe ingredient taxonomy.
- Final unit system and unit conversion policy.
- Final portion semantics, leftovers, and household scaling behavior.
- Final cookware/equipment taxonomy.
- Final active/total time semantics.
- Final temperature and cooking-method ontology.
- Final storage and reheating requirements.
- Recipe quality, nutrition, budget, cuisine, substitution, and product
  matching semantics.
- Replacement confirmation UX and what wording is user-facing.
- Whether replacement should invalidate, preserve, or regenerate recipe
  versions for affected slots.
- Whether and when to add a model-backed recipe/replacement experiment.
- Provider/model/version and prompt/schema versioning for any model-backed
  recipe/replacement generation.
- Raw-output retention/sanitization policy for recipe/replacement artifacts.
- Future Hermes/Telegram UX for recipe preview, replacement diff,
  confirmation, stale confirmation, and failure states.

Until resolved:

- Keep M6B recipe/replacement generation deterministic, fake, and runnable
  without Hermes, Telegram, external providers, network access, or secrets.
- Do not infer final recipe semantics from M6A technical menu fixtures.
- Do not add shopping-list, store-catalog, product-matching, price, package,
  aisle, or purchase arithmetic behavior in M6B.
- Do not choose production model/provider or prompt policy from fake-generator
  implementation details.

## OQ-008: Shopping taxonomy, catalog provider, prices, and checklist UX

Status: open; ADR-0010 accepts only a technical M7 deterministic mock-catalog
slice
Date: 2026-07-11

Question: Which product ingredient taxonomy, unit policy, catalog provider,
price/availability behavior, pantry semantics, matching UX, and checklist UX
should be selected after the M7 deterministic mock-catalog slice is measured?

Known facts:

- ADR-0010 uses confirmed menu versions, persisted recipe versions, reviewed
  mock catalog snapshots, and explicit command parameters as sources.
- ADR-0010 keeps shopping-list arithmetic code-owned and deterministic.
- ADR-0010 rejects unknown units, unsupported dimensions, incompatible
  conversions, and ambiguous product matches with controlled errors rather
  than guesses.
- ADR-0010 sets pantry and leftovers to zero by default for M7.
- ADR-0010 allows package and cost calculation only from reviewed mock
  snapshot data.
- ADR-0010 excludes real store APIs, scrapers, live prices, live availability,
  raw store HTML, Hermes/Telegram UX, and model-backed matching from M7.

Needed decisions before production shopping workflows:

- Final ingredient taxonomy and synonym policy.
- Final unit system, canonical units, density conversion, and locale-specific
  unit behavior.
- Pantry, leftovers, owned-products, expiration, and user-confirmation
  semantics.
- Real catalog provider strategy: API, manually curated catalog, scraper, or
  hybrid approach.
- Live price, availability, discounts, taxes, delivery fees, and currency
  policy.
- Product matching UX for multiple candidate products.
- Whether and when to add model-backed product matching.
- Provider/model/version and prompt/schema versioning for any model-backed
  catalog or matching experiment.
- Raw-output retention and sanitization policy for catalog/matching artifacts.
- Hermes/Telegram checklist UX, including exact item buttons,
  disambiguation, undo, and multi-user race behavior.

Until resolved:

- Keep M7 shopping-list calculation deterministic, mock-catalog-only, and
  runnable without Hermes, Telegram, external providers, network access, or
  secrets.
- Do not infer final ingredient/product semantics from M6B technical recipe
  fixtures.
- Do not fetch or parse live store pages.
- Do not let a model perform arithmetic, package calculation, price math,
  product matching, or checklist mutation.
