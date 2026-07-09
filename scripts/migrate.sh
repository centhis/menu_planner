#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required to run migrations}"

python3 -m alembic -c alembic.ini upgrade head
