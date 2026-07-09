# Menu Planner development instructions

## Sources of truth

Перед работой изучи относящиеся к задаче разделы:

- docs/concept.md
- docs/architecture.md
- docs/domain-rules.md
- docs/implementation-plan.md

Не меняй эти документы без прямого задания.

Не придумывай значения для полей, помеченных:
- [ТРЕБУЕТ РЕШЕНИЯ]
- [ТРЕБУЕТ РЕШЕНИЯ ИЛИ ПРОВЕРКИ]

Неизвестные факты фиксируй в:
docs/decisions/open-questions.md

## Deployment boundary

Hermes запускается только из готового Docker image через Docker Compose.

Запрещено:

- создавать Dockerfile для Hermes;
- использовать docker build для Hermes;
- использовать docker compose build hermes;
- создавать кастомный Hermes image;
- использовать docker commit;
- использовать docker cp для установки кода;
- устанавливать пакеты внутри Hermes container;
- редактировать файлы внутри работающего контейнера;
- создавать невоспроизводимое состояние через docker exec.

Разрешено:

- редактировать файлы на host VM;
- создавать и собирать application image/container;
- использовать docker compose build app;
- подключать файлы через bind mounts;
- использовать read-only bind mounts для кода и конфигурации;
- использовать named volumes для изменяемого runtime state;
- использовать docker compose exec только для диагностики;
- перезапускать или пересоздавать контейнер после изменения host-файлов.

## Component boundary

Hermes:
- dialog runtime;
- sessions;
- model providers;
- agent loop;
- skills;
- tools;
- hooks;
- toolsets;
- Telegram Gateway.

Menu Planner Domain Core:
- workflows;
- permissions;
- business rules;
- validation;
- calculations;
- versioning;
- confirmation;
- commit;
- idempotency.

Domain Core не импортирует Hermes или Telegram.

Application service владеет PostgreSQL schema, migrations, repositories и
transaction boundary. Hermes не применяет миграции, не пишет напрямую в
Application DB и не знает физическую схему БД.

Hermes интегрируется с Application service через HTTP API. Hermes plugin/tools
являются adapter layer и не импортируют Domain Core напрямую.

Модель не изменяет подтверждённое состояние напрямую.

## Development workflow

Для каждой задачи:

1. Прочитай относящиеся документы.
2. Сформулируй acceptance criteria.
3. Проверь фактическое состояние репозитория.
4. Сделай минимальное изменение.
5. Запусти релевантные проверки.
6. Выполни git diff --check.
7. Покажи diff summary.
8. Перечисли непроверенные предположения.

Не выполняй соседние задачи самостоятельно.

## Decision approval

Перед изменениями, которые отключают, обходят или заменяют штатные возможности
Hermes, Docker image entrypoint, s6 services, dashboard, gateway, auth flow,
model provider или runtime state layout, сначала явно спроси пользователя и
получи подтверждение.

Не принимай временные инфраструктурные обходы как целевое решение только потому,
что они уменьшают шум логов или позволяют быстрее запустить контейнер. Если
обход нужен для диагностики, зафиксируй его как диагностический эксперимент и
не оставляй в основной конфигурации без отдельного решения пользователя.

## Stage 0 restrictions

На этапе 0 разрешены только:

- подготовка среды;
- настройка Codex;
- Docker Compose;
- исследование готового Hermes image;
- bind mounts;
- capability probe;
- техническая документация;
- тесты capability spike.

Не реализуй:

- профиль;
- меню;
- рецепты;
- shopping list;
- PostgreSQL;
- production business workflows.

## Documentation lookup

Используй OpenAI Developer Docs MCP для вопросов о Codex,
OpenAI API и MCP OpenAI без отдельного напоминания.

Для Hermes не придумывай API по аналогии.
Сначала проверяй фактическую версию, CLI help, документацию
и установленный код внутри готового image.

## Completion report

В конце задачи сообщи:

- что изменено;
- какие команды запускались;
- какие проверки прошли;
- какие проверки не запускались;
- какие решения ещё не приняты.
