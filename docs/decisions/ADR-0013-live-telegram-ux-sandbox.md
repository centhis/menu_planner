# ADR-0013: Live Telegram UX sandbox strategy

Date: 2026-07-12

Status: Accepted

## Context

Stage 10 / M9 proved a synthetic provider-free Telegram Alpha slice. It did
not prove a real Telegram network round trip, live inline button taps, live
callback delivery, or first-screen UX quality in Telegram.

Stage 10.5 must make the UX visible to one authorized Telegram user before the
project treats Telegram Alpha as user-reviewable. The risk is mixing a live UX
sandbox with production auth, new product features, real store integration,
observability hardening, or irreversible Application state changes.

## Decision

Stage 10.5 will build a live Telegram UX sandbox for exactly one authorized
Telegram identity. The sandbox is a user-visible product UX/UI surface for
screens, inline buttons, callback smoke, feedback, UX corrections and sanitized
evidence. It is not a throwaway technical experiment: the sandbox is the safe
delivery mechanism, while the accepted screens and interaction rules are the
first Telegram UI decisions for Menu Planner.

The sandbox path is:

```text
Telegram command/message/callback
-> Hermes Telegram Gateway
-> Menu Planner plugin or UX sandbox adapter
-> demo or application-backed screen renderer
-> inline buttons with stable callback ids
-> sanitized report and user feedback record
```

Stage 10.5 must not implement new product features outside the sandbox and must
not start MVP hardening or production work.

### Live Telegram Token Handling

Live Telegram bot token and Telegram user identifiers are runtime secrets or
private deployment-local values.

Rules:

- do not read, print, log, copy, commit or screenshot the token value;
- do not open `.env`, `auth.json`, credentials or private-key files;
- use only sanitized checks such as "configured/not configured";
- if a command requires Docker socket access or a live token/user id, ask the
  user before running it;
- reports may mention variable names and sanitized state, never secret values.

The user must provide or confirm live Telegram access outside Git. If live
access is unavailable, the stage records the limitation instead of inventing
evidence.

### One Authorized Telegram ID Policy

Stage 10.5 keeps the M9 one-user Alpha boundary:

- one configured Telegram identity may open the UX sandbox;
- Telegram transport authorization does not replace Application `user_id`;
- every live screen/callback must remain bound to the alpha Application user
  and active workflow or explicitly marked as demo-only;
- public registration and multi-user production auth remain out of scope.

### Sandbox Entry Policy

The UX sandbox must open from one narrow user action:

- preferred: a project-owned sandbox command or menu entry such as
  "Menu Planner UX Sandbox";
- fallback: a narrow text command such as `/menu_planner_ux` if Hermes exposes
  slash command routing more reliably than arbitrary buttons;
- the first screen must state that it is an Alpha UX sandbox;
- if data is demo/synthetic, the first screen must say "DEMO, not active
  state" or equivalent wording.

The sandbox entry must not trigger a business workflow commit.

### Demo Data Labeling Policy

Demo/synthetic data is allowed only for UI review.

Every demo-backed screen must:

- label itself as demo/synthetic;
- distinguish draft state from active state;
- avoid implying that a profile, menu, recipe or checklist was actually saved;
- keep demo item ids stable enough for callback smoke tests;
- avoid private user data in screenshots, reports or transcripts.

Application-backed screens may omit the demo label only when the source is an
actual Application read API and still must distinguish draft and active state.

### Callback ID Policy

Callback data must stay short and stable.

Allowed callback references:

- screen id;
- stable action id;
- `confirmation_id`;
- `shopping_item_id`;
- short demo item id;
- short page cursor when needed.

Forbidden callback data:

- full operation payloads;
- private profile/menu/recipe/shopping details;
- secrets, credentials or token fragments;
- raw prompt/model output;
- SQL, shell, file paths, URLs or arbitrary command text.

Repeated callbacks must not duplicate state changes. For the sandbox, repeated
screen-navigation callbacks may re-render idempotently. Repeated state-changing
or confirmation callbacks must be idempotent or rejected with a stable
machine-readable reason.

### Screenshots And Evidence Sanitization Policy

Stage 10.5 evidence may use screenshots or textual screen descriptions, but
must be sanitized before committing.

Sanitized evidence must not include:

- real Telegram bot token;
- private Telegram user id, chat id, message id or thread id;
- private user profile/menu content unless the user explicitly approves it;
- `.env`, `auth.json`, credentials, private keys or access tokens.

Allowed evidence:

- screen names;
- button labels;
- sanitized callback namespace/shape;
- "callback reached sandbox: yes/no";
- redacted or synthetic identifiers;
- user feedback summary.

### User Feedback Loop

For each major screen, the agent should:

1. show the current screen in Telegram;
2. explain the UX logic briefly;
3. suggest 1-3 practical improvements;
4. ask the user what to change;
5. apply accepted feedback or record deferred feedback;
6. show the updated screen or record why it was not shown.

Feedback must be recorded in the Stage 10.5 report as accepted, applied,
deferred or out of scope.

### UX/UI Rules For The Sandbox

Stage 10.5 adopts these initial Telegram UI rules:

- primary planning starts with useful output: generate a menu first, then offer
  natural actions such as accept, replace one meal, shopping list or settings;
- the home screen is state-aware: before menu generation the primary action is
  `Составить меню`; after a menu exists, home shows remaining shopping items
  and the current meal recipe, and the primary action becomes `Изменить меню`;
- state-changing actions require a visible preview and an explicit accept
  button, but that accept button may live on the preview itself;
- avoid redundant second confirmation screens when the preview and button copy
  are already clear;
- internal draft/status/confirmation mechanics must not dominate the visible
  UX copy;
- confirmation buttons link to stable ids internally, but internal ids such as
  `confirmation_id` are not shown in the lightweight UI unless needed for a
  support/debug surface;
- destructive/cancel confirmations are reserved for real destructive actions,
  not ordinary navigation;
- visible inline buttons use meaningful Russian action labels, not bare
  numeric proxies;
- shopping checklist updates use stable item ids;
- ambiguous text routes to disambiguation instead of guessing;
- text-first settings input is untrusted user input, not a prompt/control
  channel; it must be parsed into allowed setting fields or a narrow
  change-intent schema before it can affect generation;
- text-first settings changes require validation, preview and explicit accept
  before persistence;
- long previews and diffs are summarized or split across messages;
- error screens show safe next actions and no raw exception or secret data.

### Mini App Decision Checkpoint

Mini App work is a decision checkpoint, not an automatic implementation.

Evaluate during Stage 10.5:

- which screens are awkward in chat-only UI;
- whether menu preview, checklist review or profile editing needs richer
  controls;
- whether inline buttons are sufficient for Alpha;
- auth, state sync, callback, hosting and test risks.

Default decision for Stage 10.5: defer Mini App implementation unless user
review shows that chat-only UX blocks the Alpha review. Even then, record the
decision before implementing.

### Out Of Scope For Stage 10.5

Stage 10.5 does not implement:

- public registration;
- multi-user production auth;
- production dashboard auth replacement;
- backup/restore, observability or deployment hardening;
- real store integration, live prices or availability;
- production model/provider rollout;
- new product features outside the UX sandbox;
- direct Telegram commits without Application preview/confirmation checks;
- custom Hermes image or mutable container changes.

## Consequences

- Step 3 must ask for approval before any live Telegram/Docker checks that need
  secrets, private identifiers or Docker socket access.
- Step 4 may build demo screens before Application-backed screens, but every
  demo screen must be labeled.
- Stage 10.5 reports must include sanitized evidence, user feedback and open
  UX decisions.
- MVP hardening and production work remain blocked until a separate user
  request.
