---
name: m6b-recipes-replacements
description: "Use when building the Menu Planner M6B recipes and local meal replacement slice: RecipeDraft schema, deterministic fake recipe generator, recipe validation, versioned recipe persistence, one-slot replacement, exact replacement diff, stale confirmation checks, golden fixtures, and M6B report, without shopping list, store catalog, product matching, Hermes plugin, Telegram UX, direct model writes, or production model dependency."
---

# M6B recipes and replacements workflow

## Scope

- Build only recipes and one-slot replacement up to Gate M6B.
- Add or refine `RecipeDraft`, fake recipe generator, validators, versioned
  recipe persistence, replacement workflow, exact diff, stale confirmation
  tests, golden fixtures, and M6B report.
- Use validated/confirmed menu data and explicit replacement request
  parameters only.
- Do not implement shopping list, store catalog, product matching, production
  Hermes plugin/tools, Telegram UX, or production model dependency.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m7-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
or when the brief is insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 7.md`
- `docs/experiments/m6a-menu-draft-generation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0008-menu-draft-generation.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If recipe timing, confirmed menu path, recipe fields, quantity semantics,
   replacement diff semantics, stale confirmation behavior, model/provider
   choice, or activation policy is blocking, ask the user during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run targeted contract/unit/golden checks first.
8. Run M6B eval/golden checks when the task changes recipe generation,
   validators, replacement behavior, or stale confirmation behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine fixture, validator, fake
  generator, or replacement-test changes when the brief and affected files are
  sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Recipe and replacement outputs are untrusted until validated.
- Model/fake output must never write confirmed state directly.
- Replacement changes exactly one meal slot.
- Unaffected meal slots must remain unchanged by test.
- Stale confirmations must be rejected.
- Keep shopping list and store catalog out of M6B.
- Keep Domain Core independent from Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
