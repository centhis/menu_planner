# Техническая концепция Menu Planner for Hermes

**Версия:** 0.2  
**Статус:** архитектурный контекст для человека и LLM-разработчика

## 1. Архитектурная позиция

Hermes Agent является основным runtime решения.

Максимально используются:

- Telegram Gateway;
- sessions;
- model providers;
- agent loop;
- tools;
- skills;
- plugins;
- hooks;
- memory;
- toolsets;
- MCP.

Прикладная функциональность реализуется как версионируемый Menu Planner Plugin и независимое от Telegram доменное ядро.

## 2. Основная схема

```text
Telegram user text
    ↓
Hermes Telegram Gateway
    ↓
Input Policy / Intent Router
    ↓
Structured Intent
    ↓
Workflow Policy
    ├── current state
    ├── allowed actions
    ├── required fields
    ├── permission level
    └── confirmation policy
    ↓
Hermes Agent Runtime
    ├── interpret
    ├── propose
    ├── explain
    └── revise
    ↓
Menu Planner Tools
    ↓
Domain Core
    ├── validation
    ├── calculations
    ├── repositories
    ├── workflows
    └── commit
```

## 3. Границы компонентов

### 3.1. Telegram Gateway

Отвечает за:

- получение сообщений;
- доставку ответов;
- идентификацию пользователя;
- привязку к сессии;
- транспортные ограничения Telegram.

Не отвечает за бизнес-валидацию и commit.

### 3.2. Input Policy / Intent Router

Новый обязательный слой между сырым текстом и прикладными tools.

Отвечает за:

- определение intent;
- извлечение параметров;
- оценку уверенности;
- поиск неоднозначностей;
- классификацию операции;
- проверку допустимости в текущем состоянии;
- выбор: выполнить read-only, создать draft, запросить уточнение или запросить подтверждение.

Результат всегда структурирован.

### 3.3. Hermes Agent Runtime

Отвечает за:

- работу с моделью;
- агентный цикл;
- применение skills;
- выбор разрешённых tools;
- объяснения;
- исправление черновиков.

Не определяет окончательные разрешения и не изменяет базу напрямую.

### 3.4. Menu Planner Plugin

Регистрирует:

- tools;
- tool schemas;
- hooks;
- commands;
- skills;
- адаптер между Hermes и Domain Core.

### 3.5. Domain Core

Источник истины для:

- workflows;
- разрешённых переходов;
- business rules;
- валидации;
- арифметики;
- commit;
- версионирования;
- идемпотентности.

## 4. Контроль свободного текста

### 4.1. Свободный текст не вызывает tools напрямую

Запрещена схема:

```text
message → model → arbitrary tool execution
```

Разрешена схема:

```text
message
→ structured intent
→ policy check
→ restricted toolset
→ domain validation
```

### 4.2. Intent schema

**[ПРЕДЛОЖЕНИЕ]**

```json
{
  "intent": "replace_meal",
  "confidence": 0.93,
  "parameters": {},
  "missing_fields": [],
  "ambiguities": [],
  "operation_class": "state_changing",
  "requires_confirmation": true,
  "suggested_next_action": "create_revision_draft"
}
```

### 4.3. Operation classes

```text
read_only
draft_producing
state_changing
administrative
unsupported
```

### 4.4. Routing rules

```text
read_only + high confidence + complete parameters
→ execute read tool

draft_producing + valid context
→ run workflow and create draft

state_changing
→ create preview and confirmation object

administrative
→ deny in user channel or route to admin channel

ambiguous / incomplete
→ ask clarification
```

## 5. Workflow engine

State machine хранит:

- текущее состояние;
- разрешённые intents;
- разрешённые tools;
- число попыток;
- черновики;
- ошибки;
- confirmation status;
- возможность восстановления после перезапуска.

Пример состояний:

```text
profile_required
profile_waiting_confirmation
context_preparing
menu_generating
menu_validating
menu_revision_required
menu_waiting_confirmation
recipes_generating
recipes_validating
products_matching
shopping_list_building
ready
failed
cancelled
```

Каждый tool handler повторно проверяет состояние. Нельзя полагаться только на корректность модели.

## 6. Подтверждение и commit

Для state-changing операций создаётся `Confirmation`.

Поля:

- `confirmation_id`;
- `user_id`;
- `operation`;
- `entity_id`;
- `expected_version`;
- `draft_version`;
- `expires_at`;
- `summary_hash`;
- `status`.

Commit tool проверяет:

- пользователя;
- срок;
- неизменность preview;
- ожидаемую версию;
- текущий workflow;
- идемпотентность;
- права;
- доменные инварианты.

## 7. Toolsets и минимальные полномочия

Для обычной Telegram-сессии доступен только прикладной toolset.

Пример:

```text
menu_profile_*
menu_planning_*
menu_recipe_*
menu_shopping_*
menu_store_search
menu_workflow_status
menu_clarify
```

По умолчанию недоступны:

- terminal;
- произвольный filesystem;
- произвольный browser;
- установка skills;
- изменение toolsets;
- изменение моделей;
- secrets;
- произвольный SQL;
- административные MCP tools.

## 8. Hooks и policy layer

### 8.1. До обработки входящего сообщения

Проверки:

- allowlist;
- размер сообщения;
- rate limit;
- допустимость канала;
- привязка к пользователю;
- текущий workflow;
- попытка административной команды.

### 8.2. До tool call

Проверки:

- tool входит в активный toolset;
- tool разрешён текущим состоянием;
- пользователь имеет право;
- параметры валидны;
- операция не требует предварительного confirmation;
- отсутствует доступ к секретам;
- есть correlation ID.

### 8.3. Внутри tool handler

Все критические проверки повторяются независимо от hooks.

Hook — дополнительный слой, а не единственная граница безопасности.

## 9. Защита от prompt injection

### Прямой injection

Пользовательский текст может содержать инструкции игнорировать правила. Такие инструкции не должны предоставлять дополнительных полномочий.

Защита:

- минимальный toolset;
- whitelist tools по состоянию;
- отсутствие terminal;
- policy hooks;
- доменные проверки;
- отдельный административный контур.

### Косвенный injection

HTML, страницы магазинов, документы и API-ответы считаются недоверенными данными.

Модели передаются нормализованные карточки, а не сырые страницы, если это возможно.

Внешний текст не может:

- менять системные инструкции;
- добавлять tools;
- инициировать commit;
- запрашивать секреты;
- изменять workflow.

## 10. Модель tools

### 10.1. Intent и clarification

```text
menu_intent_parse
menu_clarification_submit
menu_operation_preview_get
menu_operation_confirm
menu_operation_cancel
```

### 10.2. Профиль

```text
menu_profile_get
menu_profile_create_draft
menu_profile_update_draft
menu_profile_validate
menu_profile_commit
```

### 10.3. Меню

```text
menu_planning_context_create
menu_draft_submit
menu_draft_get_validation
menu_draft_replace_fragment
menu_draft_request_confirmation
menu_draft_commit
```

### 10.4. Рецепты

```text
menu_recipe_context_get
menu_recipe_draft_submit
menu_recipe_validation_get
menu_recipe_commit
```

### 10.5. Покупки

```text
menu_shopping_list_build
menu_shopping_list_get
menu_shopping_item_toggle
menu_shopping_item_add
menu_shopping_item_remove
```

### 10.6. Диагностика

```text
menu_workflow_status_get
menu_validation_errors_get
menu_workflow_cancel
```

## 11. Контракты tools

Успех:

```json
{
  "success": true,
  "operation_id": "op_001",
  "entity_id": "menu_001",
  "entity_version": 3,
  "data": {},
  "warnings": [],
  "next_allowed_actions": ["request_user_confirmation"]
}
```

Ошибка:

```json
{
  "success": false,
  "operation_id": "op_001",
  "error_type": "validation",
  "retryable": true,
  "errors": [
    {
      "code": "ACTION_NOT_ALLOWED_IN_CURRENT_STATE",
      "path": null,
      "message": "Operation is not allowed",
      "expected": "request_revision",
      "actual": "commit_menu"
    }
  ],
  "next_allowed_actions": ["request_revision", "cancel_workflow"]
}
```

## 12. Агентный и управляемый режимы

### Agentic mode

Hermes выбирает следующий tool внутри разрешённого workflow.

Подходит для сильных моделей.

### Guided mode

State machine определяет следующий этап, а модель решает только локальную задачу.

Подходит для слабых локальных моделей.

Оба режима используют одинаковые:

- intents;
- tools;
- schemas;
- validators;
- confirmation model;
- repositories;
- commit rules.

## 13. Хранение данных

**[ПРЕДЛОЖЕНИЕ]** PostgreSQL.

Дополнительные сущности для свободного текста:

```text
UserMessage
ParsedIntent
ClarificationRequest
OperationPreview
Confirmation
PolicyDecision
```

Основные сущности:

```text
User
UserProfile
ProfileVersion
Menu
MenuVersion
Recipe
RecipeVersion
ShoppingList
ShoppingListVersion
ShoppingListItem
StoreCatalogSnapshot
StoreProduct
WorkflowRun
ModelInvocation
ValidationResult
AuditEvent
```

## 14. Память Hermes

Память используется для разговорного удобства, но прикладной контекст формируется из базы.

Запись критичных фактов в memory не заменяет `profile_commit`.

Желательно, чтобы для каждого workflow в prompt явно добавлялся актуальный структурированный профиль из базы.

## 15. Интеграции с магазинами

Первый этап:

```text
StoreCatalogProvider
└── MockStoreCatalogProvider
```

Дальнейшее развитие:

```text
Hermes
    ↓ MCP
Store Catalog Service
    ├── adapters
    ├── normalization
    ├── cache
    └── scheduler
```

Модель получает нормализованные данные, а не произвольный browser-доступ.

## 16. Наблюдаемость

Логировать:

- исходное сообщение с учётом политики приватности;
- parsed intent;
- confidence;
- ambiguities;
- policy decision;
- workflow state;
- tool calls;
- validation errors;
- confirmation creation and use;
- model/provider/version;
- retries;
- commit;
- отказ по безопасности.

Не логировать секреты и credentials.

## 17. Тестирование

### Intent tests

Фиксированный набор пользовательских сообщений:

- однозначные;
- неоднозначные;
- конфликтующие;
- с попытками административных инструкций;
- с prompt injection;
- с неполными параметрами.

Проверяется:

- intent;
- operation class;
- required clarification;
- запрет автоматического commit;
- стабильность на разных моделях.

### Policy tests

Проверяется, что:

- disallowed tool блокируется;
- commit без confirmation невозможен;
- старый confirmation не работает;
- version mismatch отклоняется;
- чужая сущность недоступна;
- административный запрос не попадает в пользовательский workflow.

### Golden workflow tests

Проверяется полный путь:

```text
text
→ intent
→ draft
→ validation
→ preview
→ confirmation
→ commit
```

## 18. Развёртывание и миграция

Система поставляется как:

```text
Hermes Agent
+ versioned plugin
+ versioned skills
+ domain core
+ database migrations
+ Docker configuration
+ test suite
+ documentation
```

Не допускаются ручные изменения внутри контейнера.

При переносе сохраняются:

- БД;
- plugin version;
- skill versions;
- schemas;
- model configuration;
- toolset configuration;
- policy configuration;
- migration state.

## 19. Открытые технические вопросы

**[ТРЕБУЕТ РЕШЕНИЯ ИЛИ ПРОВЕРКИ]**

1. Где реализуется Intent Router: отдельный tool, hook или application service.
2. Используется ли та же модель или отдельная малая модель-классификатор.
3. Пороги confidence.
4. Формат callback и `confirmation_id` в Telegram Gateway.
5. Поддержка inline-кнопок установленной версией Hermes.
6. Поведение при параллельных сообщениях пользователя.
7. Нужна ли очередь входящих сообщений во время активного workflow.
8. Срок хранения исходных сообщений и parsed intents.
9. Нужна ли шифрация отдельных полей профиля.
10. Как изолировать административный Hermes-профиль.
11. Как ограничить browser и MCP tools на уровне конфигурации установленной версии.
12. Как тестировать prompt injection на выбранной модели.

## 20. Инструкции для LLM-разработчика

1. Не трактовать свободный текст как прямой commit.
2. Сначала создавать structured intent.
3. При неоднозначности задавать уточнение.
4. Read-only и state-changing операции обрабатывать по-разному.
5. Любая генерация создаёт draft.
6. Любой commit требует доменной проверки.
7. Значимые изменения требуют preview и confirmation.
8. Не полагаться на system prompt как на единственную защиту.
9. Не давать пользовательской сессии административные tools.
10. Дублировать критические проверки в tool handlers.
11. Не передавать модели сырой HTML магазина без необходимости.
12. Считать внешние данные недоверенными.
13. Поддерживать agentic и guided режимы.
14. Не придумывать значения полей с пометкой **[ТРЕБУЕТ РЕШЕНИЯ]**.
