# Этап 10.5. Live Telegram Alpha + Interactive UX/UI Design

## 1. Цель этапа 10.5

Этап 10.5 должен превратить synthetic Telegram Alpha в наглядную live UX/UI
веху:

> Пользователь видит первую версию Telegram UX прямо в Telegram, кликает
> inline buttons, корректирует экраны по ходу создания, получает UX-советы
> при правках, а проект получает sanitized evidence реального Telegram
> round-trip.

Важно: Stage 10.5 больше не рассматривается как технический эксперимент ради
эксперимента. Это создание и согласование первого продуктового UX/UI
Menu Planner в Telegram. Sandbox остаётся безопасным способом показа и
проверки интерфейса, но пользовательский результат этапа - реальные
Telegram-экраны, навигация, кнопки и UX-решения приложения.

Главный вопрос этапа:

> Может ли пользователь быстро составить меню, точечно поправить одно блюдо и
> открыть покупки без лишних экранов, внутренних терминов и лишних
> подтверждений?

Этап 10.5 заканчивается только после live UX sandbox, пользовательского
review, внесенного или явно отложенного feedback и sanitized report. После
Stage 10.5 не переходить автоматически к MVP hardening, real store integration,
production auth, observability, backup/restore или production model rollout.

## 2. Основания

Routine Stage 10.5 tasks начинают с brief, skill и непосредственно затронутых
файлов:

- `docs/briefs/m10-5-agent-brief.md`

Полный контекст открывать только при изменении ADR/stage plan/component
boundary, Telegram/Hermes boundary или если brief недостаточен:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 10.md`
- `docs/experiments/m9-telegram-alpha.md`
- `docs/experiments/m9-telegram-capability-discovery.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0011-hermes-plugin-integration.md`
- `docs/decisions/ADR-0012-telegram-alpha.md`
- `docs/decisions/open-questions.md`

Решения из M0-M9 для этого этапа:

- Stage 10 / M9 proved only a synthetic provider-free Telegram Alpha slice.
- Live Telegram token, live Telegram network and live callback round-trip were
  not proven in M9.
- One authorized Telegram ID remains the Alpha boundary.
- Meaningful state changes require preview, stable ids, `confirmation_id`,
  expected version/hash and Application checks.
- Callback data must contain stable ids only, not full payloads.
- Telegram adapter must not import Domain Core or write Application DB.
- Demo/synthetic data may be used only if clearly labeled as demo and not
  active state.

## 3. Scope

Разрешено:

- создать Codex skill для Stage 10.5;
- принять ADR/update decision для live Telegram UX sandbox and first UI/UX
  rules, if needed;
- поднять минимальный live Telegram UX sandbox for one authorized Telegram ID;
- показать реальные alpha screens/states в Telegram;
- использовать synthetic/demo data for screens when production backend flow is
  not ready;
- clearly mark all demo/synthetic data as demo and not active state;
- make inline buttons visible and clickable in Telegram;
- показывать на кнопках понятные русские action labels, not numeric proxies,
  while keeping callback data short and stable;
- handle callbacks реально through live Telegram path;
- run UX/UI co-design loop for each major screen;
- give short UX guidance during corrections;
- prototype Telegram screens for start/home, status, profile draft/preview,
  menu draft/preview, validation warnings, confirmation, recipe view, shopping
  checklist, disambiguation, cancel, expired/stale confirmation, error and
  restart/recovery;
- evaluate Mini App tradeoffs and decide whether it belongs in Alpha;
- add user review checklists for manual Telegram verification;
- create sanitized report with shown states, feedback, accepted UX decisions
  and open questions.

Запрещено на этом этапе:

- реализовывать новые продуктовые фичи вне UX sandbox;
- переходить к MVP hardening, production auth, public registration,
  observability, backup/restore or deployment hardening;
- подключать real store integration, real prices or live availability;
- выбирать production model/provider rollout;
- читать, печатать или логировать `.env`, `auth.json`, Telegram bot token,
  credentials, private keys or private user data;
- помещать full payload, secrets or private data into callback data;
- выполнять direct Telegram commit without Application preview/confirmation
  checks;
- импортировать Domain Core directly from Telegram adapter;
- создавать or менять custom Hermes image;
- оставлять live evidence with secrets or private identifiers in reports.

## 4. Entry criteria

Перед началом Stage 10.5:

```bash
git status --short
git diff --check
scripts/dev.sh m9-telegram-alpha-e2e
docker compose ps
docker compose config
```

Проверить, что:

- `docs/experiments/m9-telegram-alpha.md` exists and records synthetic Alpha
  limitations;
- live Telegram network was not considered proven by Stage 10;
- M9 did not implement production hardening, public registration, real store
  integration or production model rollout;
- ready-made Hermes image strategy from ADR-0001 is still respected;
- no secrets are opened or printed.

Если Docker socket, live Telegram bot token or Telegram ID are needed, agent
must ask the user and must not print secrets.

## 5. Acceptance criteria

Stage 10.5 считается завершенным, если:

- Stage 10.5 Codex skill exists and was used for implementation tasks;
- `docs/briefs/m10-5-agent-brief.md` is used as primary context;
- live Telegram UX sandbox is available to one authorized Telegram ID;
- user can see the bot in Telegram;
- user can open the UX sandbox;
- user can click at least one live inline button;
- live callback reaches the sandbox and produces a visible response;
- all key states are visible in Telegram at least with demo/synthetic data;
- demo/synthetic data is clearly marked and not confused with active state;
- user-visible buttons use meaningful labels instead of bare numeric choices,
  unless a Telegram/Hermes limitation is explicitly recorded;
- food settings separate text-based food preferences from managed store price
  sources; sources are not enabled by default, are selected by the user, can be
  refreshed by schedule/manual action, and explicitly avoid live
  prices/availability on Stage 10.5;
- UX co-design loop was run for major screens;
- user gave feedback on first UI/UX version;
- feedback was applied or explicitly deferred;
- UX advice was given during corrections;
- Telegram UI principles are recorded;
- Mini App decision checkpoint is recorded;
- user review checklists are present and usable;
- callback data contains stable ids only and no full payloads;
- repeated callback does not duplicate state changes;
- no meaningful state change occurs without linked preview/confirmation;
- sanitized report contains shown states, screenshots or textual descriptions,
  accepted UX decisions and open questions;
- no new product features, hardening, real store integration, production auth
  or production model rollout were added.

## 5.1. Итог этапа 10.5

Status: completed for first-version UX/UI planning on 2026-07-13.

Accepted product UX/UI result:

- first version is a narrow Telegram Menu Planner bot, not a generic prompt
  interface;
- primary flow is lightweight: `Составить меню` -> `Меню составлено` ->
  `Главная`;
- after a menu exists, `Главная` shows current meal/recipe context,
  remaining shopping items and actions `Покупки`, `Рецепт`, `Изменить меню`,
  `Настройки`;
- `Изменить меню` is text-first and leads to a preview before any product
  save;
- settings separate food preferences from managed store price sources;
- store sources are selected by the user, not enabled all at once by default;
- with two or more selected price sources, shopping lists are grouped by
  source;
- normal menus do not include a global `Закрыть` button;
- internal terms such as draft/status/confirmation ids do not dominate the
  first-version UI.

Safety settings carried into the next stage:

- text is accepted only on explicitly text-first screens;
- text on button-only screens must be blocked inside the Menu Planner adapter
  and must not fall through to the generic Hermes agent;
- prompt-injection defenses are required before commit-capable production text
  input: classify input as user data, reject system/developer/tool/secret
  instructions, parse only narrow intent schemas, validate, show preview and
  require explicit confirmation;
- callback data must remain stable-id based and must not contain full payloads,
  private data or secrets;
- no Telegram action may commit state without Application preview,
  confirmation, version/hash checks and permission checks;
- real store integration, live prices/availability, production model rollout,
  production auth and hardening remain out of Stage 10.5.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для Stage 10.5

Цель: удержать работу в live Telegram UX sandbox, а не расползтись в hardening
or new product features.

Создать:

```text
.agents/skills/m9-live-telegram-ux-sandbox/SKILL.md
```

Skill должен требовать:

- live Telegram UX sandbox;
- user-visible screens before final implementation;
- UX co-design loop;
- UX guidance during corrections;
- user review checklists;
- sanitized evidence;
- no secrets, no production hardening, no real store integration.

Критерий завершения: skill валиден локально; проверочный prompt не требуется,
если local validation прошла.

### Шаг 2. Зафиксировать live UX sandbox strategy

Цель: определить, что именно пользователь увидит в Telegram and what remains
demo/synthetic.

Создать или обновить decision note:

```text
docs/decisions/ADR-0013-live-telegram-ux-sandbox.md
```

ADR должен зафиксировать:

- live Telegram token handling without printing secrets;
- one authorized Telegram ID policy;
- sandbox entry command/button;
- demo data labeling policy;
- callback id policy;
- screenshots/evidence sanitization policy;
- user feedback loop;
- Mini App decision checkpoint;
- what remains out of Stage 10.5.

Если нужны Telegram token, Telegram ID, Docker permission, screenshot policy or
UX preference, agent asks the user during the step.

### Шаг 3. Проверить live Telegram runtime readiness

Цель: доказать, что бот can be reached before building UX details.

Проверить:

- Hermes container status;
- Menu Planner plugin loaded or UX sandbox adapter available;
- Telegram Gateway configured with token/allowlist without printing values;
- one authorized user can receive a basic live response.

Критерий завершения:

- user sees a live Telegram response;
- evidence is sanitized;
- failures are recorded honestly.

### Шаг 4. Build Live Telegram UX Sandbox shell

Цель: создать безопасную песочницу экранов, separate from active business
state.

Sandbox must:

- open from a command or button;
- show that data is demo/synthetic unless connected to active backend state;
- provide navigation between prototype states;
- expose inline buttons and callback handling;
- avoid full payload callback data.

Критерий завершения:

- user can open sandbox in Telegram;
- user can navigate between at least start/home and status;
- callback round-trip is visible.

### Шаг 5. Run UX/UI co-design loop for core screens

For each major screen:

1. Show current version in Telegram.
2. Explain UX logic briefly.
3. Suggest 1-3 improvements.
4. Ask user what to change.
5. Apply or explicitly defer feedback.
6. Show updated version in Telegram.

Screens:

- home without menu / quick start;
- home with active menu;
- generated menu preview;
- text-first menu edit;
- menu edit preview;
- shopping list;
- food settings;
- recipe card;
- settings text-edit help;
- accepted/done state;
- short error/recovery state.

UX principle for this revision:

- do not expose internal terms such as draft, workflow status,
  `confirmation_id` or stale confirmation in the primary path;
- show useful output first, then offer only the next natural actions;
- make the home screen state-aware: before menu generation it starts planning;
  after menu generation it shows remaining shopping items and the current meal
  recipe, and the primary action changes from `Составить меню` to
  `Изменить меню`;
- keep the primary menu flow to the fewest taps possible.

Критерий завершения:

- every screen was shown or explicitly deferred with reason;
- user feedback is recorded;
- accepted changes are reflected in sandbox.

### Шаг 6. Give UX guidance during corrections

During corrections, agent should give short advice on:

- free text vs inline buttons;
- button-only dangerous actions;
- preview placement;
- confirmation wording;
- disambiguation;
- long text splitting;
- avoiding Telegram text walls;
- Mini App opportunities;
- why Mini App may be premature for Alpha.

Критерий завершения:

- report includes UX advice given and accepted/rejected decisions.

### Шаг 7. Record Telegram UI principles

Зафиксировать:

- every state-changing action requires preview/confirmation;
- the preview screen itself may contain the accept button; do not add a second
  confirmation step when the action is already clear;
- internal draft/active mechanics must not dominate the user-visible copy;
- confirmation buttons still link to stable ids internally, but those ids are
  not shown in the lightweight UX;
- callback data contains no full payload;
- destructive/cancel actions require explicit buttons only when there is a real
  destructive action; do not add cancel confirmation to harmless navigation;
- shopping checklist updates use stable item id;
- ambiguous text routes to disambiguation screen;
- text-based settings input is untrusted user input; it must be parsed into a
  narrow settings/change-intent schema and must not be treated as system,
  developer, tool or policy instructions;
- in the UX sandbox, text typed from settings/settings-edit returns to the
  settings screen with a demo notice; it must not fall through to the generic
  Hermes agent;
- the bot is narrow-purpose: inline menus must not include a global `Закрыть`
  action just because this is a demo; navigation should stay inside Menu
  Planner states;
- free text is accepted only on explicitly text-first screens such as food
  settings and menu editing; on button-only screens it must be blocked inside
  the Menu Planner adapter and must not fall through to the generic Hermes
  agent;
- text-first screens require prompt-injection defenses before production use:
  classify text as user data, reject system/developer/tool/secret-seeking
  instructions, parse only a narrow intent schema, validate, show preview and
  require explicit confirmation before commit;
- text settings must not directly commit: they require validation, preview and
  explicit accept/confirmation before changing saved state;
- long preview/diff is split or summarized.

Критерий завершения:

- principles appear in ADR/report;
- screens follow or explicitly deviate from them.

### Шаг 8. Mini App decision checkpoint

Оценить:

- what is awkward in chat-only UI;
- which screens might benefit from Telegram Mini App;
- what can remain inline buttons;
- whether Mini App belongs in Alpha or should be deferred;
- risks: auth, state sync, callbacks, hosting, testing.

Критерий завершения:

- Mini App decision is recorded as accepted/deferred with reasons.

### Шаг 9. Add user review checklists

Добавить checklists for manual Telegram verification:

- first launch checklist;
- profile setup checklist;
- menu preview checklist;
- confirmation checklist;
- recipe view checklist;
- shopping checklist checklist;
- disambiguation checklist;
- repeated click checklist;
- cancel/error checklist;
- restart/recovery checklist;
- "draft vs active is clear" checklist.

Критерий завершения:

- checklists are in report or runbook;
- user can use them while clicking the live bot.

### Шаг 10. Reality gate and report

Создать:

```text
docs/experiments/m9-live-telegram-ux-sandbox.md
```

Report должен содержать:

- goal;
- live Telegram setup evidence, sanitized;
- shown screens with screenshots or textual descriptions;
- user feedback;
- applied and deferred changes;
- UX advice decisions;
- Mini App decision;
- user review checklist results;
- callback smoke result;
- repeated callback result;
- what was intentionally not implemented;
- Gate Stage 10.5 result.

Stage 10.5 cannot be closed until:

- user sees the bot in Telegram;
- user opens UX sandbox;
- user clicks inline buttons;
- all key states were shown at least on demo/synthetic data;
- user gave UI/UX feedback;
- feedback was applied or explicitly deferred;
- sanitized report exists;
- accepted UX decisions and open questions are listed.

## 7. User review checklists

Заполнить during live review:

```markdown
## User Review Checklists

### First Launch

[ ] Bot responds to my message.
[ ] I can open the UX sandbox.
[ ] I understand this is Alpha/demo when demo data is shown.

### Profile Setup

[ ] Profile draft screen is understandable.
[ ] Profile preview is not confused with active profile.
[ ] Confirmation action is clearly separated.

### Menu Preview

[ ] Menu draft is labeled as draft.
[ ] Menu preview is readable without a wall of text.
[ ] I understand what will change if I confirm.

### Confirmation

[ ] Confirmation uses a button.
[ ] Confirmation is tied to a specific preview/version.
[ ] Expired/stale confirmation is explained clearly.

### Recipe View

[ ] Recipe screen is readable in Telegram.
[ ] Long recipe content is split or summarized well.
[ ] Navigation back/status is clear.

### Shopping Checklist

[ ] Items are easy to scan.
[ ] Bought/not bought action is clear.
[ ] Repeated click does not create confusion.

### Disambiguation

[ ] Ambiguous text shows choices.
[ ] I understand why the bot asks me to choose.
[ ] Buttons are preferable to guessing.

### Exit/Error

[ ] No global close button clutters normal menus.
[ ] Destructive cancel exists only where there is something to discard.
[ ] Error messages are understandable.
[ ] The bot tells me what I can do next.

### Restart/Recovery

[ ] After restart/recovery, the bot explains current state.
[ ] I can continue or cancel.

### Draft vs Active

[ ] I can tell what is draft.
[ ] I can tell what is active.
[ ] No screen implies a draft is already committed.
```

## 8. Gate Stage 10.5 checklist

```markdown
## Gate Stage 10.5 Checklist

[ ] Stage 10.5 skill exists and was used.
[ ] Stage 10.5 brief exists and was used.
[ ] Live Telegram UX sandbox strategy is recorded.
[ ] User sees the bot in Telegram.
[ ] User can open the UX sandbox.
[ ] User can click a live inline button.
[ ] Callback reaches sandbox and returns visible response.
[ ] All key screens are shown or explicitly deferred.
[ ] Demo/synthetic data is labeled as demo.
[ ] User feedback was collected.
[ ] Feedback was applied or explicitly deferred.
[ ] UX advice was given during corrections.
[ ] Telegram UI principles are recorded.
[ ] Mini App decision checkpoint is recorded.
[ ] User review checklists are present.
[ ] Callback data contains stable ids only.
[ ] Repeated callback does not duplicate state changes.
[ ] No new product feature outside UX sandbox was added.
[ ] No production hardening, real store integration, production auth or
    production model rollout was added.
[ ] No secrets are printed in logs/reports/diffs.
[ ] `git diff --check` passed.
```

## 9. Sequence of tasks for Codex

Использовать по одному шагу за запрос. Для каждого шага:

1. Прочитать active Stage 10.5 skill and
   `docs/briefs/m10-5-agent-brief.md`.
2. Проверить фактическое состояние файлов и `git status --short`.
3. Сформулировать acceptance criteria для текущего шага.
4. Если нужен Telegram token, Telegram ID, Docker socket or UX decision,
   спросить пользователя до изменения or live action.
5. Если вопрос не блокирует текущий minimal slice, зафиксировать assumption or
   open question.
6. Сделать минимальное изменение.
7. Показать результат пользователю в Telegram when the step is UX-visible.
8. Запустить relevant targeted checks.
9. Запустить `git diff --check`.
10. Сообщить changed files, commands, passed/skipped checks, assumptions and
    remaining decisions.

Не выполнять следующий шаг самостоятельно без отдельного задания пользователя.
