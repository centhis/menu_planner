# Menu Planner for Hermes

Персональный планировщик меню на базе Hermes Agent.

## Runtime Model

Hermes запускается из готового Docker image через Docker Compose.

Проект не использует собственный Dockerfile для Hermes и не собирает Hermes
image.

Application service является отдельным project-owned container. Его image
можно и нужно собирать, потому что зависимости устанавливаются внутри app
container.

Интеграция Hermes с Menu Planner идёт через Application HTTP API.

Application service владеет PostgreSQL schema, migrations, repositories и
transaction boundary.

Изменяемое состояние хранится в named volumes или PostgreSQL. Ручные изменения
внутри работающих контейнеров запрещены.

## Current Stage

Stage 1 / M1 walking skeleton: application container, PostgreSQL, migrations,
health/readiness, tests, lint/typecheck, and smoke checks.
