#!/usr/bin/env sh
set -eu

COMPOSE="${COMPOSE:-docker compose}"
PYTHON="${PYTHON:-python3}"

require_line() {
    label="$1"
    expected="$2"
    actual="$3"

    if ! printf '%s\n' "$actual" | grep -Fx "$expected" >/dev/null 2>&1; then
        echo "smoke failed: expected $label to include '$expected'" >&2
        exit 1
    fi
}

compose_services() {
    # shellcheck disable=SC2086
    $COMPOSE config --services
}

compose_images() {
    # shellcheck disable=SC2086
    $COMPOSE config --images
}

compose_volumes() {
    # shellcheck disable=SC2086
    $COMPOSE config --volumes
}

check_compose_contract() {
    services="$(compose_services)"
    images="$(compose_images)"
    volumes="$(compose_volumes)"

    require_line "compose services" "hermes" "$services"
    require_line "compose services" "postgres" "$services"
    require_line "compose images" "nousresearch/hermes-agent:v2026.6.19" "$images"
    require_line "compose images" "postgres:16-alpine" "$images"
    require_line "compose images" "menu-planner-app:local" "$images"
    require_line "compose volumes" "hermes-data" "$volumes"
    require_line "compose volumes" "postgres-data" "$volumes"

    hermes_block="$(sed -n '/^  hermes:/,/^  postgres:/p' compose.yaml)"
    if printf '%s\n' "$hermes_block" | grep -n '^[[:space:]]*build[[:space:]]*:' >/dev/null 2>&1; then
        echo "smoke failed: hermes service must not contain build:" >&2
        exit 1
    fi

    if printf '%s\n' "$hermes_block" | grep -n 'menu-planner-probe' >/dev/null 2>&1; then
        echo "smoke failed: Stage 0 probe plugin must not be mounted in default runtime" >&2
        exit 1
    fi

    app_block="$(sed -n '/^  app:/,/^volumes:/p' compose.yaml)"
    if ! printf '%s\n' "$app_block" | grep -n 'dockerfile: Dockerfile.app' >/dev/null 2>&1; then
        echo "smoke failed: app service must build only Dockerfile.app" >&2
        exit 1
    fi

    dockerfiles="$(find . -iname 'Dockerfile*' -print)"
    if [ "$dockerfiles" != "./Dockerfile.app" ]; then
        echo "smoke failed: only application Dockerfile.app is allowed in M1" >&2
        printf '%s\n' "$dockerfiles" >&2
        exit 1
    fi
}

check_unit_tests() {
    scripts/dev.sh test
}

check_application_health_logic() {
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$PYTHON" -m tests.smoke.application_health
}

check_postgres_if_running() {
    # shellcheck disable=SC2086
    if ! ps_output="$($COMPOSE ps --status running --services 2>&1)"; then
        echo "deferred: Docker runtime is unavailable for DB smoke: $ps_output"
        return 0
    fi

    if printf '%s\n' "$ps_output" | grep -Fx postgres >/dev/null 2>&1; then
        # shellcheck disable=SC2086
        $COMPOSE exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
    else
        echo "deferred: postgres container is not running; run scripts/dev.sh up before DB smoke"
    fi
}

check_migration_status_if_available() {
    scripts/dev.sh migration-status
}

check_http_if_running() {
    # shellcheck disable=SC2086
    if ! ps_output="$($COMPOSE ps --status running --services 2>&1)"; then
        echo "deferred: Docker runtime is unavailable for HTTP smoke: $ps_output"
        return 0
    fi

    if printf '%s\n' "$ps_output" | grep -Fx app >/dev/null 2>&1; then
        "$PYTHON" scripts/http-smoke.py
    else
        echo "deferred: app container is not running; run scripts/dev.sh up before HTTP smoke"
    fi
}

check_compose_contract
check_unit_tests
check_application_health_logic
check_postgres_if_running
check_http_if_running
check_migration_status_if_available

echo "smoke ok: compose, skeleton tests, app health logic, DB, HTTP, and migration checks passed"
