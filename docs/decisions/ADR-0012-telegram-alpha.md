# ADR-0012: Telegram Alpha strategy

Date: 2026-07-12

Status: Accepted

## Context

Stage 10 / M9 moves from the provider-free Hermes plugin boundary to a
one-user Telegram Alpha. The risk is mixing a small alpha UX with production
auth, multi-user policy, callback mechanics, confirmation semantics, parallel
message handling and hardening before the transport behavior is measured.

Earlier stages already decided that:

- Hermes runs from the ready-made Docker image through Docker Compose;
- Domain Core remains independent from Hermes and Telegram;
- Hermes plugin/tools call the Application HTTP API and do not import Domain
  Core;
- meaningful state changes require preview, confirmation, expected version and
  Application/Domain checks;
- M8 stopped before Telegram Alpha, inline buttons, callbacks and production
  Telegram UX.

M9 must prove that one authorized Telegram user can complete the main scenario
without turning free text or callback text into a direct commit surface.

## Decision

M9 will implement a private Telegram Alpha for exactly one authorized Telegram
identity.

The target path is:

```text
Telegram message/callback
-> Hermes Telegram Gateway
-> user/session/workflow binding
-> presentation layer
-> Hermes plugin/Application tools
-> preview/confirmation
-> structured response
```

M9 does not implement public registration, multi-user production auth,
production dashboard auth replacement, production observability, backup/restore
hardening, real store integration, live prices, production model rollout or a
custom Hermes image.

### One-user allowlist policy

The alpha allowlist contains one Telegram identity.

The configured Telegram identity is transport authorization only. It does not
replace Application user identity, workflow permissions, confirmation checks or
Domain validation.

Any message or callback that cannot be mapped to the one alpha identity must be
rejected before tool execution.

### Telegram ID configuration source

Telegram ID configuration must come from runtime configuration already intended
for secrets or deployment-local values. It must not be committed into Git,
printed in logs or copied into reports.

Accepted sources for M9:

- existing Hermes Telegram Gateway allowlist environment/configuration;
- sanitized application config that records only whether a value is set;
- test fixtures with synthetic non-real IDs.

Forbidden:

- committing real Telegram IDs if they identify a private user;
- reading or printing bot tokens, `.env`, `auth.json`, credentials or private
  keys;
- deriving Application `user_id` from display names or free text.

### User/session/workflow binding

Every Telegram message or callback must be bound to:

- Telegram transport identity;
- Application `user_id`;
- active `WorkflowRun` or equivalent application-owned workflow/session
  record;
- Hermes session or gateway context when available.

The binding is adapter state, not domain authority. Application APIs remain
responsible for workflow state, permissions, versions, confirmation and commit
rules.

If a message cannot be bound deterministically, the adapter must return a safe
error or clarification and must not call state-changing tools.

### Message size and rate limits

M9 uses deterministic limits:

- messages above the configured size limit are rejected with a user-facing
  validation response;
- repeated messages above the per-user rate limit are rejected or delayed with
  a stable policy response;
- limits are enforced before intent routing or tool execution;
- policy failures are machine-readable for E2E tests.

Exact numeric values may start as technical alpha constants and be refined
after Telegram capability discovery.

### Timezone normalization

Relative dates in Telegram messages must be normalized with an explicit user
timezone. For M9 the timezone source order is:

1. Application profile or workflow context when present;
2. alpha runtime configuration when explicitly set;
3. UTC technical fallback recorded in the response/test artifact.

The adapter must not infer timezone from Telegram display text. User-facing
responses should make ambiguous dates explicit when needed.

### Presentation-layer scope

M9 adds only the presentation layer needed for one-user alpha scenarios:

- clarification;
- preview;
- validation warnings;
- status;
- errors;
- cancel;
- recipe view;
- shopping checklist.

Presentation formatting must not contain business rules that bypass
Application/Domain validation. It may format structured results, warnings,
confirmation prompts and callback labels.

### Inline button and callback support evidence

M9 must inspect the installed Hermes Telegram Gateway before relying on inline
buttons or callback semantics.

Existing Stage 0 evidence found Telegram callback support in Hermes internals
and built-in callback namespaces, but did not prove a Menu Planner callback
round trip. Step 3 must refresh this evidence for the current image and record
whether M9 uses:

- Hermes built-in slash confirmation callbacks;
- a project-owned stable callback id path, if supported;
- synthetic gateway callback fixtures when live Telegram is unavailable.

If callback support is unavailable or unsafe, M9 must use explicit command/text
confirmation tied to Application `confirmation_id` and record the deviation.

### Callback data shape and size policy

Callback data must contain stable references only:

- `confirmation_id`;
- stable `shopping_item_id`;
- stable action id;
- short workflow/session reference if needed.

Callback data must not contain:

- full operation payloads;
- profile/menu/recipe/shopping private details;
- secrets or credentials;
- raw prompt/model output;
- SQL, shell, file path, URL or arbitrary command text.

Callback payload size must stay below the installed Telegram/Hermes limit. If
the exact limit cannot be proven in the installed version, M9 uses a short
project limit and records the assumption.

### Confirmation binding policy

No meaningful confirmed-state change may happen from Telegram free text or a
callback alone.

Commits must be bound to:

- a previously generated preview;
- Application-owned `confirmation_id`;
- expected entity/version/hash where relevant;
- idempotency key;
- current Application workflow state;
- authenticated/bound alpha user.

The Application service remains the final authority and must reject stale,
wrong-user, wrong-version, expired or already-consumed confirmations.

### Repeated callback behavior

Repeated callbacks must not duplicate state changes.

M9 accepts either:

- idempotent handling that returns the already-applied result for the same
  idempotency key; or
- explicit rejection with a stable `already_consumed`, `stale_confirmation` or
  equivalent machine-readable error.

The selected behavior must be covered by E2E alpha tests.

### Parallel-message policy

M9 chooses explicit conflict rejection as the initial alpha policy.

For one authorized user, when a state-changing workflow action is already in
progress or waiting for confirmation, conflicting free-text messages or
callbacks must be rejected with a stable "finish or cancel current action"
response.

Read-only status/help requests may be allowed if they do not mutate workflow
state or consume confirmations.

Queueing is deferred until there is evidence that it improves UX without
hiding stale confirmations or parallel commits.

### Restart recovery policy

After restart, active workflow state must be reconstructed from Application
state, not Hermes memory.

M9 must support or explicitly record limitation for:

- pending confirmation lookup by `confirmation_id`;
- active `WorkflowRun` or equivalent application workflow record;
- safe re-rendering of status/preview when possible;
- rejection of callbacks whose state cannot be reconstructed.

Hermes session memory may help conversation continuity but must not replace
Application state.

### Telegram E2E alpha scope

M9 E2E alpha coverage must prove the one-user path for:

- profile;
- menu;
- revision;
- confirmation;
- recipe view;
- shopping checklist;
- cancel;
- expired confirmation.

The E2E path may use one authorized user with the live Telegram Gateway or a
synthetic Telegram gateway fixture when live Telegram is unavailable. Deviations
must be recorded in the M9 report.

## Consequences

- Step 3 must inspect the installed Hermes Telegram capability before callback
  implementation.
- Telegram adapter code remains presentation/transport layer and must call
  Application/Hermes plugin boundaries rather than Domain Core or DB.
- Callback data is intentionally small and indirect.
- The first alpha uses conflict rejection, not queueing, for parallel
  state-changing messages.
- Production auth and hardening decisions remain outside M9.
- Unresolved Telegram Alpha UX/security details are tracked in OQ-010.

## Out Of M9

M9 does not implement:

- public registration;
- multi-user production auth;
- production dashboard auth replacement;
- backup/restore or alerting hardening;
- broad observability hardening;
- real store API, scraper, live prices or live availability;
- production model/provider rollout;
- custom Hermes image;
- direct Telegram adapter DB writes;
- full payload callback data;
- commits from free text or callback without Application confirmation checks.
