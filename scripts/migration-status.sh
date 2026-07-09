#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required to check migration status}"

python3 -m alembic -c alembic.ini current
