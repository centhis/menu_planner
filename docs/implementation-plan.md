# План реализации Menu Planner for Hermes с нуля

**Версия:** 0.1  
**Статус:** рабочий план реализации методом вайбкодинга  
**Основание:** `concept.md`, `architecture.md`, `domain-rules.md`

## 1. Цель плана

Организовать разработку так, чтобы:

- как можно раньше получить работающий сквозной сценарий;
- использовать Hermes как основной agent runtime;
- держать бизнес-логику, разрешения, валидацию и commit в детерминированном коде;
- проверять каждое предположение небольшим исполняемым экспериментом;
- не блокировать разработку из-за открытых вопросов;
- сохранить возможность заменить облачную модель слабой локальной;
- обеспечить воспроизводимость, миграцию и тиражирование результата.

Главный порядок реализации:

```text
Domain contracts
→ deterministic workflow
→ persistence and commit
→ vertical slice without LLM
→ model adapters and evaluations
→ Hermes plugin
→ Telegram UX
→ hardening and deployment
```

Не следует начинать с большого промпта, полноценного Telegram-бота или генерации красивого меню. Сначала должен заработать безопасный контур:

```text
draft → validate → preview → confirmation → commit
```

## 2. Правила организации вайбкодинга

### 2.1. Один запрос к модели — одно проверяемое изменение

Размер задачи должен позволять:

- понять ожидаемое поведение;
- увидеть весь diff;
- выполнить тесты;
- откатить изменение одним commit;
- объяснить, почему результат считается правильным.

Запрещённые формулировки задач:

- «сделай весь backend»;
- «реализуй архитектуру»;
- «создай Telegram-бота целиком»;
- «отрефактори всё»;
- «добавь безопасность».

Допустимый размер:

- одна схема;
- один переход workflow;
- один validator;
- один tool handler;
- одна миграция;
- один вертикальный happy path;
- один класс негативных тестов.

### 2.2. Сначала контракт и тест, затем реализация

Для каждой задачи последовательность одинакова:

1. зафиксировать вход, выход и ошибки;
2. добавить или уточнить тест;
3. получить минимальную реализацию;
4. запустить локальные проверки;
5. просмотреть diff вручную;
6. проверить архитектурные инварианты;
7. обновить документацию или ADR;
8. сделать отдельный commit.

### 2.3. LLM не закрывает неопределённость догадкой

При обнаружении неизвестного модель должна сделать одно из трёх:

- использовать явно отмеченное временное допущение;
- создать эксперимент для сравнения вариантов;
- добавить вопрос в `docs/decisions/open-questions.md`.

Неопределённость не должна маскироваться произвольной реализацией.

### 2.4. Каждый эксперимент ограничен

Эксперимент должен содержать:

- гипотезу;
- сравниваемые варианты;
- тестовый набор;
- метрику;
- срок жизни экспериментального кода;
- условие выбора;
- решение: принять, отклонить или отложить.

### 2.5. Документы являются частью кода

После изменения архитектурного поведения обновляются:

- ADR;
- схема или контракт;
- тесты;
- соответствующий раздел концепции, архитектуры или доменных правил;
- журнал решений.

## 3. Рекомендуемая структура репозитория

Конкретные язык и framework выбираются после проверки установленной версии Hermes. Логическая структура не зависит от технологии.

```text
menu-planner/
├── README.md
├── AGENTS.md
├── compose.yaml
├── .env.example
├── Makefile
├── docs/
│   ├── concept.md
│   ├── architecture.md
│   ├── domain-rules.md
│   ├── implementation-plan.md
│   ├── decisions/
│   │   ├── open-questions.md
│   │   ├── decision-log.md
│   │   └── ADR-0001-*.md
│   ├── experiments/
│   └── runbooks/
├── schemas/
│   ├── intent/
│   ├── profile/
│   ├── menu/
│   ├── recipe/
│   ├── shopping/
│   └── tool-results/
├── src/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── adapters/
│   │   ├── hermes/
│   │   ├── telegram/
│   │   ├── models/
│   │   └── stores/
│   └── bootstrap/
├── migrations/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── golden/
│   ├── security/
│   └── evals/
├── fixtures/
├── scripts/
└── var/                 # только локальные, некоммитимые данные
```

### Границы зависимостей

```text
Domain
  ↑
Application
  ↑
Adapters / Infrastructure
  ↑
Hermes / Telegram bootstrap
```

`domain` не импортирует Hermes, Telegram, ORM, HTTP-клиент или SDK модели.

## 4. Сквозные инварианты проекта

Эти правила должны стать автоматическими тестами, а не только текстом документации.

1. Модель не пишет в базу напрямую.
2. Пользовательский текст не вызывает произвольный tool.
3. Любой генеративный результат сначала является draft.
4. Любое изменение подтверждённых данных проходит preview и confirmation.
5. Commit проверяет пользователя, версию, состояние workflow, срок и идемпотентность.
6. Tool повторно проверяет разрешение независимо от prompt и hook.
7. Список покупок строится детерминированным кодом.
8. Критичные данные не существуют только в memory Hermes.
9. Пользовательский toolset не содержит terminal, filesystem, произвольный browser, SQL и административные tools.
10. Внешние страницы и API-ответы считаются недоверенными данными.
11. Каждый workflow имеет ограничение числа попыток и завершённое состояние ошибки.
12. После перезапуска workflow либо продолжается, либо безопасно переводится в восстанавливаемое состояние.
13. Смена модели не требует изменения Domain Core.
14. Все прикладные сущности с первого дня содержат `user_id`, даже при одном пользователе.

## 5. Карта вех

| Веха | Результат | Главный вопрос | Критерий перехода |
|---|---|---|---|
| M0. Контекст и разведка | Зафиксированы репозиторий, версия Hermes, правила работы | На чём именно строим интеграцию? | Проект поднимается, решения и неизвестные видимы |
| M1. Walking skeleton | Приложение, БД и тесты запускаются одной командой | Воспроизводится ли среда? | Чистая машина проходит smoke test |
| M2. Доменный каркас | Схемы, state machine, policy и ошибки работают без LLM | Можно ли гарантировать переходы? | Негативные тесты блокируют запрещённые действия |
| M3. Безопасный commit | Версии, confirmation и идемпотентность работают | Может ли ошибка повредить данные? | Конкурентные и повторные commit безопасны |
| M4. Первый вертикальный срез | Профиль проходит весь путь без Hermes | Правильна ли архитектура на практике? | CLI/API сценарий полностью воспроизводим |
| M5. Intent Router | Текст превращается в измеримо надёжный intent | Какой routing достаточно безопасен? | Eval-набор даёт приемлемые ошибки и ноль опасных автокоммитов |
| M6. Меню и рецепты | Модель создаёт валидируемые drafts | Может ли генерация ремонтироваться автоматически? | Golden workflow проходит на выбранной cloud-модели |
| M7. Shopping list | Покупки строятся кодом | Достаточна ли модель данных ингредиентов? | Повторный расчёт детерминирован и тестируем |
| M8. Hermes Plugin | Tools, hooks, skills и toolsets подключены к Domain Core | Где проходит реальная граница Hermes? | Контрактные тесты и один сквозной agent workflow проходят |
| M9. Telegram Alpha | Один пользователь проходит сценарий в Telegram | Безопасен ли UX свободного текста? | Все изменения требуют связанного подтверждения |
| M10. MVP hardening | Безопасность, наблюдаемость, restore и runbooks | Можно ли доверять системе ежедневно? | Полный acceptance suite зелёный |
| M11. Local-model readiness | Guided mode и model matrix | Какая минимальная модель пригодна? | Локальная модель проходит установленный порог evals |

## 6. Подробный план по этапам

## Этап 0. Зафиксировать контекст и провести техническую разведку

### Цель

Не проектировать интеграцию с вымышленным API Hermes.

### Задачи

1. Создать Git-репозиторий и перенести исходные документы в `docs/`.
2. Добавить `AGENTS.md` с правилами для coding-агента.
3. Зафиксировать точную сборку Hermes:
   - репозиторий и commit/tag;
   - способ запуска;
   - язык и версия runtime;
   - plugin API;
   - tool registration;
   - hooks;
   - sessions;
   - Telegram Gateway;
   - toolsets;
   - skills;
   - memory;
   - MCP;
   - inline/callback возможности Telegram.
4. Создать минимальный стенд Hermes без бизнес-логики.
5. Проверить одним временным tool:
   - регистрацию;
   - получение структурированных аргументов;
   - возврат структурированной ошибки;
   - ограничение toolset;
   - hook до tool call;
   - correlation ID.
6. Записать результаты в `docs/experiments/hermes-capability-spike.md`.
7. Создать ADR о способе подключения Menu Planner к Hermes.

### Не делать

- не писать полноценный plugin;
- не подключать Telegram бизнес-сценарий;
- не проектировать по памяти неизвестные интерфейсы Hermes.

### Gate M0

- точная версия Hermes воспроизводимо запускается;
- известен минимальный механизм plugin/tool/hook;
- перечислены отсутствующие возможности и нужные адаптеры;
- принято решение, остаётся ли Domain Core в том же процессе или отдельном модуле.

### Рефлексия

- Какие заявленные возможности Hermes реально подтверждены?
- Что оказалось конфигурацией, а что потребует кода?
- Можно ли изолировать пользовательский toolset без надежды на prompt?
- Нужно ли скорректировать архитектурные документы?

## Этап 1. Создать walking skeleton

### Цель

Получить пустой, но воспроизводимый проект.

### Задачи

1. Выбрать язык и версии зависимостей на основании Hermes spike.
2. Добавить менеджер зависимостей и lock-файл.
3. Добавить formatter, linter, type checker и test runner.
4. Создать `compose.yaml`:
   - приложение;
   - PostgreSQL;
   - опционально Hermes как отдельный service, если это соответствует spike.
5. Добавить `.env.example`; секреты не коммитить.
6. Добавить команды:
   - `make setup`;
   - `make up`;
   - `make test`;
   - `make lint`;
   - `make migrate`;
   - `make smoke`.
7. Создать health/readiness checks.
8. Добавить пустую миграцию и проверку подключения к БД.
9. Настроить CI на чистом окружении.
10. Добавить smoke test запуска и остановки.

### Gate M1

Новый разработчик или coding-agent по README может с чистого checkout одной последовательностью команд:

- поднять систему;
- применить миграции;
- запустить тесты;
- получить health response;
- полностью удалить локальное состояние.

### Рефлексия

- Есть ли скрытые ручные шаги?
- Зафиксированы ли версии?
- Можно ли повторить запуск после удаления volumes?
- Достаточно ли логов, чтобы LLM диагностировала падение без догадок?

## Этап 2. Описать доменные контракты

### Цель

Создать общий язык системы до интеграции модели.

### Задачи

1. Зафиксировать версионируемые схемы:
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
   - success/error envelopes tools.
2. Для каждой схемы указать:
   - `schema_version`;
   - обязательные поля;
   - enum;
   - диапазоны;
   - правила backward compatibility;
   - пример валидного объекта;
   - примеры невалидных объектов.
3. Определить стабильный каталог machine-readable ошибок.
4. Добавить contract tests на fixtures.
5. Добавить property-based тесты для идентификаторов, диапазонов и версий, если стек позволяет.

### Временные решения, допустимые для первого среза

- один пользователь;
- одна часовая зона;
- три типа приёма пищи;
- без БЖУ;
- без остатков;
- без реального магазина;
- единицы: грамм, миллилитр, штука.

Каждое временное решение помечается в схеме и журнале решений.

### Gate M2A

- все схемы валидируются независимо от модели;
- невалидный JSON не попадает в application services;
- версия схемы является обязательной;
- ошибки пригодны для автоматического repair loop.

## Этап 3. Реализовать workflow engine и policy

### Цель

Сделать допустимые действия явными и проверяемыми.

### Задачи

1. Описать state machine таблицей, а не распределёнными `if`.
2. Для каждого состояния определить:
   - разрешённые intents;
   - разрешённые application commands;
   - разрешённые tools;
   - обязательные данные;
   - допустимые переходы;
   - terminal states;
   - retry policy.
3. Реализовать operation classes:
   - `read_only`;
   - `draft_producing`;
   - `state_changing`;
   - `administrative`;
   - `unsupported`.
4. Реализовать `PolicyDecision` с причиной решения.
5. Реализовать проверку ownership по `user_id`.
6. Реализовать лимит попыток и безопасное состояние `failed`.
7. Добавить unit tests на каждый разрешённый переход.
8. Добавить негативную матрицу «каждое действие из каждого состояния».
9. Добавить архитектурный тест: adapter не может обойти application policy и вызвать repository commit напрямую.

### Gate M2B

- запрещённый переход всегда возвращает одинаковую машинную ошибку;
- административное действие невозможно из пользовательского workflow;
- бесконечный agent loop невозможен;
- state machine можно восстановить из сохранённого состояния.

### Рефлексия M2

- Какие правила оказались доменными, а какие интерфейсными?
- Есть ли состояния, существующие только из-за Telegram?
- Можно ли прогнать state machine полностью без LLM и Hermes?
- Какие переходы сложно объяснить — и значит, вероятно, они слишком сложны?

## Этап 4. Реализовать persistence, версии и безопасный commit

### Цель

Гарантировать, что повтор, конкуренция или ошибка модели не повреждают подтверждённые данные.

### Задачи

1. Создать миграции основных сущностей.
2. Реализовать repository interfaces в Domain/Application и SQL adapters снаружи.
3. Реализовать optimistic locking через `expected_version`.
4. Разделить draft и committed versions.
5. Реализовать `OperationPreview` и стабильное вычисление `summary_hash`.
6. Реализовать `Confirmation`:
   - принадлежность пользователю;
   - конкретная операция;
   - entity и версии;
   - срок действия;
   - одноразовое или идемпотентное использование;
   - статус.
7. Реализовать idempotency key для state-changing commands.
8. Реализовать транзакционный commit.
9. Записывать audit event в той же транзакции.
10. Добавить тесты:
    - повтор одного confirmation;
    - истёкший confirmation;
    - confirmation другого пользователя;
    - изменённый preview;
    - version mismatch;
    - два параллельных commit;
    - rollback транзакции при ошибке;
    - restart между preview и confirm.

### Gate M3

- подтверждённая версия не меняется без валидного confirmation;
- повтор запроса не создаёт дубликат;
- конкурентное изменение обнаруживается;
- audit позволяет восстановить причину commit;
- после restart pending confirmation обрабатывается предсказуемо.

### Точка решения

Решить, нужен ли бизнес-rollback в MVP. По умолчанию предпочтительнее создавать новую корректирующую версию, а не удалять историю.

## Этап 5. Первый вертикальный срез без LLM: профиль

### Цель

Проверить архитектуру на реальном сценарии без вероятностных компонентов.

### Сквозной сценарий

```text
structured command
→ ProfileDraft
→ validation
→ preview
→ Confirmation
→ commit
→ read committed profile
```

### Задачи

1. Выбрать минимальные поля профиля для эксперимента:
   - число людей;
   - строгие исключения;
   - мягкие предпочтения;
   - доступное оборудование;
   - базовый лимит времени;
   - locale/timezone.
2. Реализовать profile validators.
3. Реализовать application commands и queries.
4. Добавить временный CLI или test API.
5. Сделать человекочитаемый preview.
6. Пройти happy path.
7. Добавить негативные сценарии неоднозначности и конфликтов.
8. Проверить restore после перезапуска.

### Gate M4

Вертикальный сценарий выполняется без Hermes и модели, полностью покрыт тестами и демонстрирует все критические механизмы: draft, validation, workflow, preview, confirmation, commit, versioning, audit.

### Рефлексия

- Достаточно ли чисты границы Domain/Application/Adapters?
- Можно ли заменить CLI на Telegram без изменения домена?
- Можно ли добавить новый профильный intent без изменения commit-механизма?
- Какие поля профиля реально понадобились, а какие были преждевременными?

## Этап 6. Создать evaluation harness и Intent Router

### Цель

Не обсуждать качество распознавания субъективно, а измерять его.

### Задачи подготовки evals

1. Создать версионируемый набор сообщений минимум по категориям:
   - однозначные read-only;
   - draft-producing;
   - state-changing;
   - административные;
   - unsupported;
   - неполные;
   - неоднозначные;
   - конфликтующие с workflow;
   - prompt injection;
   - смешанные намерения;
   - опечатки и разговорные формулировки.
2. Для каждого сообщения зафиксировать ожидаемые:
   - intent;
   - operation class;
   - параметры;
   - missing fields;
   - ambiguities;
   - scope/persistence;
   - requires confirmation;
   - допустимое действие policy.
3. Разделить набор на development и holdout.
4. Создать runner, сохраняющий:
   - model/provider/version;
   - prompt/schema version;
   - raw output;
   - parsed output;
   - latency;
   - token usage;
   - ошибки;
   - итоговые метрики.

### Варианты для эксперимента

- A: та же модель, что и основной agent;
- B: отдельная малая модель-классификатор;
- C: правила для очевидных команд + модель для остальных;
- D: guided forms/buttons для опасных областей.

### Метрики

- exact intent accuracy;
- parameter extraction accuracy;
- ambiguity recall;
- missing-field recall;
- schema-valid rate;
- false automatic execution rate;
- false state-changing classification;
- latency и стоимость;
- стабильность на повторных запусках.

Главная safety-метрика: опасное state-changing сообщение не должно становиться автоматическим read-only или непосредственным commit.

### Confidence

Не доверять self-reported confidence без калибровки. Порог выбирать по eval-набору и классу риска. Для state-changing операций confidence не отменяет confirmation.

### Gate M5

- router всегда возвращает schema-valid результат либо контролируемую ошибку;
- административные запросы блокируются;
- неоднозначные опасные сообщения отправляются на clarification;
- выбран вариант router и записан ADR;
- пороги основаны на измерениях, а не ощущении.

### Рефлексия и решение

- Достаточно ли одной модели?
- Где правила надёжнее и дешевле LLM?
- Какие intents надо удалить или сузить?
- Какие формулировки лучше переводить в кнопки?

## Этап 7. Генерация и валидация недельного меню

### Цель

Подключить вероятностную генерацию только после готовности безопасного контура.

### Порядок реализации

1. Начать с одного дня и фиксированного числа meal slots.
2. Создать `PlanningContext` исключительно из подтверждённых данных и явных временных пожеланий.
3. Определить `MenuDraft` schema.
4. Создать model port `MenuDraftGenerator`.
5. Создать fake generator с fixtures.
6. Реализовать validators:
   - полнота периода;
   - meal slots;
   - строгие ограничения;
   - оборудование;
   - время;
   - порции;
   - повторяемость;
   - ссылочная целостность.
7. Создать bounded repair loop:
   - модель получает структурированные ошибки;
   - максимум N попыток;
   - каждая попытка логируется;
   - затем fallback или остановка.
8. Расширить с одного дня до недели.
9. Создать preview и confirmation для активации версии меню.
10. Создать golden tests на фиксированном generator и evals на реальной модели.

### Gate M6A

- модель не может активировать меню;
- невалидный draft не становится preview для commit;
- repair loop конечен;
- при полном отказе модели активное меню остаётся неизменным;
- одинаковый fixture даёт одинаковый доменный результат.

## Этап 8. Рецепты и замена отдельного блюда

### Задачи

1. Определить `RecipeDraft` schema.
2. Генерировать рецепты после подтверждения меню либо по явной политике предварительной генерации.
3. Валидировать:
   - ингредиенты и количества;
   - порции;
   - оборудование;
   - активное и полное время;
   - появление ингредиентов в шагах;
   - отсутствие новых ингредиентов только в шагах;
   - согласованность температур и методов;
   - хранение и разогрев.
4. Сохранять рецепты версионированно.
5. Реализовать замену одного meal slot как новую menu draft version.
6. После подтверждения замены пересчитывать зависимые данные.
7. Добавить тесты, что остальные meal slots не изменились.
8. Добавить тесты на stale confirmation после параллельной замены.

### Gate M6B

- замена локальна и версионирована;
- recipe generation не изменяет активное меню;
- ошибки рецепта не повреждают подтверждённые сущности;
- пользователь видит точный diff замены.

### Рефлексия M6

- Какие проверки действительно детерминированы?
- Где нужна модель-судья, а где достаточно кода?
- Насколько repair loop улучшает результат против повторной генерации?
- Не стал ли формат слишком сложным для будущей локальной модели?

## Этап 9. Детерминированный shopping list и mock-каталог

### Цель

Проверить расчёт покупок без риска и нестабильности модели.

### Задачи

1. Создать словарь нормализованных ингредиентов и единиц.
2. Реализовать преобразования только для поддерживаемых размерностей.
3. Масштабировать ингредиенты по порциям.
4. Объединять одинаковые ингредиенты.
5. Создать `StoreCatalogProvider` interface.
6. Реализовать `MockStoreCatalogProvider` со snapshot.
7. Сопоставление продуктов на первом шаге сделать фиксированным или подтверждаемым.
8. Рассчитывать упаковки и стоимость кодом.
9. Создавать shopping list version, связанную с menu version и catalog snapshot.
10. Реализовать точное изменение checklist item по ID.
11. Для текстового «молоко куплено» требовать disambiguation при нескольких совпадениях.
12. Добавить property tests для единиц, упаковок и округления.

### Gate M7

- один и тот же набор входов создаёт один и тот же список;
- список связан с конкретной версией меню и snapshot;
- арифметика не выполняется моделью;
- замена блюда создаёт предсказуемый diff списка;
- неизвестная единица приводит к контролируемой ошибке, а не догадке.

### Точка решения

После mock-каталога решить экспериментом, нужны ли цены и наличие в MVP. Реальный магазин не подключать до устойчивости нормализованного provider contract.

## Этап 10. Интеграция с Hermes

### Цель

Использовать Hermes максимально, не передавая ему полномочия Domain Core.

### Задачи

1. Создать адаптер между Hermes plugin API и application services.
2. Зарегистрировать узкие tools по доменным операциям.
3. Для каждого tool определить строгую input/output schema.
4. Разделить toolsets по состоянию и роли.
5. Реализовать pre-message policy hook.
6. Реализовать pre-tool hook.
7. Повторить критические проверки внутри handler/application service.
8. Добавить skills для:
   - intent interpretation;
   - clarification;
   - menu generation;
   - repair по validation errors;
   - объяснения preview.
9. Не помещать бизнес-правила только в skills/prompts.
10. Подключить application context из БД вместо доверия memory.
11. Сохранить два режима:
    - `agentic`: Hermes выбирает следующий разрешённый tool;
    - `guided`: workflow engine задаёт следующий шаг, модель решает локальную задачу.
12. Добавить fake model provider для integration tests.
13. Добавить contract tests на каждый tool.
14. Добавить тест, что пользовательский agent не видит административные tools.
15. Добавить тест prompt injection с попыткой вызвать terminal/SQL/commit.

### Gate M8

- Hermes вызывает только разрешённые tools;
- Domain Core отклоняет неправильный вызов даже при обходе hook;
- memory не заменяет БД;
- tool result полностью структурирован;
- agentic и guided используют одинаковые доменные команды;
- смена model provider не требует изменения домена.

### Рефлексия

- Какие возможности Hermes реально сократили код?
- Где Hermes дублирует application workflow и создаёт риск?
- Можно ли ещё сузить tools?
- Достаточно ли guided mode для слабой модели?

## Этап 11. Telegram Alpha

### Цель

Подключить пользовательский канал после готовности прикладного сценария.

### Задачи

1. Включить allowlist одного Telegram ID.
2. Привязать Telegram user/session к `user_id` и `WorkflowRun`.
3. Ограничить размер сообщения и rate limit.
4. Нормализовать даты относительно timezone пользователя.
5. Реализовать presentation layer:
   - clarification;
   - preview;
   - validation warnings;
   - status;
   - errors;
   - cancel.
6. Проверить inline buttons/callbacks установленной версии Hermes.
7. Связать callback с `confirmation_id`, а не с текстом «да».
8. Не помещать полный payload операции в callback data.
9. Реализовать защиту от повторного callback.
10. Определить политику параллельных сообщений:
    - последовательная очередь на пользователя;
    - либо явное отклонение конфликтующего действия.
11. Восстанавливать активный workflow после restart.
12. Добавить E2E-сценарии:
    - создание профиля;
    - недельное меню;
    - revision;
    - confirm;
    - recipe view;
    - shopping checklist;
    - cancel;
    - expired confirmation.

### Gate M9

Один авторизованный пользователь проходит основной сценарий только через Telegram, при этом ни одно значимое изменение не происходит без связанного preview/confirmation.

### Рефлексия

- Где свободный текст удобен, а где создаёт лишнюю неоднозначность?
- Какие действия должны остаться только кнопками?
- Что происходит при двух быстрых сообщениях?
- Понимает ли пользователь, что является draft, а что active?

## Этап 11.5. Live Telegram Alpha + Interactive UX/UI Design

### Цель

Доказать реальный Telegram round-trip и согласовать первую usable версию UI/UX
бота прямо в Telegram, а не продолжать только synthetic E2E.

Эта веха является reality gate между Telegram Alpha и MVP hardening.

Не реализовывать новые продуктовые фичи. Не переходить к production auth,
MVP hardening, observability, backup/restore, real store integration, live
prices/availability или production model rollout.

### Задачи

1. Поднять minimal live Telegram UX sandbox для одного authorized Telegram ID.
2. Проверить, что пользователь видит бота в Telegram и может открыть UX
   sandbox.
3. Показать реальные alpha screens/states в Telegram.
4. Разрешить synthetic/demo data только если production backend flow ещё не
   готов, и явно помечать такие данные как demo, not active state.
5. Сделать inline buttons visible and clickable.
6. Обрабатывать callbacks реально через live Telegram path.
7. Провести UX/UI co-design loop для крупных экранов:
   - показать текущий экран в Telegram;
   - кратко объяснить UX-логику;
   - предложить 1-3 улучшения;
   - спросить пользователя, что изменить;
   - внести правки или явно отложить;
   - снова показать обновленный экран.
8. Создать кликабельные Telegram prototypes для:
   - start / home;
   - current status;
   - profile draft;
   - profile preview;
   - menu draft;
   - menu preview;
   - validation warnings;
   - confirmation screen;
   - recipe view;
   - shopping checklist;
   - item disambiguation;
   - cancel flow;
   - expired/stale confirmation;
   - error state;
   - restart/recovery state.
9. Во время корректировок давать короткие UX-советы:
   - где лучше свободный текст;
   - где лучше inline buttons;
   - какие действия должны быть только кнопками;
   - где нужен preview;
   - где нужен confirmation;
   - где нужен disambiguation;
   - где текст слишком длинный для Telegram;
   - где лучше разбить экран на несколько сообщений;
   - где Mini App может быть полезнее;
   - где Mini App пока преждевременен и усложнит Alpha.
10. Зафиксировать Telegram UI principles:
   - каждое state-changing действие проходит через preview/confirmation;
   - draft и active state визуально различимы;
   - кнопка подтверждения всегда связана с `confirmation_id`;
   - callback data не содержит full payload;
   - destructive/cancel actions требуют явной кнопки;
   - shopping checklist updates используют stable item id;
   - неоднозначные текстовые команды ведут к disambiguation screen;
   - длинные preview/diff не превращаются в простыню текста.
11. Провести Mini App decision checkpoint:
   - какие части UX неудобны в chat-only interface;
   - какие экраны могут выиграть от Telegram Mini App;
   - что можно оставить в inline buttons;
   - нужен ли Mini App в Alpha или его стоит отложить;
   - какие риски Mini App добавит: auth, state sync, callbacks, hosting,
     testing.
12. Добавить user review checklists for manual Telegram verification:
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
   - "понятно ли, что draft, а что active" checklist.
13. Создать sanitized report:
   `docs/experiments/m9-live-telegram-ux-sandbox.md`.

### Gate M9.5

Status: completed for first-version UX/UI planning on 2026-07-13.

Stage 10.5 нельзя считать закрытой, пока:

- пользователь видит бота в Telegram;
- пользователь может открыть UX sandbox;
- пользователь может нажимать live inline buttons;
- live callback доходит до sandbox and produces visible response;
- пользователь увидел все ключевые состояния хотя бы на demo/synthetic data;
- demo/synthetic data clearly marked as demo and not active state;
- пользователь дал feedback по первой версии UX/UI;
- feedback внесен или явно отложен;
- есть sanitized report со скриншотами или описанием показанных состояний;
- есть список принятых UX-решений и открытых вопросов;
- callback data uses stable ids and no full payload;
- repeated callback не ломает состояние;
- секреты не попали в logs, reports or diffs.

Accepted result:

- first-version Telegram UX/UI is a narrow Menu Planner bot, not a generic
  prompt box;
- primary path is `Составить меню` -> `Меню составлено` -> state-aware
  `Главная`;
- active home shows current meal/recipe context, remaining shopping items and
  actions `Покупки`, `Рецепт`, `Изменить меню`, `Настройки`;
- `Изменить меню` and food settings are text-first, but text is treated only
  as user data and must lead to preview before commit;
- store price sources are managed/selectable sources, not free-form store text;
- button-only screens block free text inside the Menu Planner adapter and do
  not forward it to the generic Hermes agent;
- normal menus do not include a global `Закрыть` button.

Safety carry-forward to the next stage:

- add prompt-injection tests for text-first settings and menu editing;
- reject system/developer/tool/secret-seeking instructions in user text;
- parse only narrow settings/menu-change intent schemas;
- validate parsed intents with Application policy before preview;
- require explicit preview/confirmation plus version/hash and permission
  checks before any commit;
- keep callback data stable-id based and free of full payloads, private data
  and secrets.

### Рефлексия

- Какие экраны реально понятны в Telegram chat UI?
- Где Telegram chat превращается в перегруженный интерфейс?
- Какие действия пользователь ожидает видеть кнопками?
- Какие состояния требуют Mini App позже?
- Что должно быть изменено до MVP hardening?

## Этап 12. Безопасность, наблюдаемость и отказоустойчивость

### Задачи безопасности

1. Проверить минимальный toolset в runtime-конфигурации.
2. Запретить terminal, filesystem, произвольный browser, SQL, secrets и admin MCP.
3. Добавить тесты прямого prompt injection, включая Stage 10.5 text-first
   screens: `Изменить меню` and food settings.
4. Добавить fixtures косвенного injection из store data.
5. Добавить ownership tests на все read/write операции.
6. Добавить secret scanning и dependency scanning.
7. Ограничить и валидировать все внешние payloads.
8. Настроить timeouts и bounded retries.
9. Проверить, что text on button-only Telegram screens is blocked inside the
   Menu Planner adapter and does not fall through to the generic Hermes agent.
10. Проверить, что text-first screens parse only narrow intent schemas and
    cannot commit without preview, confirmation, version/hash and permission
    checks.

### Наблюдаемость

Логировать с correlation ID:

- user message согласно privacy policy;
- parsed intent;
- policy decision;
- workflow state и переход;
- tool call и результат;
- model/provider/version;
- schema/prompt version;
- validation errors;
- retry;
- confirmation lifecycle;
- commit;
- security denial.

Не логировать secrets и credentials. Срок хранения исходных сообщений должен быть отдельным решением.

### Отказоустойчивость

1. Убить процесс в каждой критической точке workflow и проверить восстановление.
2. Проверить недоступность модели.
3. Проверить недоступность БД.
4. Проверить malformed model output.
5. Проверить timeout Telegram callback.
6. Проверить повтор доставки сообщения.
7. Проверить миграцию со старой схемы.

### Gate M10A

- причина каждого отказа находится по correlation ID;
- секреты не попадают в логи;
- prompt injection не увеличивает полномочия;
- повторная доставка безопасна;
- модель может быть недоступна без повреждения данных.

## Этап 13. Воспроизводимое развёртывание, backup и миграция

### Задачи

1. Создать production compose или выбранный deployment manifest.
2. Зафиксировать images по версиям/digest.
3. Создать миграционный pipeline.
4. Создать backup БД.
5. Создать restore drill на чистом окружении.
6. Создать runbooks:
   - install;
   - upgrade;
   - rollback версии приложения;
   - restore БД;
   - rotate secrets;
   - смена model provider;
   - диагностика stuck workflow.
7. Исключить ручные изменения внутри контейнера.
8. Сохранять и версионировать:
   - plugin;
   - skills;
   - schemas;
   - policies;
   - model config;
   - toolsets;
   - migrations.
9. Проверить перенос на другую машину.

### Gate M10B

На чистой машине система разворачивается по документации, затем восстанавливается из backup с сохранением профиля, активного меню, workflow state и audit history.

## Этап 14. MVP acceptance и решение о следующем развитии

### Полный acceptance suite

1. Telegram allowlist работает.
2. Любой текст сначала становится structured intent.
3. Неоднозначное state-changing сообщение не выполняется.
4. Read-only запрос выполняется без лишнего confirmation только при выполнении policy.
5. Генерация создаёт draft.
6. Невалидный draft не может быть committed.
7. Preview связан с confirmation и версиями.
8. Stale/expired/foreign confirmation отклоняется.
9. Ошибка модели не изменяет active data.
10. Меню и рецепты версионируются.
11. Замена meal slot не меняет остальные слоты.
12. Shopping list строится кодом.
13. Restart не теряет подтверждённые данные.
14. Prompt injection не открывает дополнительные tools.
15. Смена cloud model выполняется конфигурацией.
16. Система разворачивается и восстанавливается на чистой машине.

### Решение после MVP

Выбрать один следующий трек, а не развивать всё одновременно:

- реальный каталог магазина;
- остатки и бюджет;
- улучшение качества меню;
- переход к локальной модели;
- несколько пользователей.

Решение принять по фактическим логам использования и evals.

## Этап 15. Подготовка к слабым локальным моделям

### Цель

Сделать переход измеримым, а не переписать приложение под конкретную модель.

### Задачи

1. Зафиксировать cloud baseline на всех eval-наборах.
2. Разделить сложные вызовы на локальные задачи:
   - intent classification;
   - parameter extraction;
   - menu draft;
   - recipe draft;
   - repair;
   - explanation.
3. Сократить schemas и prompts там, где это возможно без потери правил.
4. Включить guided mode.
5. Динамически выдавать только нужный toolset текущего состояния.
6. Сравнить несколько локальных моделей на одинаковом runner.
7. Ввести fallback policy:
   - local;
   - повтор с упрощённым prompt;
   - cloud fallback;
   - остановка и запрос пользователю.
8. Измерять качество, latency, память и стоимость.
9. Определить минимальный допустимый порог по каждой задаче, а не один общий рейтинг модели.

### Gate M11

Локальная модель может заменить cloud как минимум в одном production workflow без изменения Domain Core и без ухудшения safety-инвариантов.

## 7. Реестр неопределённостей и рекомендуемые эксперименты

| Вопрос | Первый безопасный вариант | Эксперимент | Критерий решения |
|---|---|---|---|
| Поля профиля | Минимальный профиль для вертикального среза | 3–5 реальных недель использования | Поля реально влияют на меню или валидацию |
| Где Intent Router | Application service за адаптером Hermes | Сравнить hook/tool/application orchestration | Тестируемость, отсутствие обхода policy |
| Отдельная модель router | Начать с заменяемого port | A/B на eval-наборе | Safety errors, latency, стоимость |
| Confidence threshold | Не использовать для commit | Калибровка на holdout | Максимум recall неоднозначности при допустимом UX |
| Текстовое подтверждение | Кнопка с confirmation ID | Сравнить UX после alpha | Нет ошибочных подтверждений и повторов |
| Срок confirmation | Короткий конфигурируемый TTL | Наблюдение за реальным временем ответа | Минимум истечений без роста риска stale commit |
| Параллельные сообщения | Очередь на пользователя | Stress/E2E тест | Нет гонок, понятная реакция пользователю |
| Rollback | Новая корректирующая версия | Проверить реальные сценарии ошибок | Нужен только при доказанной пользе |
| Цены в MVP | Mock snapshot без реального магазина | Пользовательский тест | Цена влияет на решения достаточно часто |
| Реальный магазин | Provider interface + mock | Spike одного источника | Законность, стабильность, качество нормализации |
| Семантическая валидация | Код + ограниченные эвристики | Сравнить с моделью-судьёй | Recall ошибок без ложной уверенности |
| Local model | Guided mode | Model matrix | Проходит порог конкретной задачи |

## 8. Формат задачи для coding-агента

Каждая issue должна содержать готовый пакет контекста.

```markdown
# Цель
Одно наблюдаемое изменение.

# Контекст
Ссылки на конкретные разделы docs, ADR и схемы.

# Разрешённая область
Список файлов/модулей, которые можно менять.

# Запрещено
Архитектурные обходы, новые зависимости, рефакторинг вне задачи.

# Контракт
Вход, выход, ошибки, side effects.

# Acceptance criteria
Проверяемые условия в Given/When/Then.

# Tests first
Какие тесты должны быть добавлены или изменены.

# Команды проверки
Точные команды lint/typecheck/test.

# Документация
Что обновить при изменении решения.

# Результат ответа агента
1. Краткое описание решения.
2. Изменённые файлы.
3. Результаты команд.
4. Риски и оставшиеся вопросы.
```

### Пример хорошей задачи

```markdown
Реализовать отклонение просроченного Confirmation.

Given Confirmation.expires_at меньше текущего времени
When application command пытается выполнить commit
Then возвращается error code CONFIRMATION_EXPIRED
And active entity version не меняется
And AuditEvent фиксирует отказ
And повторный вызов возвращает тот же безопасный результат.

Не менять Telegram adapter и model prompts.
```

## 9. Контроль качества каждого vibecoding-цикла

Перед merge обязательно:

1. Diff соответствует только заявленной задаче.
2. Новая бизнес-логика покрыта тестом.
3. Есть негативный тест.
4. Нет прямого доступа model/Hermes adapter к SQL.
5. Нет новых незафиксированных зависимостей.
6. Нет секретов и локальных путей.
7. Ошибки machine-readable.
8. Логи не содержат credentials.
9. Миграция обратима или имеет понятный recovery plan.
10. Документы не противоречат коду.
11. Все команды quality gate зелёные.
12. Coding-agent не оставил скрытых TODO без записи в backlog.

### Полезные автоматические ограничения

- dependency rules/layer tests;
- запрет импортов infrastructure из domain;
- запрет SQL вне repositories;
- schema compatibility tests;
- migration test на пустой и заполненной БД;
- maximum tool count для user toolset;
- snapshot списка разрешённых tools;
- mutation tests для критичных validators по возможности.

## 10. Вехи рефлексии и правила принятия решений

После каждой вехи проводить короткий review и фиксировать решение в Git.

### Шаблон review

```markdown
# Milestone

## Что доказано работающим
Только наблюдаемые результаты и тесты.

## Что не доказано
Предположения, ручные проверки, непокрытые сбои.

## Метрики
Tests, evals, latency, cost, incidents, manual steps.

## Архитектурные расхождения
Где реализация разошлась с concept/architecture/domain-rules.

## Удаляемый код
Какие spikes, mocks и временные обходы надо удалить.

## Решения
Принять / изменить / отложить с причиной.

## Следующая веха
Один главный риск, который проверяем далее.
```

### Stop-критерии

Остановить наращивание функций и исправить основание, если:

- state-changing операция обходит confirmation;
- модель или adapter может писать в БД;
- запрещённый tool доступен пользовательской сессии;
- workflow нельзя восстановить после restart;
- eval-набор не воспроизводим;
- schema регулярно меняется без версий;
- невозможно понять причину commit по audit;
- deployment требует ручного редактирования контейнера;
- один prompt одновременно интерпретирует, генерирует, разрешает и commit-ит.

## 11. Первые 20 конкретных задач

### P0 — начать немедленно

1. **BOOT-001:** создать репозиторий, структуру каталогов и перенести три исходных документа.
2. **BOOT-002:** написать `AGENTS.md` с архитектурными запретами и форматом задач.
3. **SPIKE-001:** зафиксировать версию Hermes и проверить plugin/tool/hook/toolset API.
4. **ADR-001:** выбрать способ интеграции Domain Core с Hermes.
5. **BOOT-003:** настроить lock-файл, lint, typecheck, tests и CI.
6. **INFRA-001:** создать compose с приложением и PostgreSQL.
7. **INFRA-002:** добавить healthcheck, migrations и smoke test.

### P1 — доменное основание

8. **SCHEMA-001:** определить общий envelope tool success/error.
9. **SCHEMA-002:** определить `ParsedIntent` v1.
10. **SCHEMA-003:** определить `WorkflowRun`, states и transitions v1.
11. **DOMAIN-001:** реализовать каталог доменных ошибок.
12. **DOMAIN-002:** реализовать operation classes и policy decision.
13. **DOMAIN-003:** реализовать state machine с табличными переходами.
14. **TEST-001:** создать негативную матрицу действий по состояниям.

### P2 — commit-контур

15. **DB-001:** миграции User, WorkflowRun, AuditEvent.
16. **DB-002:** миграции draft/version/confirmation.
17. **APP-001:** реализовать preview и `summary_hash`.
18. **APP-002:** реализовать confirmation validation.
19. **APP-003:** реализовать idempotent versioned commit.
20. **TEST-002:** concurrency, stale, expired, foreign и replay tests.

После выполнения этих 20 задач не переходить сразу к Telegram. Следующий блок — вертикальный профильный сценарий без LLM.

## 12. Рекомендуемый порядок веток и commits

- одна issue — одна короткая ветка;
- один логический commit или небольшой линейный набор;
- spike не смешивается с production code;
- generated files отделяются от ручного кода;
- миграция и код, который её использует, входят в один контролируемый change set;
- крупный refactor делается отдельно от изменения поведения;
- после milestone создаётся tag.

Пример tags:

```text
m0-hermes-spike
m1-walking-skeleton
m2-domain-policy
m3-safe-commit
m4-profile-vertical-slice
m5-intent-router
m6-menu-generation
m8-hermes-plugin
m9-telegram-alpha
m10-mvp
```

## 13. Что считать реальным прогрессом

Не считать прогрессом:

- количество написанного кода;
- длину prompt;
- красивую демонстрацию без негативных тестов;
- успешный единичный ответ модели;
- ручной запуск на одной машине;
- наличие многих tools.

Считать прогрессом:

- новый проверенный инвариант;
- пройденный сквозной сценарий;
- уменьшение неизвестности экспериментом;
- воспроизводимый тест;
- восстановление после сбоя;
- измеренное качество модели;
- возможность заменить adapter без изменения домена;
- удалённый временный обход;
- документированное решение с условием пересмотра.

## 14. Ближайшая практическая цель

Первая рабочая цель проекта — не «бот составляет меню», а:

> На чистом окружении пользовательская команда создаёт ProfileDraft, детерминированный код валидирует его, формирует preview, выдаёт Confirmation, безопасно фиксирует новую ProfileVersion и после перезапуска возвращает подтверждённый профиль с полной audit-трассой.

Когда этот сценарий устойчив, к нему последовательно подключаются Intent Router, модель, Hermes и Telegram. Такой порядок обеспечивает контролируемую эволюцию, позволяет быстро тестировать варианты и сохраняет возможность перехода на слабые локальные модели.
