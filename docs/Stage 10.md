# Этап 10. M9 Telegram Alpha for one authorized user

## 1. Цель этапа 10

Этап 10 должен довести проект до ближайшей рефлексивной вехи M9:

> Один авторизованный пользователь проходит основной сценарий через Telegram,
> при этом ни одно значимое изменение не происходит без связанного preview,
> `confirmation_id`, expected version and Application/Domain checks.

Главный вопрос этапа:

> Безопасен ли UX свободного текста и callbacks: где текст удобен, где нужны
> кнопки, что происходит при параллельных сообщениях, и понимает ли
> пользователь разницу между draft and active state?

Этап 10 заканчивается на Gate M9 и рефлексии M9. После Gate M9 не переходить
автоматически к MVP hardening, production deployment, real store integration,
multi-user auth или observability/backup work без отдельного задания.

## 2. Основания

Routine M9 tasks начинают с brief, skill и непосредственно затронутых файлов:

- `docs/briefs/m10-agent-brief.md`

Полный контекст открывать только при изменении ADR/stage plan/component
boundary, Telegram/Hermes boundary или если brief недостаточен:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 9.md`
- `docs/experiments/m8-hermes-plugin-integration.md`
- `docs/experiments/m8-hermes-runtime-api-discovery.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0011-hermes-plugin-integration.md`
- `docs/decisions/open-questions.md`

Решения из M0-M8 для этого этапа:

- Hermes runs from the ready-made Docker image through Docker Compose.
- Domain Core remains independent from Hermes and Telegram.
- Telegram Gateway receives messages, sends responses, identifies user, binds
  session and handles transport limits, but does not own business validation or
  commit.
- Hermes plugin/tools call Application HTTP API and do not import Domain Core.
- Free text becomes structured intent, policy decision, restricted toolset and
  domain validation before state-changing action.
- Read-only operations may run without confirmation.
- Generative operations create drafts.
- Meaningful confirmed-state changes require preview and confirmation.
- Commit is tied to concrete version and `confirmation_id`.
- Checklist status changes require exact `shopping_item_id` or disambiguated
  structured action.
- M8 stops before Telegram Alpha, inline buttons, callbacks or production
  Telegram UX.

## 3. Scope

Разрешено:

- создать Codex skill для M9;
- принять ADR для Telegram Alpha UX, allowlist, session binding, callbacks,
  confirmation binding, parallel-message policy, restart recovery and E2E
  scenarios;
- включить allowlist одного Telegram ID;
- связать Telegram user/session with `user_id` and `WorkflowRun`;
- ограничить message size and rate limit;
- normalize dates relative to user's timezone;
- реализовать presentation layer for clarification, preview, validation
  warnings, status, errors, cancel, recipe view and shopping checklist;
- проверить inline buttons/callbacks установленной версии Hermes;
- связать callback with `confirmation_id`, stable `shopping_item_id` or stable
  action id, not raw full payload;
- защитить repeated callback;
- определить and implement parallel-message policy: per-user queue or explicit
  rejection of conflicting action;
- restore active workflow after restart;
- добавить Telegram E2E alpha scenarios for profile, menu, revision, confirm,
  recipe view, shopping checklist, cancel and expired confirmation;
- заполнить M9 report and reflection.

Запрещено на этом этапе:

- реализовывать public registration or multi-user production auth;
- делать production dashboard auth replacement, backup/restore, alerting,
  observability hardening or deployment hardening;
- подключать real store API, scraper, live prices or availability;
- читать, печатать или логировать `.env`, `auth.json`, tokens or credentials;
- помещать full operation payload, secrets or private data into callback data;
- связывать callback with display text like "yes" instead of stable id;
- выполнять commit from free text or callback without Application
  confirmation/version/hash checks;
- позволять Telegram adapter directly write Application DB;
- импортировать Domain Core directly from Telegram adapter;
- давать user Telegram session administrative tools;
- выбирать production cloud/local model provider без отдельного решения;
- создавать or менять custom Hermes image;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 10:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m8-fake-integration
docker compose ps
docker compose config
```

Проверить, что:

- Gate M8 функционально закрыт или явно отложен человеком;
- `docs/experiments/m8-hermes-plugin-integration.md` exists and is filled;
- ADR-0011 accepted;
- Hermes plugin boundary, tools, hooks, toolsets and fake workflow work without
  Telegram Alpha;
- M8 did not implement Telegram production UX, real store integration or
  production model rollout;
- ready-made Hermes image strategy from ADR-0001 is still respected;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты.

Если Docker socket access нужен для Hermes/Telegram checks, агент должен
запросить разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 10 считается завершенным, если:

- M9 Codex skill exists and helps keep tasks inside Telegram Alpha boundary;
- `docs/briefs/m10-agent-brief.md` is used as primary context for routine
  tasks;
- ADR-0012 or equivalent decision note fixes Telegram Alpha UX, allowlist,
  session binding, callbacks, confirmation binding, parallel-message policy,
  restart recovery and E2E scope;
- exactly one authorized Telegram ID is allowed for alpha;
- Telegram user/session is bound to `user_id` and `WorkflowRun`;
- message size and rate limit behavior is deterministic;
- dates are normalized relative to user timezone;
- presentation layer supports clarification, preview, validation warnings,
  status, errors, cancel, recipe view and shopping checklist;
- inline button/callback support for installed Hermes version is verified or
  skipped with recorded reason;
- callbacks reference `confirmation_id` or stable item/action ids, not full
  payloads;
- repeated callback is rejected or idempotently handled;
- parallel-message behavior is queue or explicit conflict rejection;
- active workflow can recover after restart or limitation is recorded;
- E2E alpha scenario passes for profile, menu, revision, confirm, recipe view,
  shopping checklist, cancel and expired confirmation, or deviations are
  recorded;
- no meaningful state change occurs without linked preview/confirmation;
- Domain Core still has no Hermes, Telegram, ORM, HTTP client or model SDK
  imports;
- Telegram adapter/plugin does not write Application DB directly;
- no public registration, real store integration, production hardening or
  production model rollout was added;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke`, Telegram E2E alpha command and `git diff --check`
  pass or deviations are explicitly recorded;
- создан `docs/experiments/m9-telegram-alpha.md` с результатом Gate M9 and
  reflection.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M9

Цель: не дать Stage 10 расползтись в production hardening, real store
integration, multi-user auth, broad admin UX or direct Telegram commits.

Создать:

```text
.agents/skills/m9-telegram-alpha/SKILL.md
```

Содержимое:

```markdown
---
name: m9-telegram-alpha
description: "Use when building the Menu Planner M9 Telegram Alpha slice: one authorized Telegram ID, Telegram user/session binding to user_id and WorkflowRun, message size and rate limits, timezone normalization, presentation layer for clarification/preview/warnings/status/errors/cancel/recipe view/shopping checklist, inline button and callback capability checks, confirmation_id-bound callbacks, repeated callback protection, parallel-message policy, restart recovery, Telegram E2E alpha scenarios, and M9 report, without public registration, multi-user production auth, real store integration, production hardening, direct Telegram commits, full payload callback data, or production model rollout."
---

# M9 Telegram Alpha workflow

## Scope

- Build only one-user Telegram Alpha up to Gate M9.
- Add or refine allowlist, session binding, message/rate limits, timezone
  normalization, presentation layer, callbacks, repeated callback protection,
  parallel-message policy, restart recovery, E2E alpha scenarios, and M9
  report.
- Use Hermes Telegram Gateway and existing Hermes plugin/Application API
  boundary.
- Do not implement public registration, multi-user production auth, real store
  integration, production hardening, direct Telegram commits, full payload
  callback data, or production model rollout.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m10-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
Telegram/Hermes boundary, Docker/runtime configuration, or when the brief is
insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 10.md`
- `docs/experiments/m8-hermes-plugin-integration.md`
- `docs/experiments/m8-hermes-runtime-api-discovery.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0011-hermes-plugin-integration.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation and actual Hermes/Telegram capability before
   editing Telegram integration code.
3. If allowlist source, Telegram ID handling, callback support, callback data
   shape, confirmation binding, parallel-message policy, timezone policy,
   restart recovery or E2E test surface is blocking, ask the user during that
   step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and verified Hermes image behavior.
6. Add the smallest testable change.
7. Run targeted presentation/session/callback tests first.
8. Run Telegram E2E alpha checks when the task changes gateway, callback,
   workflow recovery or user-facing flow behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine presentation, callback,
  fixture, or E2E-test changes when the brief and affected files are
  sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Free text never commits state directly.
- Meaningful changes require preview and confirmation tied to version and
  `confirmation_id`.
- Callback data must carry stable ids only, not full operation payloads.
- Repeated and stale callbacks must not duplicate state changes.
- Ambiguous text requires clarification or disambiguation.
- Telegram adapter does not import Domain Core or write Application DB.
- Keep public registration, multi-user production auth, real store integration
  and hardening out of M9.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
```

Критерий завершения: skill валиден локально; проверочный prompt не требуется,
если local validation прошла.

### Шаг 2. Зафиксировать Telegram Alpha strategy

Цель: не смешать alpha UX, production auth, callbacks, confirmation,
parallel messages and hardening в одну непроверяемую реализацию.

Создать:

```text
docs/decisions/ADR-0012-telegram-alpha.md
```

ADR должен зафиксировать:

- one-user allowlist policy;
- source of Telegram ID configuration without exposing secrets;
- mapping Telegram user/session to `user_id` and `WorkflowRun`;
- message size and rate-limit policy;
- timezone normalization policy;
- presentation-layer scope;
- inline button/callback support evidence;
- callback data shape and size policy;
- confirmation binding policy;
- repeated callback behavior;
- parallel-message policy: queue or explicit conflict rejection;
- restart recovery policy;
- Telegram E2E alpha scope;
- what remains out of M9.

Если нужны решения по Telegram ID, callback support, callback payload shape,
parallel-message policy, timezone, restart recovery or E2E surface, агент
задает вопрос пользователю. Если выбор не блокирует discovery or documentation
slice, агент фиксирует technical assumption and open question.

Критерий завершения:

- ADR-0012 принят;
- no public registration, production auth or production hardening hidden in
  Telegram Alpha;
- M9 can be verified with one authorized user/synthetic Telegram gateway path;
- unresolved UX/security decisions перенесены в
  `docs/decisions/open-questions.md`.

### Шаг 3. Inspect installed Hermes Telegram capability

Цель: не реализовывать callbacks or gateway behavior by analogy.

Проверить локально:

- Hermes image/version from current compose setup;
- Telegram Gateway configuration surface;
- inline button/callback support in installed version;
- callback data limits and handler semantics, if discoverable;
- session/user identity surfaces;
- safe way to run synthetic Telegram E2E without real token, if available.

Запрещено:

- read or print real Telegram token;
- mutate Hermes image or install packages in container;
- edit files inside running container;
- use `docker cp` to install code.

Критерий завершения:

- evidence recorded in ADR/report or experiment note;
- callback support verified or skipped with reason;
- no secrets printed;
- unknown API details remain explicit open questions.

### Шаг 4. Implement one-user allowlist and session binding

Цель: Telegram Alpha is private and maps every message to application identity.

Реализовать:

- one allowed Telegram ID source without logging the secret/private value;
- mapping Telegram user/session to `user_id`;
- binding to `WorkflowRun`;
- structured rejection for unknown user/session.

Критерий завершения:

- allowed user path covered;
- disallowed user path covered;
- user/session mismatch cannot access another workflow.

### Шаг 5. Add message size, rate limit and timezone normalization

Цель: inbound text is bounded and dates are deterministic.

Реализовать:

- max message size;
- rate-limit or conflict placeholder from ADR-0012;
- timezone source for the alpha user;
- date normalization relative to timezone;
- controlled errors for invalid dates/timezone.

Критерий завершения:

- oversized message rejected before tool workflow;
- rate/concurrency behavior deterministic;
- date fixtures normalize predictably.

### Шаг 6. Implement presentation layer

Цель: domain/tool results become clear Telegram responses without moving
business rules into UI text.

Presentation layer covers:

- clarification;
- preview;
- validation warnings;
- status;
- errors;
- cancel;
- recipe view;
- shopping checklist.

Критерий завершения:

- each presentation type has tests/fixtures;
- text distinguishes draft from active state;
- sensitive payloads and secrets are not displayed.

### Шаг 7. Implement confirmation-bound callbacks

Цель: buttons/callbacks must identify exact operation, not rely on displayed
text.

Callbacks must:

- link confirmation actions to `confirmation_id`;
- include expected version/hash reference where required;
- avoid full operation payload in callback data;
- reject expired/stale/missing confirmation;
- not commit without Application checks.

Критерий завершения:

- valid confirmation callback path covered;
- stale/expired callback rejected;
- callback data remains bounded and non-secret.

### Шаг 8. Implement checklist callbacks and text disambiguation

Цель: shopping checklist state changes target exact item identity.

Реализовать:

- callback for concrete `shopping_item_id`;
- repeated item callback behavior from ADR-0012;
- text "milk bought" path only when one deterministic match exists;
- disambiguation prompt when multiple matches exist.

Критерий завершения:

- exact item callback covered;
- repeated callback covered;
- ambiguous text does not mutate state.

### Шаг 9. Implement cancel, errors and expired confirmation UX

Цель: user can recover from alpha workflow failures.

Добавить:

- cancel workflow action;
- expired confirmation message;
- validation error rendering;
- policy/permission error rendering;
- retry or next-action hints from structured tool results.

Критерий завершения:

- cancel is test-covered;
- expired confirmation is test-covered;
- errors do not expose raw exception/secret data.

### Шаг 10. Define and implement parallel-message policy

Цель: two quick messages cannot corrupt workflow state.

ADR-0012 must choose one:

- sequential per-user queue; or
- explicit rejection of conflicting action while workflow step is active.

Реализовать chosen policy for:

- two text messages;
- callback while prior action is active;
- duplicate callback/retry.

Критерий завершения:

- concurrent/conflicting message test covered;
- state remains unchanged or changes exactly once;
- user-facing response explains what happened.

### Шаг 11. Restore active workflow after restart

Цель: alpha user is not stranded after container/process restart.

Реализовать or document limitation for:

- reload active `WorkflowRun`;
- reload pending confirmation;
- reconstruct allowed actions;
- resume/cancel response.

Критерий завершения:

- restart recovery test or documented limitation exists;
- memory is not source of truth;
- stale in-memory state cannot commit.

### Шаг 12. Add Telegram E2E alpha scenarios

Цель: Gate M9 should prove a real user-shaped flow, not only unit tests.

Scenarios:

- create/update profile;
- generate menu or accepted menu path;
- revision;
- confirm;
- recipe view;
- shopping checklist;
- cancel;
- expired confirmation.

Use synthetic gateway/test harness where possible. If real Telegram token is
required, agent must ask user and must not print the token.

Критерий завершения:

- E2E alpha command exists or skipped with recorded reason;
- no meaningful state change occurs without linked preview/confirmation;
- transcript/report contains no secrets.

### Шаг 13. Заполнить M9 report and reflection

Цель: остановиться на Gate M9, а не перейти автоматически в hardening.

Создать:

```text
docs/experiments/m9-telegram-alpha.md
```

Report должен содержать:

- цель;
- scope;
- Telegram/Hermes capability evidence;
- allowlist/session decisions;
- presentation/callback decisions;
- parallel-message policy;
- restart recovery status;
- commands run;
- E2E metrics;
- what was intentionally not implemented;
- Gate M9 result;
- reflection;
- decisions before MVP hardening.

Критерий завершения:

- Gate M9 checklist заполнен;
- remaining assumptions listed;
- relevant questions copied to `docs/decisions/open-questions.md`;
- в отчете явно сказано: не переходить к MVP hardening/production work без
  отдельного задания.

## 7. Gate M9 checklist

Заполнить в `docs/experiments/m9-telegram-alpha.md`:

```markdown
## Gate M9 Checklist

[ ] M9 Codex skill exists and was used for implementation tasks.
[ ] M9 brief exists and was used for routine tasks.
[ ] ADR-0012 or equivalent decision note fixes Telegram Alpha strategy.
[ ] Installed Hermes Telegram/callback capability was inspected and recorded.
[ ] Exactly one authorized Telegram ID is allowed for alpha.
[ ] Telegram user/session maps to `user_id` and `WorkflowRun`.
[ ] Message size limit is enforced.
[ ] Rate/concurrency policy is deterministic.
[ ] Dates are normalized relative to user timezone.
[ ] Presentation layer covers clarification, preview, warnings, status, errors,
    cancel, recipe view and shopping checklist.
[ ] Callback data references stable ids and not full operation payloads.
[ ] Confirmation callbacks bind to `confirmation_id` and expected version/hash.
[ ] Expired/stale confirmations are rejected.
[ ] Repeated callbacks do not duplicate state changes.
[ ] Parallel messages are queued or rejected according to ADR-0012.
[ ] Active workflow restart recovery works or limitation is recorded.
[ ] Telegram E2E alpha covers profile, menu, revision, confirm, recipe view,
    shopping checklist, cancel and expired confirmation, or deviations are
    recorded.
[ ] No meaningful state change occurs without linked preview/confirmation.
[ ] Telegram adapter does not import Domain Core or write Application DB.
[ ] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[ ] No public registration, multi-user production auth, real store integration,
    production hardening or production model rollout added.
[ ] `scripts/dev.sh test` passed or deviation recorded.
[ ] `scripts/dev.sh lint` passed or deviation recorded.
[ ] `scripts/dev.sh typecheck` passed or deviation recorded.
[ ] `scripts/dev.sh smoke` passed or deviation recorded.
[ ] Telegram E2E alpha command passed or skipped with reason.
[ ] `git diff --check` passed.
```

## 8. Reflection M9

Заполнить после Gate M9:

```markdown
## Reflection M9

### Где свободный текст удобен, а где создает лишнюю неоднозначность?

- [ответ]

### Какие действия должны остаться только кнопками?

- [ответ]

### Что происходит при двух быстрых сообщениях?

- [ответ]

### Понимает ли пользователь, что является draft, а что active?

- [ответ]

### Какие решения нужны перед MVP hardening?

- [ответ]
```

## 9. Sequence of tasks for Codex

Использовать по одному шагу за запрос. Для каждого шага:

1. Прочитать active M9 skill and `docs/briefs/m10-agent-brief.md`.
2. Проверить фактическое состояние файлов и `git status --short`.
3. Сформулировать acceptance criteria для текущего шага.
4. Если появляется blocking question, задать его пользователю до изменения.
5. Если вопрос не блокирует текущий minimal slice, зафиксировать assumption или
   open question.
6. Сделать минимальное изменение.
7. Запустить relevant targeted checks.
8. Запустить `git diff --check`.
9. Сообщить changed files, commands, passed/skipped checks, assumptions and
   remaining decisions.

Не выполнять следующий шаг самостоятельно без отдельного задания пользователя.
