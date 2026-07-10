# Этап 3. M3 safe commit: persistence, версии, confirmation и идемпотентность

## 1. Цель этапа 3

Этап 3 должен довести проект до вехи M3:

> Версии, persistent confirmation, idempotency и транзакционный commit
> работают детерминированно и безопасно без LLM, Hermes business adapter,
> Telegram UX и production business workflows.

Главный вопрос этапа:

> Может ли повтор, конкуренция, stale preview или ошибка модели повредить
> подтвержденные данные?

Этап 3 заканчивается на Gate M3 и рефлексии M3. После Gate M3 не переходить
автоматически к M4 profile vertical slice без отдельного задания.

## 2. Основания

Перед работой учитывать:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 2.md`
- `docs/experiments/m2-domain-skeleton.md`
- `docs/decisions/ADR-0001-stage-0-integration-decisions.md`
- `docs/decisions/ADR-0002-application-runtime.md`
- `docs/decisions/ADR-0003-post-m1-runtime-boundaries.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/open-questions.md`

Решения из M0-M2 для этого этапа:

- Application service владеет PostgreSQL schema, migrations, repositories и
  transaction boundary.
- Domain Core не импортирует Hermes, Telegram, ORM, HTTP clients или model
  SDK.
- Hermes plugin/tools позже будут только adapter layer к Application HTTP API.
- Подтвержденное состояние не хранится только в Hermes runtime state.
- M2 уже определил контракты `OperationPreview`, `Confirmation`,
  `AuditEvent`, `PolicyDecision`, error catalog, state machine и policy.
- M2 `PolicyDecision` доходит только до preview/confirmation policy. Persistent
  confirmation, idempotency storage и commit относятся к M3.
- Production dependencies не добавлять без отдельного решения.

Решения M3, принятые в ADR-0005 после шага 2:

- expiration проверяется через явный `expires_at`; hidden default в M3 не
  вводится;
- idempotency key является явным полем application command; Hermes/Telegram
  mapping откладывается до adapter milestones;
- audit events сохраняются без cleanup/retention job в M3; будущая retention
  policy не должна менять commit semantics;
- MVP business correction идет через новые корректирующие версии, а не через
  удаление или переписывание committed history;
- technical canonical preview payload обязателен и является источником
  `summary_hash`; user-facing copy откладывается до user workflow/UX этапов.

Если следующая задача упирается в точное UX-значение, например конкретную
длительность confirmation для Telegram-сценария, агент должен не придумывать
его в M3, а вынести это в соответствующий M4/M9 шаг.

## 3. Scope

Разрешено:

- создать Codex skill для M3;
- создать ADR для persistence и safe commit strategy;
- добавить M3 machine-readable commit/idempotency errors;
- добавить PostgreSQL migrations для generic commit primitives;
- добавить repository/application ports и SQL adapters вне Domain Core;
- реализовать deterministic `OperationPreview` и stable `summary_hash`;
- реализовать persistent `Confirmation` lifecycle;
- реализовать idempotency storage для state-changing commands;
- реализовать optimistic locking через `expected_version`;
- разделить draft и committed versions на уровне M3 persistence primitives;
- реализовать транзакционный commit orchestration;
- записывать `AuditEvent` в той же транзакции, что и commit;
- добавить unit/integration tests для повторов, конкуренции, stale preview,
  version mismatch, expired confirmation, wrong user, rollback и restart;
- заполнить M3 report и рефлексию.

Запрещено на этом этапе:

- реализовывать production profile workflow;
- реализовывать menu, recipe, shopping list или store workflows;
- подключать LLM generation, eval harness или Intent Router M5;
- создавать production Menu Planner Hermes plugin;
- подключать Telegram business UX или реальные Telegram callbacks;
- считать Hermes `sc:*` callback доказанным Menu Planner confirmation
  round-trip;
- менять Hermes image или создавать custom Hermes image;
- редактировать файлы внутри работающего Hermes container;
- использовать `docker compose build hermes`, `docker build` для Hermes,
  `docker commit` или `docker cp` для установки кода;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`;
- выбирать business rollback policy без явного решения человека.

## 4. Entry criteria

Перед началом Stage 3:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
```

Проверить, что:

- Gate M2 функционально закрыт или явно отложен человеком;
- `docs/experiments/m2-domain-skeleton.md` существует и заполнен;
- ADR-0001, ADR-0002, ADR-0003 и ADR-0004 приняты;
- `compose.yaml` по-прежнему не содержит `build:` для Hermes;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты;
- M2 domain tests не требуют реального Hermes agent turn, LLM, Telegram или
  domain PostgreSQL tables.

Если `scripts/dev.sh ...` требует Docker socket access, агент должен запросить
разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 3 считается завершенным, если:

- M3 Codex skill существует и помогает удерживать задачи в границах M3;
- ADR для persistence и safe commit strategy принят;
- M3 не меняет архитектурную границу Domain/Application/Infrastructure;
- Domain Core по-прежнему не импортирует Hermes, Telegram, ORM, HTTP clients
  или model SDK;
- migrations создают только M3 persistence primitives, а не production
  profile/menu/recipe/shopping workflows;
- `OperationPreview` имеет deterministic `summary_hash`;
- изменение preview делает старое confirmation непригодным для commit;
- persistent `Confirmation` проверяет пользователя, операцию, entity,
  `expected_version`, `draft_version`, срок действия, статус и `summary_hash`;
- state-changing commit требует валидный confirmation;
- повтор одного запроса не создает дубликат committed version;
- повтор с тем же idempotency key возвращает предсказуемый результат;
- повтор с тем же idempotency key и другим payload блокируется машинной
  ошибкой;
- конкурентный commit обнаруживает version mismatch или row conflict;
- audit event пишется в той же транзакции, что и committed change;
- rollback транзакции не оставляет partially committed state;
- pending confirmation после restart обрабатывается предсказуемо;
- тесты покрывают happy path и негативные сценарии M3;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke` и `git diff --check` проходят или отклонения явно
  зафиксированы;
- создан `docs/experiments/m3-safe-commit.md` с результатом Gate M3 и
  рефлексией.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M3

Цель: не дать Stage 3 расползтись в M4 profile workflow, M5 Intent Router,
Hermes plugin или Telegram UX.

Создать:

```text
.agents/skills/m3-safe-commit/SKILL.md
```

Содержимое:

```markdown
---
name: m3-safe-commit
description: Use when building the Menu Planner M3 safe commit layer: persistence primitives, versioning, OperationPreview hashing, persistent Confirmation, idempotency, transactional commit, audit, and tests, without profile/menu workflows, LLM, Hermes plugin, or Telegram UX.
---

# M3 safe commit workflow

## Scope

- Build only deterministic persistence and safe commit mechanisms.
- Use M2 contracts, state machine, policy, and error catalog as inputs.
- Add migrations, repository/application ports, SQL adapters, confirmation
  lifecycle, idempotency, transaction orchestration, and audit.
- Do not implement production profile, menu, recipe, shopping list, store,
  Intent Router, LLM generation, Hermes plugin, or Telegram business UX.
- Do not create or modify a custom Hermes image.

## Required context

Read before acting:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 3.md`
- `docs/experiments/m2-domain-skeleton.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If a product or safety decision is missing, ask the user during that step.
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
- Hermes and Telegram callbacks must never commit application state directly.
- State-changing commands require preview, confirmation, version check,
  idempotency handling, transaction, and audit.
- Do not choose business rollback policy without explicit user decision.
- Keep secrets out of Git, logs, reports, and diffs.
```

Проверка:

```text
$m3-safe-commit

Ничего не меняй.
Опиши границы M3 и что нельзя реализовывать на этом этапе.
```

Критерий завершения: Codex явно говорит, что M3 ограничен persistence,
версиями, confirmation, idempotency, transactional commit и audit, без M4
profile workflow, M5 Intent Router, LLM, production Hermes plugin и Telegram
UX.

### Шаг 2. Зафиксировать persistence и safe commit strategy

Цель: не реализовывать commit semantics как набор случайных SQL-запросов.

Создать ADR:

```text
docs/decisions/ADR-0005-safe-commit-and-persistence.md
```

ADR должен зафиксировать:

- какие M3 persistence primitives создаются;
- какие таблицы являются generic/test primitives, а какие запрещены до M4+;
- где живут repository/application ports;
- где живут SQL adapters;
- transaction boundary;
- isolation/locking approach;
- optimistic locking через `expected_version`;
- draft vs committed version model;
- canonicalization для `summary_hash`;
- confirmation lifecycle и statuses;
- expiration policy;
- idempotency key policy;
- idempotency conflict behavior;
- audit event fields;
- restart behavior for pending confirmations;
- rollback policy;
- что не решается в M3.

Если для решения нужен продуктовый выбор, агент задает вопрос пользователю.
Если выбор не блокирует текущий минимальный тестируемый шаг, агент фиксирует
его в `docs/decisions/open-questions.md` и продолжает с явно ограниченным
technical assumption.

Критерий завершения:

- ADR-0005 принят;
- нет новых production dependencies без решения;
- commit strategy можно проверить тестом без Hermes, Telegram и LLM;
- Domain Core остается независимым от persistence implementation.

### Шаг 3. Расширить machine-readable error catalog для M3

Цель: commit failures должны быть машинно различимы и пригодны для будущего UX
и repair loop.

Добавить ошибки минимум для:

- confirmation not found;
- confirmation expired;
- confirmation already used;
- confirmation rejected or cancelled;
- confirmation user mismatch;
- confirmation operation mismatch;
- confirmation entity mismatch;
- preview summary hash mismatch;
- expected version mismatch;
- draft version mismatch;
- idempotency key missing when required;
- idempotency replay;
- idempotency payload mismatch;
- transaction conflict;
- audit write failure.

Критерий завершения:

- tests проверяют стабильность error codes;
- ошибки не зависят от текста exception;
- validation/policy/commit используют единый catalog-backed формат.

### Шаг 4. Добавить persistence schema для M3 primitives

Цель: получить reproducible PostgreSQL schema для commit mechanics без
production business workflows.

Добавить Alembic migration для M3 primitives, например:

- confirmations;
- idempotency records;
- audit events;
- generic versioned records или другой минимальный M3 test target,
  утвержденный ADR-0005;
- indexes и unique constraints для ownership, versioning и idempotency.

Не создавать production profile/menu/recipe/shopping tables на этом шаге.

Проверки:

```bash
scripts/dev.sh migration-status
scripts/dev.sh test
git diff --check
```

Критерий завершения:

- migration применима и обратима согласно выбранному migration policy;
- M1 smoke не сломан;
- tests подтверждают, что Hermes service не получил `build:`.

### Шаг 5. Добавить repository/application ports и SQL adapters

Цель: сохранить границу Domain Core и дать Application service владеть commit
transaction.

Добавить:

- application-level ports для confirmations, idempotency, versioned records и
  audit;
- SQL adapters в infrastructure layer;
- tests, которые доказывают, что Domain Core не импортирует infrastructure;
- tests на базовые repository operations.

Критерий завершения:

- Domain import-boundary test остается зеленым;
- SQL adapters не вызываются из Hermes или Telegram code path;
- repository operations работают через application/infrastructure boundary.

### Шаг 6. Реализовать deterministic OperationPreview и summary_hash

Цель: confirmation должен быть связан с конкретным preview, а не только с
человеческим текстом.

Реализовать:

- canonical JSON-compatible payload для preview;
- stable ordering;
- включение `schema_version`, `operation`, `entity_id`, `expected_version`,
  `draft_version`, `user_id` или другого утвержденного ownership marker;
- `summary_hash`;
- tests на одинаковый hash для семантически одинакового preview;
- tests на разный hash при изменении значимого поля.

Критерий завершения:

- preview hash не зависит от порядка ключей;
- изменение committed-relevant данных invalidates confirmation;
- user-facing wording не является единственным источником hash.

### Шаг 7. Реализовать persistent Confirmation lifecycle

Цель: state-changing operation может ждать подтверждения и переживать restart.

Реализовать statuses и transitions, утвержденные ADR-0005, минимум:

```text
pending
confirmed
committed
expired
rejected
used
```

Проверить:

- создание pending confirmation;
- lookup by confirmation_id and user_id;
- expiration handling;
- reject/cancel;
- one-time или idempotent reuse согласно ADR-0005;
- stale preview detection через `summary_hash`;
- restart между preview и confirm.

Критерий завершения:

- expired confirmation не commit-ится;
- confirmation другого пользователя не commit-ится;
- старый preview не commit-ится после изменения значимых данных;
- pending confirmation не зависит от Hermes memory.

### Шаг 8. Реализовать idempotency storage

Цель: повтор network/model/user action не создает дубликаты.

Реализовать:

- idempotency key capture for state-changing commands;
- request fingerprint или payload hash;
- stored outcome или reference to committed result;
- replay behavior;
- conflict behavior for same key with different payload;
- cleanup/retention question, если policy не выбрана.

Критерий завершения:

- повтор того же запроса возвращает тот же committed result или controlled
  replay response;
- тот же key с другим payload возвращает machine-readable conflict;
- отсутствие required idempotency key блокируется там, где это требует ADR.

### Шаг 9. Реализовать transactional commit orchestration

Цель: commit становится одной атомарной операцией Application service.

Commit должен проверять:

- user ownership;
- operation;
- entity_id;
- current workflow/policy allowance where applicable;
- `expected_version`;
- `draft_version`;
- confirmation status;
- confirmation expiration;
- `summary_hash`;
- idempotency key;
- optimistic locking result.

В одной транзакции:

- применить committed version;
- обновить confirmation status;
- записать idempotency outcome;
- записать audit event.

Критерий завершения:

- partial commit невозможен при ошибке;
- audit event появляется только вместе с committed change;
- conflict не оставляет confirmation в неверном финальном статусе;
- transaction boundary находится в Application service, не в Hermes.

### Шаг 10. Добавить M3 негативные и concurrency tests

Цель: доказать безопасность на сценариях, где чаще всего ломается commit.

Покрыть минимум:

- happy path;
- повтор одного confirmation;
- expired confirmation;
- confirmation другого пользователя;
- changed preview;
- version mismatch;
- draft version mismatch;
- same idempotency key and same payload;
- same idempotency key and different payload;
- два параллельных commit;
- rollback transaction при ошибке audit или version write;
- restart между preview и confirm;
- Domain import-boundary regression.

Критерий завершения:

- tests воспроизводимы локально;
- concurrency test не зависит от sleep как единственной синхронизации;
- failures возвращают stable machine-readable errors.

### Шаг 11. Проверить M3 без Hermes, LLM и Telegram

Минимальная последовательность:

```bash
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
git diff --check
```

Дополнительные проверки:

```bash
docker compose config --services
docker compose config --images
rg -n '^\s*build\s*:' compose.yaml
find . -iname 'Dockerfile*' -print
```

Интерпретация остается ручной:

- `build:` под service `hermes` запрещен;
- Dockerfile для Hermes запрещен;
- application Dockerfile остается допустимым;
- M3 tests не требуют реального Hermes agent turn;
- M3 tests не требуют Telegram callbacks или LLM calls.

### Шаг 12. Заполнить отчет M3

Создать:

```text
docs/experiments/m3-safe-commit.md
```

Структура:

```markdown
# M3 safe commit report

## Environment

## Persistence strategy

## Migration summary

## Preview and hash

## Confirmation lifecycle

## Idempotency behavior

## Transaction and audit behavior

## Commands

## Checks

## Boundary checks

## Known limits

## Gate M3 result

## Reflection
```

## 7. Gate M3

Этап 3 завершен, когда выполнены все пункты:

```text
[x] M3 Codex skill exists and is usable.
[x] ADR-0005 safe commit and persistence strategy accepted.
[x] M3 error catalog additions are stable and tested.
[x] M3 persistence migrations exist.
[x] Migrations do not create production profile/menu/recipe/shopping workflows.
[x] Repository/application ports exist outside Domain Core.
[x] SQL adapters live outside Domain Core.
[x] Domain import-boundary tests still pass.
[x] OperationPreview summary_hash is deterministic.
[x] Changed preview invalidates old confirmation.
[x] Persistent Confirmation lifecycle is implemented and tested.
[x] Expired confirmation cannot commit.
[x] Wrong-user confirmation cannot commit.
[x] Used/replayed confirmation behavior follows ADR-0005.
[x] Idempotency storage is implemented and tested.
[x] Same idempotency key with different payload is rejected.
[x] Transactional commit checks ownership, operation, version, confirmation,
    summary_hash and idempotency.
[x] Concurrent commit is safe.
[x] Audit event is written in the same transaction as commit.
[x] Rollback leaves no partial committed state.
[x] Restart between preview and confirm is covered.
[x] No LLM generation, Intent Router, production Hermes plugin, or Telegram UX
    added.
[x] No Hermes image mutation or custom Hermes image added.
[x] scripts/dev.sh test passes.
[x] scripts/dev.sh lint passes.
[x] scripts/dev.sh typecheck passes.
[x] scripts/dev.sh smoke passes.
[x] git diff --check passes.
[x] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[x] M3 report is filled.
```

## 8. Рефлексия M3

Ответить перед переходом к M4:

- Достаточно ли generic M3 primitives, чтобы реализовать первый profile
  vertical slice без переписывания commit?
- Где проходит фактическая transaction boundary?
- Не протекли ли ORM, SQL или infrastructure imports в Domain Core?
- Какие ошибки commit должны стать user-facing, а какие останутся developer
  diagnostics?
- Как explicit `expires_at` проверяется без hidden default в M3?
- Как ведет себя повтор после restart?
- Можно ли объяснить audit trail для каждого committed change?
- Достаточно ли принятой MVP policy с корректирующими версиями без удаления
  history?
- Какие M3 assumptions нужно превратить в решения перед M4?
- Нужно ли обновить ADR-0001, ADR-0002, ADR-0003 или ADR-0004?

## 9. Последовательность задач для Codex

Каждую задачу передавать отдельно. Агент должен задавать вопросы по ходу
выполнения конкретного шага, если обнаруживает блокирующее решение.

### Задача 1

```text
Используй $m3-safe-commit.
Ничего не реализуй в application code.
Создай .agents/skills/m3-safe-commit/SKILL.md по Stage 3.
В конце запусти git diff --check и покажи измененные файлы.
```

### Задача 2

```text
Используй $m3-safe-commit.
Создай ADR-0005 для safe commit and persistence strategy.
Если нужен выбор по expiration/idempotency/rollback, задай вопрос по ходу
задачи или зафиксируй open question, если это не блокирует ADR skeleton.
```

### Задача 3

```text
Используй $m3-safe-commit.
Добавь только M3 commit/idempotency ошибки в stable error catalog и tests.
Не добавляй migrations, repositories или business workflows.
```

### Задача 4

```text
Используй $m3-safe-commit.
Добавь Alembic migration только для M3 persistence primitives,
согласованных ADR-0005.
Не создавай profile/menu/recipe/shopping production tables.
```

### Задача 5

```text
Используй $m3-safe-commit.
Добавь repository/application ports и минимальный SQL adapter для одного M3
primitive с tests.
Проверь, что Domain Core не импортирует infrastructure.
```

### Задача 6

```text
Используй $m3-safe-commit.
Реализуй deterministic OperationPreview summary_hash с tests.
Не реализуй confirmation lifecycle или commit в этой задаче.
```

### Задача 7

```text
Используй $m3-safe-commit.
Реализуй persistent Confirmation lifecycle для одного минимального сценария.
Покрой expired, wrong-user и changed-preview cases.
```

### Задача 8

```text
Используй $m3-safe-commit.
Реализуй idempotency storage и tests для replay и payload mismatch.
Не добавляй business workflows.
```

### Задача 9

```text
Используй $m3-safe-commit.
Реализуй transactional commit orchestration для generic M3 test target.
Покрой version mismatch, audit-in-transaction и rollback behavior.
```

### Задача 10

```text
Используй $m3-safe-commit.
Добавь concurrency/restart tests для M3 commit.
Не подключай Hermes, Telegram или LLM.
```

### Задача 11

```text
Используй $m3-safe-commit.
Заполни docs/experiments/m3-safe-commit.md и Gate M3 checklist.
Не переходи к M4.
```
