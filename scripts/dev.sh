#!/usr/bin/env sh
set -eu

COMPOSE="${COMPOSE:-docker compose}"
PYTHON="${PYTHON:-python3}"

usage() {
    cat <<'USAGE'
Menu Planner M1 commands:
  setup             Validate local command prerequisites and Compose config
  up                Start M1 runtime services that exist today
  down              Stop runtime services without deleting volumes
  test              Run unit tests for the current skeleton
  lint              Run Ruff when available, otherwise explain deferral
  typecheck         Run mypy when available, otherwise explain deferral
  migrate           Run Alembic when available and DATABASE_URL is set
  smoke             Run the current non-destructive smoke checks
  m5-eval           Run the M5 Intent Router eval skeleton
  m6a-eval          Run the M6A menu draft generation golden eval
  check             Run local CI-equivalent checks available for M1
  clean             Remove generated Python bytecode caches
  clean-runtime     Stop services; volumes are intentionally retained
USAGE
}

compose_config_quiet() {
    # shellcheck disable=SC2086
    $COMPOSE config --services >/dev/null
}

app_run() {
    # shellcheck disable=SC2086
    $COMPOSE run --rm app "$@"
}

cmd="${1:-help}"

case "$cmd" in
    help)
        usage
        ;;
    setup)
        "$PYTHON" --version
        compose_config_quiet
        echo "setup ok: Python and Docker Compose config are available"
        ;;
    up)
        # shellcheck disable=SC2086
        $COMPOSE up -d postgres app
        ;;
    down)
        # shellcheck disable=SC2086
        $COMPOSE down
        ;;
    test)
        app_run python -m pytest tests/unit tests/contract
        ;;
    lint)
        app_run python -m ruff check src tests migrations
        ;;
    typecheck)
        app_run python -m mypy src tests migrations
        ;;
    format)
        app_run python -m ruff format src tests migrations
        ;;
    format-check)
        app_run python -m ruff format --check src tests migrations
        ;;
    migrate)
        app_run scripts/migrate.sh
        ;;
    migration-status)
        app_run scripts/migration-status.sh
        ;;
    smoke)
        scripts/smoke.sh
        ;;
    m5-eval)
        shift
        app_run python -m menu_planner.bootstrap.intent_eval_cli "$@"
        ;;
    m6a-eval)
        shift
        app_run python -m menu_planner.bootstrap.menu_eval_cli "$@"
        ;;
    check)
        "$0" format-check
        "$0" lint
        "$0" typecheck
        "$0" test
        "$0" smoke
        ;;
    clean)
        find src tests migrations -type d -name __pycache__ -prune -exec rm -r {} +
        ;;
    clean-runtime)
        "$0" down
        echo "runtime stopped; named volumes are retained by design"
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
