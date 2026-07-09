# Этап 1. Walking skeleton: приложение, PostgreSQL и проверки

## 1. Цель этапа 1

Этап 1 должен довести проект до вехи M1:

> Приложение, база данных и тесты запускаются одной воспроизводимой
> последовательностью команд.

Главный вопрос этапа:

> Воспроизводится ли среда на чистом checkout без ручных действий внутри
> контейнеров и без скрытых локальных зависимостей?

Этап 1 заканчивается на Gate M1 и рефлексии. После Gate M1 не переходить
автоматически к доменным контрактам M2 без отдельного задания.

## 2. Основания

Перед работой учитывать:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/experiments/hermes-capability-spike.md`
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md`

Решения из ADR-0001 для этого этапа:

- использовать Hermes-to-Application HTTP API adapter direction;
- отложить local models на отдельный этап;
- оставить Hermes Dashboard для dev/ops, но считать basic auth временным;
- использовать Telegram `sc:*` confirmations как выбранное направление;
- целевой Telegram user toolset должен быть только `menu_planner_*`;
- project-owned inputs подключать через read-only bind mounts;
- прикладное состояние хранить в PostgreSQL / Application DB.

## 3. Scope

Разрешено:

- выбрать application runtime и toolchain;
- добавить dependency manager и lock file;
- создать пустой application skeleton;
- добавить PostgreSQL в Compose;
- добавить application DB configuration через `.env.example`;
- добавить миграционный инструмент и пустую начальную миграцию;
- добавить health/readiness endpoint или эквивалентный smoke endpoint;
- добавить test/lint/format/typecheck commands;
- добавить `Makefile` или другой единый command entrypoint;
- добавить локальный smoke test;
- добавить CI или локально воспроизводимый CI-скрипт;
- добавить документацию запуска и диагностики.

Запрещено на этом этапе:

- реализовывать профиль пользователя;
- реализовывать меню;
- реализовывать рецепты;
- реализовывать shopping list;
- реализовывать production business workflows;
- создавать production Menu Planner Plugin;
- подключать Telegram business UX;
- менять Hermes image или создавать custom Hermes image;
- редактировать файлы внутри работающего Hermes container;
- добавлять production dependencies без отдельного решения по runtime/toolchain.

## 4. Entry criteria

Перед началом Stage 1:

```bash
git status --short
git diff --check
git add --dry-run .
```

Проверить, что:

- Stage 0 commit создан или осознанно отложен человеком;
- `.env`, credentials, `auth.json`, tokens и private keys не попадают в
  `git add --dry-run .`;
- `compose.yaml` использует готовый Hermes image и не содержит `build:` для
  Hermes;
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md` существует.

## 5. Acceptance criteria

Этап 1 считается завершённым, если новый разработчик или Codex-agent на чистом
checkout может выполнить одну задокументированную последовательность команд и
получить:

- запущенный PostgreSQL;
- запущенное пустое приложение;
- применённые миграции;
- зелёные тесты;
- зелёный lint/typecheck, если выбранный toolchain их поддерживает;
- работающий health/readiness response;
- smoke test, который проверяет приложение и подключение к БД;
- возможность полностью удалить локальное runtime state и повторить запуск.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M1

Цель: не дать Stage 1 расползтись в доменную реализацию.

Создать:

```text
.agents/skills/m1-walking-skeleton/SKILL.md
```

Содержимое:

```markdown
---
name: m1-walking-skeleton
description: Use when building the Menu Planner M1 walking skeleton: app runtime, PostgreSQL, migrations, health checks, Makefile, tests, lint, and smoke checks, without business workflows.
---

# M1 walking skeleton workflow

## Scope

- Build only the empty reproducible application skeleton.
- Add PostgreSQL / Application DB plumbing.
- Add migrations, health/readiness checks, tests, lint/typecheck, and smoke.
- Do not implement profile, menu, recipes, shopping list, or production workflows.
- Do not create or modify a custom Hermes image.

## Required context

Read before acting:

- `AGENTS.md`
- `docs/implementation-plan.md`
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md`
- `docs/Stage 1.md`

## Work cycle

1. Restate the single task and acceptance criteria.
2. Identify files expected to change.
3. Inspect current implementation before editing.
4. Prefer the selected project toolchain and existing patterns.
5. Add the smallest testable change.
6. Run the narrowest relevant check.
7. Run `git diff --check`.
8. Report changed files, commands, passed checks, skipped checks, and
   remaining assumptions.

## Guardrails

- Keep Domain Core independent of Hermes and Telegram imports.
- Keep confirmed business state out of Hermes runtime state.
- Keep secrets out of Git and logs.
- Any Dockerfile must be for the application only and must not be named or
  used as a Hermes image.
```

Проверка:

```text
$m1-walking-skeleton

Ничего не меняй.
Опиши границы M1 и что нельзя реализовывать на этом этапе.
```

Критерий завершения: Codex явно говорит, что M1 ограничен пустым skeleton,
PostgreSQL, миграциями, health, тестами и smoke, без бизнес-workflows.

### Шаг 2. Выбрать application runtime и toolchain

Цель: не добавлять зависимости случайно.

Создать ADR:

```text
docs/decisions/ADR-0002-application-runtime.md
```

ADR должен зафиксировать:

- язык и версию;
- dependency manager;
- lock-file policy;
- formatter;
- linter;
- type checker, если применимо;
- test runner;
- migration tool;
- application service shape;
- CI command set.

Неизвестные параметры фиксировать как `[ТРЕБУЕТ РЕШЕНИЯ]`, а не подменять
догадкой.

Критерий завершения:

- ADR-0002 принят;
- выбранные команды можно запускать локально;
- production dependencies добавлены только после решения ADR-0002.

### Шаг 3. Создать минимальный application skeleton

Цель: получить пустое приложение без бизнес-логики.

Добавить структуру согласно выбранному runtime. Логически должны появиться:

```text
src/
tests/
```

Минимальный код должен уметь:

- стартовать;
- вернуть health/readiness response;
- прочитать безопасную конфигурацию;
- проверить подключение к PostgreSQL;
- проверить доступность Hermes как критического внешнего runtime component
  для полного `/readyz`;
- завершиться с понятной ошибкой при недоступной БД.

Запрещено добавлять:

- profile entities;
- menu entities;
- recipe entities;
- shopping list entities;
- workflow business transitions.

Критерий завершения:

- приложение стартует локально выбранной командой;
- health/readiness проверяется автоматически;
- `/readyz` покрывает app, PostgreSQL и Hermes;
- Stage 0 probe plugin не смонтирован и не включён в default runtime;
- тесты не требуют реального Hermes agent turn.

### Шаг 4. Добавить PostgreSQL в Compose

Цель: получить Application DB как отдельный runtime state.

Изменить `compose.yaml` минимально:

- оставить Hermes на готовом image;
- добавить `postgres` service;
- добавить application service, если выбранный runtime требует compose-run;
- добавить named volume для PostgreSQL;
- не монтировать секреты из host напрямую в Git;
- не использовать `docker compose build` для Hermes;
- использовать `docker compose build app`, когда нужно пересобрать application
  image или обновить зависимости.

Обновить `.env.example` placeholders:

```text
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
```

Реальный `.env` не открывать и не коммитить.

`.env` хранит примитивы и секреты. Derived values, например `DATABASE_URL`,
собираются в `compose.yaml` или приложением из примитивов.

Проверки:

```bash
docker compose config --services
docker compose config --images
docker compose config --volumes
rg -n '^\s*build\s*:' compose.yaml
find . -iname 'Dockerfile*' -print
```

Вывод `rg` и `find` нужно интерпретировать вручную:

- `build:` под service `hermes` запрещён;
- Dockerfile для Hermes запрещён;
- Dockerfile и `build:` для application service допустимы и ожидаемы, потому
  что зависимости устанавливаются в application image.

Критерий завершения:

- `postgres` виден в Compose;
- PostgreSQL state хранится в named volume;
- Hermes по-прежнему запускается только из ready image;
- если появляется Dockerfile, он относится только к application service и
  отдельно объяснён в ADR-0002 или Stage 1 report.

### Шаг 5. Добавить миграции

Цель: проверить миграционный контур без доменной модели.

Добавить:

- migration directory;
- пустую или техническую initial migration;
- команду применения миграций;
- команду проверки текущего состояния миграций.

Миграция не должна создавать profile/menu/recipe/shopping tables.

Допустимо создать только техническую таблицу миграционного инструмента, если
она требуется выбранным toolchain.

Критерий завершения:

```bash
make migrate
make smoke
```

или эквивалентные команды выбранного entrypoint проходят на пустой БД.

### Шаг 6. Добавить единые команды разработки

Цель: один понятный вход для человека и coding-agent.

Добавить `Makefile` или ADR-0002-approved equivalent с командами:

```text
setup
up
down
test
lint
typecheck
migrate
smoke
clean
```

Если часть команд неприменима к выбранному runtime, команда должна быть
явно описана как no-op или заменена ADR-0002-approved аналогом.

Критерий завершения:

```bash
make setup
make up
make migrate
make test
make lint
make smoke
```

проходят или дают документированную причину, почему команда отложена.

### Шаг 7. Добавить tests и smoke

Цель: Gate M1 должен проверяться автоматически.

Минимальный набор:

- unit test для health/config logic;
- integration test или smoke для PostgreSQL connection;
- smoke command, который проверяет:
  - приложение отвечает;
  - БД доступна;
  - миграции применены;
  - Hermes service не сломан compose-изменениями.

Не добавлять LLM evals, golden workflows или Telegram E2E в M1.

Критерий завершения:

```bash
make test
make smoke
```

проходят на свежем запуске.

### Шаг 8. Добавить локальную runbook-документацию

Создать:

```text
docs/runbooks/local-development.md
```

Документ должен объяснять:

- как создать `.env` из `.env.example`;
- какие секреты нельзя коммитить;
- как поднять систему;
- как применить миграции;
- как запустить тесты;
- как выполнить smoke;
- как остановить сервисы;
- как удалить локальное state с явным предупреждением про volumes.

Не включать реальные секреты.

### Шаг 9. Проверить воспроизводимость M1

Минимальная последовательность:

```bash
git status --short
git diff --check
docker compose config --services
docker compose config --images
docker compose config --volumes
make setup
make up
make migrate
make test
make lint
make smoke
```

Отдельная destructive-проверка только после явного подтверждения человека.
Это release/reproducibility drill или emergency reset, потому что команда
удаляет named volumes, включая Hermes runtime state и Codex authorization:

```bash
docker compose down -v
make up
make migrate
make smoke
```

Критерий завершения:

- чистый checkout воспроизводимо поднимает пустое приложение и БД;
- после удаления volumes система восстанавливается командами M1;
- диагностика ошибок достаточно понятна без чтения секретов.

### Шаг 10. Заполнить отчёт M1

Создать:

```text
docs/experiments/m1-walking-skeleton.md
```

Структура:

```markdown
# M1 walking skeleton report

## Environment

## Runtime and toolchain

## Compose services

## Database

## Commands

## Checks

## Secret handling

## Known limits

## Gate M1 result

## Reflection
```

## 7. Gate M1

Этап 1 завершён, когда выполнены все пункты:

```text
[ ] Stage 0 baseline committed or explicitly deferred by the operator.
[ ] M1 Codex skill exists and is usable.
[ ] ADR-0002 application runtime accepted.
[ ] Dependency manager and lock file exist.
[ ] Formatter/linter/typecheck/test runner configured.
[ ] PostgreSQL service added to Compose.
[ ] Application service or local app command starts reproducibly.
[ ] `.env.example` contains placeholders, not secrets.
[ ] Real `.env` remains ignored.
[ ] Migrations command exists.
[ ] Empty/technical initial migration applies.
[ ] Health/readiness check exists.
[ ] DB connection smoke exists.
[ ] Hermes readiness is included in `/readyz` or documented as pending.
[ ] `make setup` works or documented equivalent exists.
[ ] `make up` works or documented equivalent exists.
[ ] `make migrate` works or documented equivalent exists.
[ ] `make test` works or documented equivalent exists.
[ ] `make lint` works or documented equivalent exists.
[ ] `make smoke` works or documented equivalent exists.
[ ] `git diff --check` passes.
[ ] Secret scan before commit passes.
[ ] M1 report is filled.
```

## 8. Рефлексия M1

Ответить перед переходом к M2:

- Есть ли скрытые ручные шаги?
- Зафиксированы ли версии runtime и зависимостей?
- Можно ли повторить запуск после удаления volumes?
- Достаточно ли логов, чтобы LLM диагностировала падение без догадок?
- Не попала ли бизнес-логика M2+ в walking skeleton?
- Не зависит ли Domain Core от Hermes или Telegram?
- Сохраняется ли разделение Hermes runtime state и application state?
- Нужно ли скорректировать ADR-0001 или ADR-0002 перед M2?

## 9. Последовательность задач для Codex

Каждую задачу передавать отдельно.

### Задача 1

```text
$verified-small-change

Зафиксируй финальное состояние Stage 0 перед началом M1.
Ничего не реализуй.
Проверь secret safety и готовность к baseline commit.
```

### Задача 2

```text
$verified-small-change

Создай только Codex skill m1-walking-skeleton.
Не меняй application code и Compose.
```

### Задача 3

```text
$verified-small-change
$m1-walking-skeleton

Подготовь ADR-0002 с выбором application runtime и toolchain.
Не добавляй production dependencies до принятия ADR.
```

### Задача 4

```text
$verified-small-change
$m1-walking-skeleton

Добавь минимальный application skeleton по ADR-0002.
Без PostgreSQL, миграций и бизнес-логики.
```

### Задача 5

```text
$verified-small-change
$m1-walking-skeleton

Добавь PostgreSQL и application DB configuration в Compose.
Не меняй Hermes image и не читай .env.
```

### Задача 6

```text
$verified-small-change
$m1-walking-skeleton

Добавь миграционный контур и пустую initial migration.
Не создавай доменные таблицы профиля, меню, рецептов или shopping list.
```

### Задача 7

```text
$verified-small-change
$m1-walking-skeleton

Добавь единые команды setup/up/migrate/test/lint/smoke и минимальные проверки.
```

### Задача 8

```text
$verified-small-change
$m1-walking-skeleton

Заполни M1 walking skeleton report и проверь Gate M1.
Не переходи к M2.
```
