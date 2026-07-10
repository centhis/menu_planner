# ADR-0006: Minimal profile vertical slice

Date: 2026-07-10

Status: Accepted

## Context

Stage 4 / M4 must prove the first real business vertical slice without LLM,
Intent Router, production Hermes plugin, Telegram business UX, menu, recipes,
shopping list, store catalog, or substitutions.

The M4 scenario is:

```text
structured command
-> ProfileDraft
-> validation
-> preview
-> persistent Confirmation
-> safe commit
-> ProfileVersion read-back
```

Concept and domain documents intentionally leave final product profile fields
open. ADR-0004 already defines generic `ProfileDraft` and `ProfileVersion`
contracts with a JSON-compatible `fields` object. ADR-0005 already defines
generic safe commit primitives, explicit `expires_at`, idempotency records,
versioning, and audit.

M4 needs enough profile shape to validate, preview, commit, and read back a
profile version, but must not silently decide the final product profile model.

## Decision

Use a minimal M4 profile shape as a technical assumption for the deterministic
vertical slice.

This is not the final product profile schema. It is the smallest profile
payload that can exercise validation, workflow, preview, confirmation, safe
commit, versioning, idempotency, audit, and restart read-back.

### M4 ProfileDraft fields

For M4 only, `ProfileDraft.fields` and the committed
`ProfileVersion.fields` use this JSON-compatible shape:

```json
{
  "user_facts": {
    "people_count": 1,
    "locale": "en-US",
    "timezone": "UTC",
    "available_equipment": ["stovetop"],
    "default_max_active_time_minutes": 30
  },
  "strict_restrictions": [
    {
      "kind": "ingredient_exclusion",
      "value": "peanut"
    }
  ],
  "soft_preferences": [
    {
      "direction": "prefer",
      "value": "vegetables"
    }
  ]
}
```

M4 validators may require these top-level keys and validate their primitive
types, non-empty strings, and basic positive integer values.

M4 must not add final product meaning beyond these categories. For example,
`peanut`, `vegetables`, `stovetop`, `en-US`, and `UTC` are fixture values for
tests and examples, not selected product defaults for the owner.

### Technical assumptions vs product decisions

Technical assumptions for M4:

- A profile has one current committed version per `user_id`.
- `people_count` is a user fact used to prove numeric validation.
- `locale` and `timezone` are user facts used to prove stable structured
  storage and preview output.
- `available_equipment` is a user fact used to prove array validation.
- `default_max_active_time_minutes` is a user fact used to prove range
  validation.
- `strict_restrictions` are explicit hard exclusions.
- `soft_preferences` are non-binding preferences with a direction.

Product decisions not made by M4:

- final required profile fields;
- supported locales, countries, cities, currencies, and time zones;
- supported equipment catalog and equipment taxonomy;
- supported allergen, ingredient, cuisine, diet, religious, medical, and
  preference taxonomies;
- whether `people_count` means household size, servings, guests, or meal
  participants;
- budget, calories, macro targets, leftovers, pantry state, store region, and
  catalog assumptions;
- UX wording and whether a real user must answer every field during onboarding.

### Strict restrictions, soft preferences, and user facts

M4 distinguishes profile data categories as follows:

- `strict_restrictions`: hard constraints that future generated drafts must
  not violate after later menu workflows exist.
- `soft_preferences`: non-binding preferences that may guide future generation
  but do not make a profile invalid when absent.
- `user_facts`: stable structured facts about the user context that are neither
  hard exclusions nor preference signals.

M4 does not model temporary wishes, unverified dialogue claims, confidence,
source attribution, expiration, or clarification history. Those remain outside
the deterministic profile vertical slice.

### Profile entity identity

M4 uses one profile entity per application `user_id`.

The application entity identity for M3 safe commit primitives is:

```text
entity_type = "profile"
entity_id = "profile:<user_id>"
operation = "commit_profile"
```

The committed `ProfileVersion.profile_id` uses the same `entity_id` value.
This is a technical identity for the M4 single-profile-per-user slice, not a
decision that the product can never support multiple profile-like entities.

The first committed profile version is version `1`. A missing current profile
is represented at the application boundary by `expected_version = 0`.

### Mapping to M3 safe commit primitives

M4 profile commit must reuse the M3 preview-confirm-commit flow.

Mapping:

- `ProfileDraft` is the draft payload for `entity_type = "profile"`.
- `ProfileVersion` is the committed payload created by safe commit.
- `OperationPreview.operation` is `commit_profile`.
- `OperationPreview.entity_id` is `profile:<user_id>`.
- `OperationPreview.expected_version` is the current committed profile version
  or `0` when no profile exists.
- `OperationPreview.draft_version` identifies the profile draft version used
  to build the preview.
- `OperationPreview.summary_hash` is computed from canonical
  committed-relevant profile data, not from display wording.
- `Confirmation` must match `user_id`, operation, entity identity,
  `expected_version`, `draft_version`, and `summary_hash`.
- A successful commit writes the new `ProfileVersion`, confirmation status,
  idempotency outcome, and audit event in one transaction.

M4 must not create a profile-specific commit shortcut that bypasses M3
confirmation, idempotency, version checks, transaction handling, or audit.

### Confirmation expiration

M4 does not choose a user-facing global confirmation TTL.

The deterministic CLI or test API must supply an explicit `expires_at` value
when creating a confirmation, following ADR-0005. Tests should use controlled
timestamps for non-expired and expired confirmations. Any future default such
as "15 minutes after preview" is a UX/product decision for a later user-facing
adapter milestone.

### Idempotency key source

M4 CLI/test API commit commands require an explicit idempotency key field or
argument supplied by the caller.

Tests may use stable fixture keys such as:

```text
m4-profile-commit:user_001:profile_draft_001:v1
```

This is only the deterministic test boundary. Mapping HTTP headers, Hermes
turn metadata, Telegram callback data, or session IDs into idempotency keys is
deferred to the relevant adapter milestone.

## Consequences

- M4 can proceed without choosing final product profile fields.
- Profile validation can become deterministic and testable in the next M4
  task.
- M4 profile commit can reuse M3 safe commit primitives instead of creating a
  second commit path.
- CLI/test API scenarios can run without Hermes, Telegram, LLM, secrets, or
  transport-specific callback assumptions.
- Later menu workflows must revisit the product meaning of profile fields
  before relying on this M4 shape as user-facing semantics.

## Not Decided Here

- Final product profile schema and onboarding UX.
- Final taxonomy for restrictions, allergies, ingredients, equipment, cuisine,
  diet, stores, budget, calories, macros, leftovers, pantry, region, and
  currency.
- Intent Router M5, confidence thresholds, ambiguity handling from free text,
  eval harnesses, or model repair loops.
- Production Hermes plugin, Hermes tool schemas, Telegram callback mapping, or
  Telegram confirmation copy.
- User-facing confirmation TTL.
- Adapter-level idempotency key mapping.
- Menu, recipe, shopping list, store catalog, substitutions, or generated
  drafts.
- Any change to the ready-made Hermes image, Docker daemon, dashboard, gateway,
  auth flow, model provider, or runtime state layout.
