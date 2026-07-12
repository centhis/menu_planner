# M9 Telegram Alpha Report

Date: 2026-07-12

## Goal

M9 verifies that one authorized Telegram Alpha user can move through the main
Menu Planner UX shape while meaningful state changes remain gated by preview,
stable identifiers, `confirmation_id`, expected version/hash and Application
checks.

The stage intentionally stops at Telegram Alpha. Do not proceed to MVP
hardening, production deployment, production auth, observability, backup work,
real store integration or production model rollout without a separate user
request.

## Scope

Included:

- one-user allowlist and Telegram session binding;
- message size, rate-limit and timezone normalization;
- Telegram presentation layer for clarification, preview, warnings, status,
  errors, cancel, recipe view, shopping checklist and restart recovery;
- confirmation-bound callbacks and checklist callbacks with stable ids;
- explicit conflict rejection for parallel state-changing actions;
- restart recovery from Application-facing resolver contracts;
- provider-free synthetic Telegram Alpha E2E transcript.

Not included:

- public registration or multi-user production auth;
- live Telegram token or real Telegram network test;
- real store integration, live prices or availability;
- production hardening, backup/restore, observability or alerting;
- production model/provider selection;
- direct Telegram adapter DB writes;
- custom Hermes image or mutable container changes.

## Capability Evidence

Telegram/Hermes discovery is recorded in
`docs/experiments/m9-telegram-capability-discovery.md`.

Key non-secret evidence:

- current Hermes image: `nousresearch/hermes-agent:v2026.6.19`;
- Hermes version: `v0.17.0 (2026.6.19)`;
- Telegram adapter exposes inbound user/chat/message/thread metadata;
- installed Telegram adapter supports inline buttons and callback queries;
- built-in callback namespaces include slash confirmations and clarifications;
- installed source records Telegram `callback_data` limit as 64 bytes;
- live Menu Planner callback round trip was not proven in M9.

Gate M9 therefore uses a synthetic provider-free Telegram Alpha E2E harness:

```sh
scripts/dev.sh m9-telegram-alpha-e2e
```

Transcript:

```text
docs/experiments/m9-telegram-alpha-transcript.json
```

## Decisions

Allowlist and identity:

- exactly one Telegram Alpha user is allowed by configuration;
- reports expose only whether the allowlist is configured, not its value;
- Telegram transport identity is mapped to Application `user_id`;
- active session is bound to `WorkflowRun`.

Presentation and callbacks:

- free text may start draft-producing/read-only flows but does not commit;
- meaningful state changes require preview and confirmation references;
- confirmation callbacks carry `confirmation_id`, expected version and hash;
- checklist callbacks carry stable `shopping_item_id` and action only;
- callback data never carries full operation payloads or secrets.

Parallel messages:

- ADR-0012 selects explicit conflict rejection, not queueing;
- conflicting state-changing text or callbacks return
  `conflicting_action_in_progress`;
- read-only status/help can be allowed later if it remains non-mutating.

Restart recovery:

- recovery reloads `WorkflowRun` and pending confirmation through
  Application-facing resolver contracts;
- in-memory Telegram/Hermes session state is not source of truth;
- expired, consumed, wrong-user and wrong-workflow confirmations are not
  resumable.

## E2E Metrics

Synthetic E2E result:

- command: `scripts/dev.sh m9-telegram-alpha-e2e`;
- result: passed;
- provider: synthetic;
- Telegram network used: false;
- credentials used: false;
- direct DB writes: false;
- meaningful changes require confirmation: true.

Covered scenarios:

- create/update profile;
- generate menu or accepted menu path;
- revision;
- confirm;
- recipe view;
- shopping checklist;
- cancel;
- expired confirmation;
- restart recovery.

Deviation:

- live Telegram E2E was not run because M9 must not read or print a real bot
  token and no approved live-token run was requested.

## Commands Run

Relevant commands run during M9 implementation and gate checks:

```sh
docker compose ps
docker compose config --services
docker run --rm nousresearch/hermes-agent:v2026.6.19 hermes --version
scripts/dev.sh m9-telegram-alpha-e2e
PYTHONPATH=src python3 -m unittest tests.unit.test_telegram_alpha
PYTHONPATH=src python3 -m unittest tests.unit.test_m9_telegram_alpha_e2e_script
PYTHONPATH=src python3 -m unittest tests.unit.domain.test_import_boundaries
PYTHONPATH=src python3 -m unittest \
  tests.unit.domain.test_import_boundaries \
  tests.unit.test_telegram_alpha \
  tests.unit.test_m9_telegram_alpha_e2e_script \
  tests.unit.test_makefile
PYTHONPATH=src python3 -m py_compile \
  src/menu_planner/application/telegram_alpha.py \
  tests/unit/test_telegram_alpha.py
PYTHONPATH=src python3 -m py_compile \
  scripts/m9_telegram_alpha_e2e.py \
  tests/unit/test_m9_telegram_alpha_e2e_script.py
python3 -m json.tool fixtures/telegram_alpha/presentation.v1.json
python3 -m json.tool docs/experiments/m9-telegram-alpha-transcript.json
sh -n scripts/dev.sh
git diff --check
```

Stage-gate deviations:

- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck` and
  `scripts/dev.sh smoke` were not run in step 13; targeted unit, syntax,
  JSON, E2E and boundary checks were run instead.
- Live Telegram E2E was replaced by synthetic E2E with recorded reason.

## Gate M9 Checklist

[x] M9 Codex skill exists and was used for implementation tasks.
[x] M9 brief exists and was used for routine tasks.
[x] ADR-0012 or equivalent decision note fixes Telegram Alpha strategy.
[x] Installed Hermes Telegram/callback capability was inspected and recorded.
[x] Exactly one authorized Telegram ID is allowed for alpha.
[x] Telegram user/session maps to `user_id` and `WorkflowRun`.
[x] Message size limit is enforced.
[x] Rate/concurrency policy is deterministic.
[x] Dates are normalized relative to user timezone.
[x] Presentation layer covers clarification, preview, warnings, status, errors,
    cancel, recipe view and shopping checklist.
[x] Callback data references stable ids and not full operation payloads.
[x] Confirmation callbacks bind to `confirmation_id` and expected version/hash.
[x] Expired/stale confirmations are rejected.
[x] Repeated callbacks do not duplicate state changes.
[x] Parallel messages are queued or rejected according to ADR-0012.
[x] Active workflow restart recovery works or limitation is recorded.
[x] Telegram E2E alpha covers profile, menu, revision, confirm, recipe view,
    shopping checklist, cancel and expired confirmation, or deviations are
    recorded.
[x] No meaningful state change occurs without linked preview/confirmation.
[x] Telegram adapter does not import Domain Core or write Application DB.
[x] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[x] No public registration, multi-user production auth, real store integration,
    production hardening or production model rollout added.
[x] `scripts/dev.sh test` passed or deviation recorded.
[x] `scripts/dev.sh lint` passed or deviation recorded.
[x] `scripts/dev.sh typecheck` passed or deviation recorded.
[x] `scripts/dev.sh smoke` passed or deviation recorded.
[x] Telegram E2E alpha command passed or skipped with reason.
[x] `git diff --check` passed.

Deviations for unchecked gate commands are recorded in "Commands Run".

## Reflection M9

### Where is free text convenient, and where is it ambiguous?

Free text is convenient for starting low-risk intents such as profile edits,
menu generation requests, revision requests, status requests and simple
shopping text like "milk bought" when one deterministic item match exists.

Free text becomes ambiguous for shopping list updates when multiple items match,
for confirmations, for destructive/replacing actions and for any state change
where the user must understand draft versus active state.

### Which actions should remain button-only?

Confirmation, cancel, exact checklist item updates and disambiguation choices
should remain button/callback oriented whenever Telegram supports them. They
need stable ids, short callback payloads and Application checks, not display
text such as "yes".

### What happens with two quick messages?

M9 rejects conflicting state-changing messages and callbacks with
`conflicting_action_in_progress`. Queueing is deferred. The user-facing response
asks the user to finish or cancel the current action.

### Does the user understand draft versus active state?

The preview presentation explicitly says: "This is draft state, not active
state." Status presentation separates draft state from active state. The E2E
transcript records profile/menu previews as not changing state before
confirmation.

### What decisions are needed before MVP hardening?

- Run a live Telegram round trip with sanitized evidence, if the user approves
  use of a real bot token.
- Decide production callback strategy: Hermes built-in slash confirmations,
  project-owned callback adapter or another bridge.
- Choose production auth and allowlist/user management.
- Define the live Application HTTP API for workflow recovery, pending
  confirmation lookup and commit.
- Decide operational hardening scope: dashboard auth, observability, backups,
  deployment and incident handling.
- Decide production model/provider rollout separately from Telegram Alpha.

## Remaining Assumptions

- The one-user allowlist is configured outside Git and reported only as a
  boolean/sanitized fact.
- Synthetic E2E is sufficient for Gate M9 because live Telegram token use was
  not requested.
- Application service remains the final authority for persistence, workflow
  state, confirmation validity and commits.
- Live Telegram callback behavior may differ from the synthetic callback path;
  OQ-010 records the remaining live/runtime decisions.

## Gate M9 Result

Gate M9 is conditionally passed for the synthetic Telegram Alpha slice.

The project should stop here until the user explicitly requests the next stage
or MVP hardening. No production work should be started implicitly.
