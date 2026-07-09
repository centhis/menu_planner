# Application DB migrations

This directory contains Alembic migrations for the Menu Planner application
database.

M1 starts with an empty baseline migration. Do not add profile, menu, recipe,
shopping list, workflow, confirmation, or other business tables during M1.

Use:

```bash
scripts/migrate.sh
scripts/migration-status.sh
```

Both commands expect `DATABASE_URL` in the environment. In Docker Compose,
future app and migration services should reuse the `x-application-db-environment`
block from `compose.yaml` instead of asking operators to duplicate connection
settings.

