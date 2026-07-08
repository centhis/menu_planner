#!/bin/sh
set -eu

export HERMES_HOME="${HERMES_HOME:-/opt/data}"
export HERMES_WRITE_SAFE_ROOT="${HERMES_WRITE_SAFE_ROOT:-$HERMES_HOME}"
export HOME="${HOME:-$HERMES_HOME}"
export PATH="/opt/hermes/bin:/opt/hermes/.venv/bin:$HERMES_HOME/.local/bin:$PATH"

if [ -d "$HERMES_HOME" ] && [ "$(id -u)" = 0 ] && id hermes >/dev/null 2>&1; then
    chown -R hermes:hermes "$HERMES_HOME"
fi

run_hermes() {
    if [ "$(id -u)" = 0 ] && command -v s6-setuidgid >/dev/null 2>&1 && id hermes >/dev/null 2>&1; then
        s6-setuidgid hermes /opt/hermes/hermes "$@"
    else
        /opt/hermes/hermes "$@"
    fi
}

exec_hermes() {
    if [ "$(id -u)" = 0 ] && command -v s6-setuidgid >/dev/null 2>&1 && id hermes >/dev/null 2>&1; then
        exec s6-setuidgid hermes /opt/hermes/hermes "$@"
    else
        exec /opt/hermes/hermes "$@"
    fi
}

is_enabled() {
    case "${HERMES_USE_CODEX_AUTH:-0}" in
        1|true|TRUE|yes|YES|on|ON) return 0 ;;
        *) return 1 ;;
    esac
}

check_codex_auth() {
    run_hermes auth status openai-codex 2>&1 || true
}

if is_enabled; then
    echo "[hermes] HERMES_USE_CODEX_AUTH=1; checking openai-codex auth..."
    status="$(check_codex_auth)"
    printf '%s\n' "$status"

    if printf '%s\n' "$status" | grep -qi 'logged in'; then
        echo "[hermes] openai-codex auth is configured."
    else
        cat <<'EOF'
[hermes] openai-codex auth is not configured or is not usable.
[hermes] Starting Hermes device-code authorization.
[hermes] Follow the OpenAI URL and enter the device code printed below.
EOF
        if ! run_hermes auth add openai-codex; then
            echo "[hermes] ERROR: openai-codex device-code authorization did not complete; gateway was not started." >&2
            exit 1
        fi

        status="$(check_codex_auth)"
        printf '%s\n' "$status"
        if ! printf '%s\n' "$status" | grep -qi 'logged in'; then
            echo "[hermes] ERROR: openai-codex auth is still not configured after device-code flow." >&2
            exit 1
        fi
    fi
else
    echo "[hermes] HERMES_USE_CODEX_AUTH is disabled; skipping openai-codex auth check."
fi

exec_hermes "$@"
