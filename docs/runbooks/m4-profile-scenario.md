# M4 profile scenario runbook

This runbook describes the temporary M4 command for the deterministic profile
vertical slice. It is intentionally not a Hermes plugin, Telegram UX, Intent
Router, LLM flow, menu workflow, recipe workflow, or shopping list workflow.

## Boundary

The command runs this chain:

```text
structured command -> ProfileDraft -> validation -> preview -> Confirmation
-> safe commit -> committed ProfileVersion read-back
```

The command uses the application database through `DATABASE_URL` from the app
runtime. It does not require OpenAI keys, Telegram tokens, Hermes sessions, or
model provider credentials. Do not print or copy local `.env` values when
sharing command output.

## Prerequisites

Apply migrations before running the scenario:

```bash
scripts/dev.sh migrate
```

Run the command in the application container:

```bash
docker compose run --rm app python -m menu_planner.bootstrap.profile_cli \
  --user-id user_001 \
  --run-id m4_profile_cli \
  --idempotency-key m4-profile-cli:user_001:v1 \
  --expires-at 2026-07-10T12:05:00+00:00 \
  --now 2026-07-10T12:00:00+00:00
```

Expected result:

- exit code `0`;
- JSON output with `"ok": true`;
- `profile_id` is `profile:user_001`;
- `profile_version` is `1`;
- no database URL or secret value is printed.

Run the same command again with the same arguments to verify idempotency replay.
The second result should still exit `0` and include:

```json
{"ok": true, "replayed": true, "reused_confirmation": true, "reused_draft": true}
```

The replay must not create a duplicate committed profile version.
