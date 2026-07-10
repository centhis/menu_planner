# Этап 2. M2 domain skeleton: контракты, state machine и policy

## 1. Цель этапа 2

Этап 2 должен довести проект до вехи M2:

> Схемы, state machine, policy и машинные ошибки работают без LLM, без Hermes
> business adapter и без persistence/commit M3.

Главный вопрос этапа:

> Можно ли гарантировать допустимые переходы и форму данных детерминированным
> кодом до подключения модели и Telegram UX?

Этап 2 заканчивается на Gate M2 и рефлексии M2. После Gate M2 не переходить
автоматически к persistence, версиям, confirmation commit или M3 без отдельного
задания.

## 2. Основания

Перед работой учитывать:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 1.md`
- `docs/experiments/m1-walking-skeleton.md`
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md`
- `docs/decisions/ADR-0002-application-runtime.md`
- `docs/decisions/ADR-0003-post-m1-runtime-boundaries.md`

Решения из M0/M1 для этого этапа:

- Domain Core не импортирует Hermes, Telegram, ORM, HTTP clients или model SDK;
- Application service остаётся владельцем HTTP boundary и будущей БД;
- Hermes plugin/tools позже будут только adapter layer к Application HTTP API;
- подтверждённое состояние не хранится только в Hermes runtime state;
- M2 должен выполняться без реального Hermes agent turn и без LLM;
- production dependencies не добавлять без отдельного решения.

## 3. Scope

Разрешено:

- создать или уточнить Codex skill для M2;
- выбрать формат доменных контрактов через ADR;
- добавить domain package skeleton без бизнес-workflow M3+;
- описать версионируемые схемы/модели и fixtures;
- добавить validation и contract tests;
- добавить стабильный каталог machine-readable ошибок;
- описать operation classes;
- реализовать state machine как явную таблицу или эквивалентную структуру;
- реализовать `PolicyDecision` и policy checks без записи в БД;
- добавить негативную матрицу запрещённых действий;
- добавить архитектурные import-boundary тесты;
- заполнить M2 report и рефлексию.

Запрещено на этом этапе:

- создавать domain PostgreSQL tables;
- реализовывать repositories, transaction boundary или SQL adapters;
- реализовывать confirmation commit, idempotency persistence или audit storage;
- реализовывать профиль, меню, рецепты, shopping list как production workflows;
- подключать LLM generation, eval harness или Intent Router M5;
- создавать production Menu Planner Hermes plugin;
- подключать Telegram business UX;
- менять Hermes image или создавать custom Hermes image;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 2:

```bash
git status --short
git diff --check
make check
```

Проверить, что:

- Gate M1 функционально закрыт или явно отложен человеком;
- `docs/experiments/m1-walking-skeleton.md` существует;
- ADR-0001, ADR-0002 и ADR-0003 приняты;
- `compose.yaml` по-прежнему не содержит `build:` для Hermes;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчёты.

## 5. Acceptance criteria

Этап 2 считается завершённым, если:

- M2 Codex skill существует и помогает удерживать задачи в границах M2;
- выбран и зафиксирован формат контрактов и validation strategy;
- все M2 контракты имеют обязательный `schema_version`;
- fixtures содержат валидные и невалидные примеры для контрактов M2;
- невалидный вход возвращает контролируемые машинные ошибки;
- stable error catalog пригоден для будущего repair loop;
- state machine описывает состояния, intents/actions, transitions, terminal
  states и retry policy;
- запрещённый переход всегда возвращает одинаковую машинную ошибку;
- administrative intent/action невозможен из пользовательского workflow;
- policy можно прогнать полностью без LLM, Hermes, Telegram и PostgreSQL
  domain tables;
- архитектурные тесты защищают Domain Core от импортов Hermes/Telegram/ORM/HTTP;
- `make test`, `make lint`, `make typecheck`, `make smoke` и `git diff --check`
  проходят или отклонения явно зафиксированы;
- создан `docs/experiments/m2-domain-skeleton.md` с результатом Gate M2 и
  рефлексией.

## 6. Шаги этапа

### Шаг 1. Создать или обновить Codex skill для M2

Цель: не дать Stage 2 расползтись в M3 persistence/commit или M5 LLM router.

Создать или поддерживать:

```text
.agents/skills/m2-domain-skeleton/SKILL.md
```

Skill должен фиксировать:

- M2 состоит из M2A contracts и M2B workflow/policy;
- разрешены только deterministic contracts, validation, errors, state machine
  и policy;
- запрещены persistence/commit, LLM generation, production Hermes plugin и
  Telegram UX;
- обязательный work cycle: маленькая задача, tests, `git diff --check`, отчёт.

Проверка:

```text
$m2-domain-skeleton

Ничего не меняй.
Опиши границы M2 и что нельзя реализовывать на этом этапе.
```

Критерий завершения: Codex явно говорит, что M2 заканчивается на reflection
после contracts/state machine/policy и не включает M3 commit или M5 LLM.

### Шаг 2. Зафиксировать формат контрактов и validation strategy

Цель: не размазать схемы между Python types, JSON examples и тестовыми
фикстурами без решения.

Создать ADR:

```text
docs/decisions/ADR-0004-domain-contracts-and-validation.md
```

ADR должен зафиксировать:

- формат первичных контрактов;
- где живут runtime validators;
- как экспортируются или проверяются JSON-compatible schemas;
- policy для `schema_version`;
- naming/versioning policy;
- где хранятся fixtures;
- как оформляются validation errors;
- что не решается в M2.

Если для выбранного подхода нужна новая production dependency, сначала явно
согласовать её назначение и обновить dependency policy. Не использовать факт,
что зависимость пришла транзитивно через FastAPI, как молчаливое архитектурное
решение для Domain Core.

Критерий завершения:

- ADR-0004 принят;
- нет новых production dependencies без решения;
- выбранный подход можно проверить тестом без Hermes и LLM.

### Шаг 3. Создать domain package boundary

Цель: подготовить место для доменного кода без привязки к инфраструктуре.

Логически должны появиться:

```text
src/menu_planner/domain/
tests/unit/domain/
tests/contract/
fixtures/
```

Допустимо скорректировать структуру, если ADR-0004 выбирает другой путь, но
граница Domain Core должна оставаться явной.

Добавить архитектурный тест, который запрещает импорт из Domain Core:

- Hermes modules/plugins;
- Telegram adapters;
- ORM/SQL adapters;
- HTTP clients;
- model SDKs.

Критерий завершения:

- пустой или минимальный domain package проходит typecheck;
- import-boundary test падает при запрещённом импорте;
- существующий M1 app остаётся работоспособным.

### Шаг 4. M2A: описать версионируемые контракты

Цель: создать общий язык системы до интеграции модели.

Зафиксировать M2 contracts:

- `ParsedIntent`;
- `ProfileDraft` и `ProfileVersion`;
- `PlanningContext`;
- `MenuDraft`, `MenuVersion`, `MealSlot`;
- `RecipeDraft`, `RecipeVersion`, `Ingredient`;
- `ShoppingList`, `ShoppingListItem`;
- `WorkflowRun`;
- `ValidationResult`;
- `OperationPreview`;
- `Confirmation`;
- `PolicyDecision`;
- `AuditEvent`;
- success/error envelopes для будущих tools.

Для каждого контракта указать:

- `schema_version`;
- обязательные поля;
- enum values;
- диапазоны, если они уже решены;
- compatibility rule;
- минимум один валидный fixture;
- минимум один невалидный fixture;
- машинную ошибку для типового нарушения.

Неизвестные продуктовые поля не придумывать. Если контракт упирается в
`[ТРЕБУЕТ РЕШЕНИЯ]`, добавить вопрос в:

```text
docs/decisions/open-questions.md
```

Временные решения допустимы только если они явно отмечены как M2 technical
assumption и не маскируют продуктовый выбор.

Критерий завершения:

- contract tests валидируют fixtures;
- все M2 contracts имеют `schema_version`;
- invalid fixtures не проходят validation;
- ошибки стабильны и machine-readable.

### Шаг 5. Создать stable error catalog

Цель: будущий repair loop должен получать структурированные ошибки, а не
человеческий текст.

Каталог ошибок должен покрывать минимум:

- schema/version mismatch;
- missing required field;
- invalid enum;
- invalid range;
- action not allowed in current state;
- administrative action denied;
- ambiguous or incomplete intent;
- unsupported intent;
- ownership required but unavailable;
- retry limit reached.

Для каждой ошибки указать:

- stable `code`;
- краткое developer message;
- machine fields;
- где ошибка может возникнуть;
- можно ли её показывать пользователю напрямую или нужен user-facing adapter.

Критерий завершения:

- tests проверяют стабильность error codes;
- ошибки не зависят от текста exception;
- validation и policy используют единый каталог.

### Шаг 6. M2B: реализовать state machine и operation classes

Цель: сделать допустимые действия явными и проверяемыми.

Описать состояния и переходы таблицей или другой обозримой структурой.

Для каждого состояния определить:

- разрешённые intents/actions;
- operation class;
- required data;
- allowed transitions;
- terminal states;
- retry policy;
- machine error для запрещённого действия.

Минимальные operation classes:

```text
read_only
draft_producing
state_changing
administrative
unsupported
```

Не реализовывать реальные profile/menu/recipe/shopping workflows. Для M2
достаточно deterministic policy skeleton и representative states, позволяющих
проверить архитектурные инварианты из `domain-rules.md`.

Критерий завершения:

- unit tests покрывают разрешённые переходы;
- негативная матрица проверяет запрещённые переходы;
- administrative action denied из пользовательского workflow;
- бесконечный loop невозможен из-за retry policy или terminal state.

### Шаг 7. Добавить policy decision layer

Цель: отделить интерпретацию намерения от разрешения действия.

`PolicyDecision` должен возвращать структурированный результат:

- allow/deny/clarify/confirm/unsupported;
- operation class;
- reason/error code;
- current state;
- allowed actions when denied;
- required missing fields or ambiguities;
- whether confirmation is required.

State-changing operation в M2 может доходить только до policy/preview decision.
Commit, persistent confirmation и idempotency storage относятся к M3.

Критерий завершения:

- state-changing decision не меняет подтверждённое состояние;
- ambiguous/incomplete input возвращает clarification decision;
- unsupported/admin input не проходит как read-only;
- tests демонстрируют все decision outcomes.

### Шаг 8. Проверить M2 без Hermes, LLM и PostgreSQL domain tables

Минимальная последовательность:

```bash
make test
make lint
make typecheck
make smoke
git diff --check
```

Дополнительные проверки:

```bash
docker compose config --services
docker compose config --images
rg -n '^\s*build\s*:' compose.yaml
find . -iname 'Dockerfile*' -print
```

Интерпретация остаётся ручной:

- `build:` под service `hermes` запрещён;
- Dockerfile для Hermes запрещён;
- application Dockerfile остаётся допустимым;
- M2 tests не требуют реального Hermes agent turn.

Критерий завершения:

- M1 smoke не сломан;
- M2 domain/policy tests зелёные;
- Hermes image boundary не нарушен.

### Шаг 9. Заполнить отчёт M2

Создать:

```text
docs/experiments/m2-domain-skeleton.md
```

Структура:

```markdown
# M2 domain skeleton report

## Environment

## Contract strategy

## Contracts and fixtures

## Error catalog

## State machine and policy

## Commands

## Checks

## Boundary checks

## Known limits

## Gate M2 result

## Reflection
```

## 7. Gate M2

Этап 2 завершён, когда выполнены все пункты:

```text
[ ] M2 Codex skill exists and is usable.
[ ] ADR-0004 domain contracts and validation accepted.
[ ] Domain Core boundary exists.
[ ] Import-boundary tests protect Domain Core from Hermes/Telegram/ORM/HTTP/model imports.
[ ] Contract fixtures exist for all M2 contracts.
[ ] Every contract requires schema_version.
[ ] Invalid fixtures fail with stable machine-readable errors.
[ ] Stable error catalog exists and is used by validation/policy.
[ ] State machine is explicit and test-covered.
[ ] Operation classes are implemented.
[ ] PolicyDecision outcomes are test-covered.
[ ] Negative transition matrix blocks forbidden actions.
[ ] Administrative action is denied in user workflow.
[ ] No domain PostgreSQL tables or M3 persistence/commit added.
[ ] No LLM generation, Intent Router, production Hermes plugin, or Telegram UX added.
[ ] make test passes.
[ ] make lint passes.
[ ] make typecheck passes.
[ ] make smoke passes.
[ ] git diff --check passes.
[ ] Secret scan/reporting does not expose .env, auth.json, tokens, or credentials.
[ ] M2 report is filled.
```

## 8. Рефлексия M2

Ответить перед переходом к M3:

- Какие правила оказались доменными, а какие интерфейсными?
- Есть ли состояния, существующие только из-за Telegram?
- Можно ли прогнать state machine полностью без LLM и Hermes?
- Какие переходы сложно объяснить, и значит, возможно, они слишком сложны?
- Достаточно ли stable error catalog для будущего repair loop?
- Не попали ли persistence, commit или реальные business workflows в M2?
- Какие поля требуют решения человека перед M3/M4?
- Нужно ли скорректировать ADR-0001, ADR-0002, ADR-0003 или ADR-0004?

## 9. Последовательность задач для Codex

Каждую задачу передавать отдельно.

### Задача 1

```text
Используй $m2-domain-skeleton.
Ничего не реализуй в домене.
Создай ADR-0004 для формата контрактов и validation strategy M2.
Сначала прочитай обязательные документы из skill.
В конце запусти релевантные проверки и git diff --check.
```

### Задача 2

```text
Используй $m2-domain-skeleton.
Создай минимальный domain package boundary и import-boundary test.
Не добавляй бизнес-сущности, БД, repositories или Hermes adapter.
```

### Задача 3

```text
Используй $m2-domain-skeleton.
Добавь один контракт M2 с валидным и невалидным fixture.
Не переходи к другим контрактам без отдельного задания.
```

### Задача 4

```text
Используй $m2-domain-skeleton.
Добавь stable error catalog или один класс ошибок из Stage 2.
Проверь, что tests не зависят от текста exception.
```

### Задача 5

```text
Используй $m2-domain-skeleton.
Добавь минимальную state machine table и operation classes.
Покрой только один небольшой набор состояний и запрещённых переходов.
```

### Задача 6

```text
Используй $m2-domain-skeleton.
Добавь PolicyDecision для одного decision outcome с tests.
Не реализуй persistence, confirmation commit или Telegram UX.
```

### Задача 7

```text
Используй $m2-domain-skeleton.
Расширь негативную матрицу transitions.
Проверь, что administrative action невозможен из пользовательского workflow.
```

### Задача 8

```text
Используй $m2-domain-skeleton.
Заполни docs/experiments/m2-domain-skeleton.md и Gate M2 checklist.
Не переходи к M3.
```
