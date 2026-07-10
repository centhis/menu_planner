# Этап 4. M4 profile vertical slice: первый бизнес-сценарий без LLM

## 1. Цель этапа 4

Этап 4 должен довести проект до вехи M4:

> ProfileDraft проходит полный путь через validation, preview, persistent
> Confirmation, safe commit, versioning, audit и read-back после restart без
> Hermes business adapter, Telegram UX, Intent Router и LLM.

Главный вопрос этапа:

> Правильна ли архитектура Domain/Application/Infrastructure на первом
> реальном пользовательском сценарии, если убрать вероятностные компоненты?

Этап 4 заканчивается на Gate M4 и рефлексии M4. После Gate M4 не переходить
автоматически к M5 Intent Router, LLM evals, Hermes plugin или Telegram UX без
отдельного задания.

## 2. Основания

Перед работой учитывать:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 3.md`
- `docs/experiments/m3-safe-commit.md`
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md`
- `docs/decisions/ADR-0002-application-runtime.md`
- `docs/decisions/ADR-0003-post-m1-runtime-boundaries.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/open-questions.md`

Решения из M0-M3 для этого этапа:

- Domain Core не импортирует Hermes, Telegram, ORM, HTTP clients или model SDK.
- Application service владеет PostgreSQL schema, migrations, repositories и
  transaction boundary.
- Hermes plugin/tools позже будут только adapter layer к Application HTTP API.
- M3 generic safe commit primitives считаются достаточной основой для M4, если
  M4 мапит profile drafts и committed profile versions на тот же
  preview-confirm-commit flow.
- Подтвержденное состояние не хранится только в Hermes runtime state.
- User-facing confirmation TTL, profile draft shape, HTTP/API mapping и
  adapter-level idempotency key source остаются решениями M4/M9, если они
  блокируют конкретный шаг.

## 3. Scope

Разрешено:

- создать Codex skill для M4;
- принять ADR или короткую decision note по минимальной форме profile vertical
  slice, если существующих решений недостаточно;
- уточнить `ProfileDraft` и `ProfileVersion` в рамках минимального M4 сценария;
- добавить profile validation и machine-readable ошибки;
- связать profile workflow с M2 state machine/policy для минимального
  сценария;
- добавить profile-specific application commands и queries;
- добавить migrations/tables только для M4 profile state, если они нужны;
- переиспользовать M3 preview, confirmation, idempotency, versioning и audit;
- добавить временный CLI или test API для детерминированного сценария;
- добавить integration tests для happy path, validation failures,
  confirmation failures, idempotency replay, stale version, audit и restart;
- заполнить M4 report и рефлексию.

Запрещено на этом этапе:

- подключать LLM generation, repair loop или eval harness;
- реализовывать Intent Router M5;
- создавать production Menu Planner Hermes plugin;
- подключать Telegram business UX или реальные Telegram callbacks;
- реализовывать menu, recipe, shopping list, store catalog или substitutions;
- выбирать окончательный набор продуктовых полей профиля за рамками
  минимального M4 эксперимента;
- менять Hermes image или создавать custom Hermes image;
- редактировать файлы внутри работающего Hermes container;
- использовать `docker compose build hermes`, `docker build` для Hermes,
  `docker commit` или `docker cp` для установки кода;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 4:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
```

Проверить, что:

- Gate M3 функционально закрыт или явно отложен человеком;
- `docs/experiments/m3-safe-commit.md` существует и заполнен;
- ADR-0001 через ADR-0005 приняты;
- `compose.yaml` по-прежнему не содержит `build:` для Hermes;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты;
- M3 tests не требуют реального Hermes agent turn, LLM или Telegram.

Если `scripts/dev.sh ...` требует Docker socket access, агент должен запросить
разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 4 считается завершенным, если:

- M4 Codex skill существует и помогает удерживать задачи в границах M4;
- минимальная форма profile vertical slice зафиксирована решением или ADR;
- неизвестные продуктовые поля профиля не подменены догадками;
- `ProfileDraft` валидируется детерминированно;
- невалидный профиль возвращает стабильные machine-readable ошибки;
- profile workflow проходит через M2 state machine/policy и блокирует действия
  вне текущего состояния;
- profile preview содержит canonical payload и человекочитаемый summary;
- persistent Confirmation привязан к конкретному user, operation, entity,
  `expected_version`, `draft_version` и `summary_hash`;
- safe commit создает новую `ProfileVersion` и audit event в одной транзакции;
- повтор с тем же idempotency key не создает дубликат profile version;
- повтор с тем же idempotency key и другим payload блокируется;
- stale preview или version mismatch не меняет подтвержденный профиль;
- read query возвращает committed profile after restart;
- сценарий работает через CLI или test API без Hermes, Telegram и LLM;
- Domain Core по-прежнему не импортирует Hermes, Telegram, ORM, HTTP clients
  или model SDK;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke` и `git diff --check` проходят или отклонения явно
  зафиксированы;
- создан `docs/experiments/m4-profile-vertical-slice.md` с результатом Gate M4
  и рефлексией.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M4

Цель: не дать Stage 4 расползтись в M5 Intent Router, LLM, Hermes plugin,
Telegram UX или menu workflows.

Создать:

```text
.agents/skills/m4-profile-vertical-slice/SKILL.md
```

Содержимое:

```markdown
---
name: m4-profile-vertical-slice
description: "Use when building the Menu Planner M4 profile vertical slice: ProfileDraft validation, preview, persistent confirmation, safe commit, ProfileVersion read-back, audit, CLI/test API, and tests, without LLM, Intent Router, Hermes plugin, Telegram UX, menu, recipes, or shopping list."
---

# M4 profile vertical slice workflow

## Scope

- Build only the first deterministic business vertical slice for profile.
- Reuse M2 contracts/policy and M3 safe commit primitives.
- Add profile-specific validation, application commands/queries,
  persistence mapping, preview, commit, audit, and tests.
- Connect profile workflow to the M2 state machine/policy and cover disallowed
  actions in the current workflow state.
- Provide a temporary CLI or test API for the scenario.
- Do not implement Intent Router, LLM generation, Hermes plugin, Telegram UX,
  menu, recipes, shopping list, store catalog, or substitutions.
- Do not create or modify a custom Hermes image.

## Required context

Read before acting:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 4.md`
- `docs/experiments/m3-safe-commit.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If a product or safety decision is blocking, ask the user during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run the narrowest relevant checks first.
8. Run `git diff --check`.
9. Report changed files, commands, passed checks, skipped checks, assumptions,
   and follow-up tasks.

## Guardrails

- Domain Core must not import Hermes, Telegram, ORM, HTTP clients, or model SDK.
- Application service owns transaction boundary and PostgreSQL writes.
- Profile workflow/policy must block profile actions outside the current
  state.
- Profile commit must reuse preview, confirmation, version check,
  idempotency handling, transaction, and audit.
- User text, LLM output, Hermes callbacks, and Telegram callbacks are outside
  M4 and must not commit application state.
- Do not choose final product profile fields without explicit user decision.
- Keep secrets out of Git, logs, reports, and diffs.
```

Проверка:

```text
$m4-profile-vertical-slice

Ничего не меняй.
Опиши границы M4 и что нельзя реализовывать на этом этапе.
```

Критерий завершения: Codex явно говорит, что M4 ограничен deterministic profile
vertical slice без LLM, Intent Router, production Hermes plugin, Telegram UX,
menu, recipes и shopping list.

### Шаг 2. Зафиксировать минимальную форму profile vertical slice

Цель: не превратить M4 в незаметное продуктовое проектирование всего профиля.

Создать ADR или decision note:

```text
docs/decisions/ADR-0006-profile-vertical-slice.md
```

ADR должен зафиксировать:

- минимальные поля `ProfileDraft`, нужные только для M4;
- какие поля являются временным technical assumption, а какие продуктовым
  решением;
- как различаются strict restrictions, soft preferences и user facts;
- какие поля остаются `[ТРЕБУЕТ РЕШЕНИЯ]` после M4;
- как формируется profile entity identity;
- как M4 profile versions мапятся на M3 commit primitives;
- confirmation TTL для deterministic CLI/test API или причину, почему TTL
  задается явно в тестовом сценарии;
- idempotency key source для CLI/test API;
- что не решается в M4.

Если агенту нужно выбрать реальные продуктовые поля профиля, он должен задать
вопрос пользователю. Если достаточно минимального technical assumption для
теста архитектуры, он должен явно зафиксировать это в ADR и не выдавать его за
окончательное продуктовое решение.

Критерий завершения:

- ADR-0006 принят;
- нет новых production dependencies без решения;
- профильный сценарий можно проверить без Hermes, Telegram и LLM;
- открытые продуктовые вопросы перенесены в
  `docs/decisions/open-questions.md`.

### Шаг 3. Уточнить profile contracts и validation

Цель: `ProfileDraft` должен стать первым реальным валидируемым бизнес-входом.

Добавить или уточнить:

- `ProfileDraft`;
- `ProfileVersion`;
- valid/invalid fixtures;
- profile validation rules;
- machine-readable profile errors.

Неизвестные продуктовые значения не придумывать. Если поле влияет на смысл
профиля, агент должен спросить пользователя или оставить поле вне M4.

Критерий завершения:

- contract/unit tests валидируют fixtures;
- invalid fixtures возвращают стабильные ошибки;
- все profile contracts сохраняют `schema_version`;
- Domain Core остается независимым от infrastructure.

### Шаг 4. Добавить profile persistence mapping

Цель: сохранить только то состояние, которое нужно для первого вертикального
среза.

Разрешено добавить migrations/tables для:

- profile draft storage, если он не покрывается существующими M3 primitives;
- committed profile versions;
- связи profile version с M3 confirmation/idempotency/audit flow.

Запрещено добавлять tables для menu, recipe, shopping list, store catalog или
Telegram UX state.

Критерий завершения:

- migrations проходят локально;
- rollback/upgrade проверены релевантным тестом или smoke;
- M3 generic primitives не дублируются без причины;
- confirmed profile state переживает restart.

### Шаг 5. Реализовать application commands и queries

Цель: дать внешний deterministic сценарий без Hermes и модели.

Добавить commands/queries минимум для:

- create/update profile draft from structured input;
- validate profile draft;
- create profile preview;
- create confirmation for profile commit;
- commit profile version;
- read current committed profile;
- read current profile workflow/status.

Если HTTP/API shape нужен уже в M4, но его внешний контракт не выбран, агент
должен спросить пользователя. Если HTTP не нужен для Gate M4, оставить CLI или
test API как временную deterministic boundary.

Критерий завершения:

- happy path проходит через application service;
- workflow/policy не позволяет выполнить профильное действие вне текущего
  состояния;
- state-changing operation требует valid confirmation;
- read query возвращает committed profile;
- код не импортирует Hermes, Telegram или LLM adapters.

### Шаг 6. Добавить временный CLI или test API

Цель: сделать сценарий воспроизводимым человеком и тестами до подключения
Intent Router и Hermes.

CLI/test API должен уметь пройти цепочку:

```text
structured command
→ ProfileDraft
→ validation
→ preview
→ Confirmation
→ commit
→ read committed profile
```

Критерий завершения:

- сценарий описан в runbook или experiment report;
- команда не требует секретов;
- команда не требует Hermes, Telegram или LLM;
- команда безопасно переисполняется через idempotency.

### Шаг 7. Покрыть негативные сценарии

Цель: доказать, что M4 не только проходит happy path, но и сохраняет safety
инварианты M3 на реальном профиле.

Покрыть минимум:

- invalid profile input;
- missing required profile field, если оно выбрано для M4;
- ambiguous strict restriction vs soft preference, если это выражено
  structured input;
- expired confirmation;
- wrong-user confirmation;
- changed preview / summary hash mismatch;
- action not allowed in current workflow state;
- idempotency replay;
- idempotency payload mismatch;
- stale expected version;
- rollback при ошибке commit.

Если сценарий требует продуктового решения, агент должен спросить пользователя
или сузить тест до уже принятого M4 technical assumption.

Критерий завершения:

- negative tests проходят;
- ошибки machine-readable;
- confirmed profile не меняется при отказе.

### Шаг 8. Проверить restart и audit trail

Цель: подтвердить, что первый бизнес-сценарий не зависит от process memory.

Проверить:

- pending confirmation после restart;
- committed profile read-back после restart;
- audit event для successful commit;
- отсутствие partial state после rollback.

Критерий завершения:

- integration/smoke test покрывает restart или documented equivalent;
- audit trail объясняет who/what/when/why для committed profile version;
- отчет не раскрывает secrets.

### Шаг 9. Заполнить M4 report и Gate M4 checklist

Цель: остановиться на рефлексии, а не продолжить автоматически в M5.

Создать:

```text
docs/experiments/m4-profile-vertical-slice.md
```

Report должен содержать:

- цель;
- scope;
- команды проверки;
- что реализовано;
- что намеренно не реализовано;
- результаты Gate M4;
- рефлексию;
- решения, которые нужно принять перед M5.

Критерий завершения:

- Gate M4 checklist заполнен;
- remaining assumptions перечислены;
- следующие вопросы перенесены в `docs/decisions/open-questions.md`;
- в отчете явно сказано: не переходить к M5 без отдельного задания.

## 7. Gate M4 checklist

Заполнить в `docs/experiments/m4-profile-vertical-slice.md`:

```markdown
## Gate M4 Checklist

[ ] M4 Codex skill exists and was used for implementation tasks.
[ ] ADR-0006 or equivalent decision note fixes the minimal M4 profile slice.
[ ] Unknown final product profile fields are not invented.
[ ] ProfileDraft validation is deterministic and tested.
[ ] Invalid profile input returns machine-readable errors.
[ ] Profile workflow uses M2 state machine/policy and blocks disallowed actions.
[ ] Profile preview has canonical payload and human-readable summary.
[ ] Profile confirmation is persistent and bound to user, operation, entity,
    version, draft and summary hash.
[ ] Profile commit creates a new ProfileVersion.
[ ] Profile commit writes audit in the same transaction.
[ ] Idempotency replay does not create duplicate ProfileVersion.
[ ] Idempotency payload mismatch is rejected.
[ ] Stale preview/version mismatch cannot change confirmed profile.
[ ] Current committed profile can be read after restart.
[ ] CLI/test API scenario runs without Hermes, Telegram and LLM.
[ ] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[ ] No menu, recipe, shopping list, store catalog, Intent Router, LLM,
    production Hermes plugin or Telegram UX added.
[ ] No Hermes image mutation or custom Hermes image added.
[ ] scripts/dev.sh test passes.
[ ] scripts/dev.sh lint passes.
[ ] scripts/dev.sh typecheck passes.
[ ] scripts/dev.sh smoke passes.
[ ] git diff --check passes.
[ ] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[ ] M4 report is filled.
```

## 8. Рефлексия M4

Ответить перед переходом к M5:

- Достаточно ли чисто profile workflow лег поверх M2 contracts и M3 safe
  commit primitives?
- Пришлось ли менять M3 commit semantics ради профиля?
- Где фактически проходит application transaction boundary в profile commit?
- Какие profile validation errors должны стать user-facing?
- Какие поля профиля реально понадобились для вертикального среза?
- Какие поля профиля остаются `[ТРЕБУЕТ РЕШЕНИЯ]` перед menu workflows?
- Можно ли заменить CLI/test API на Hermes HTTP adapter без изменения Domain
  Core?
- Как будет формироваться idempotency key после подключения Hermes/Telegram?
- Какой confirmation TTL нужен для реального UX, а не CLI/test API?
- Какие вопросы нужно решить перед M5 Intent Router и eval harness?

## 9. Последовательность задач для Codex

Каждую задачу передавать отдельно. Агент должен задавать вопросы по ходу
выполнения конкретного шага, если обнаруживает блокирующее решение. Если
вопрос не блокирует минимальный проверяемый шаг, агент должен продолжить с
явным technical assumption и зафиксировать вопрос в
`docs/decisions/open-questions.md`.

### Задача 1

```text
Используй $m4-profile-vertical-slice.
Ничего не реализуй в application code.
Создай .agents/skills/m4-profile-vertical-slice/SKILL.md по Stage 4.
В конце запусти git diff --check и покажи измененные файлы.
```

### Задача 2

```text
Используй $m4-profile-vertical-slice.
Создай ADR-0006 для минимального profile vertical slice.
Если нужно выбрать продуктовые поля профиля, задай вопрос по ходу задачи.
Если достаточно technical assumption для M4, явно отдели его от продуктового
решения и зафиксируй open questions.
```

### Задача 3

```text
Используй $m4-profile-vertical-slice.
Уточни только ProfileDraft/ProfileVersion contracts, fixtures, validation и
profile errors для M4.
Не добавляй persistence, CLI, HTTP API, Hermes, Telegram или LLM.
```

### Задача 4

```text
Используй $m4-profile-vertical-slice.
Добавь migrations и persistence mapping только для committed profile versions
и необходимых M4 profile primitives.
Не создавай menu/recipe/shopping/store tables.
```

### Задача 5

```text
Используй $m4-profile-vertical-slice.
Добавь application commands/queries для deterministic profile flow:
draft, validate, preview, confirmation, commit, read current profile,
read profile workflow/status.
Переиспользуй M3 safe commit primitives.
```

### Задача 6

```text
Используй $m4-profile-vertical-slice.
Добавь временный CLI или test API для полного profile happy path.
Сценарий не должен требовать Hermes, Telegram, LLM или secrets.
```

### Задача 7

```text
Используй $m4-profile-vertical-slice.
Добавь негативные tests для invalid profile, expired/wrong confirmation,
changed preview, action not allowed in current workflow state,
idempotency replay/conflict и stale version.
Не расширяй scope до menu или Intent Router.
```

### Задача 8

```text
Используй $m4-profile-vertical-slice.
Добавь restart/read-back/audit coverage для profile vertical slice.
Проверь, что rollback не оставляет partial committed profile state.
```

### Задача 9

```text
Используй $m4-profile-vertical-slice.
Заполни docs/experiments/m4-profile-vertical-slice.md и Gate M4 checklist.
Не переходи к M5.
```
