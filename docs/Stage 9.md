# Этап 9. M8 Hermes plugin integration with narrow tools

## 1. Цель этапа 9

Этап 9 должен довести проект до ближайшей рефлексивной вехи M8:

> Hermes вызывает только разрешенные narrow tools через версионированный
> plugin-adapter, каждый tool имеет strict schema and structured result,
> hooks/toolsets ограничивают полномочия, а Application/Domain повторно
> проверяют инварианты даже при обходе Hermes policy layer.

Главный вопрос этапа:

> Где проходит реальная граница Hermes: какие возможности runtime сокращают
> adapter code, а где Hermes начинает дублировать application workflow и
> создавать риск?

Этап 9 заканчивается на Gate M8 и рефлексии M8. После Gate M8 не переходить
автоматически к Telegram Alpha, real store integration, production model
rollout или production deployment hardening без отдельного задания.

## 2. Основания

Routine M8 tasks начинают с brief, skill и непосредственно затронутых файлов:

- `docs/briefs/m9-agent-brief.md`

Полный контекст открывать только при изменении ADR/stage plan/component
boundary, Hermes boundary или если brief недостаточен:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 8.md`
- `docs/experiments/m7-shopping-list-and-mock-catalog.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `docs/decisions/ADR-0010-shopping-list-and-mock-catalog.md`
- `docs/decisions/open-questions.md`

Решения из M0-M7 для этого этапа:

- Hermes запускается только из готового Docker image через Docker Compose.
- Custom Hermes image, mutable container edits and docker commit are forbidden.
- Domain Core не импортирует Hermes, Telegram, ORM, HTTP clients или model SDK.
- Application service владеет HTTP API, DB schema, migrations, repositories and
  transaction boundary.
- Hermes plugin/tools являются adapter layer and do not import Domain Core
  directly.
- Модель не изменяет подтвержденное состояние напрямую.
- Free text must become structured intent, policy decision, restricted toolset
  and domain validation before any state-changing action.
- Critical facts in Hermes memory never replace Application DB.
- User toolset must not expose terminal, arbitrary filesystem/browser, SQL,
  secrets, model/toolset/skill modification or administrative MCP tools.
- M7 stopped before production Hermes plugin, Telegram UX and real store
  integration.

## 3. Scope

Разрешено:

- создать Codex skill для M8;
- принять ADR для Hermes plugin packaging, tool boundary, hooks, toolsets,
  runtime skills, context sourcing, guided/agentic modes, fake model tests and
  prompt-injection tests;
- inspect actual Hermes version, CLI help, plugin API, mounted config and
  ready-made image behavior before implementing plugin code;
- создать adapter между Hermes plugin API and Application HTTP API;
- зарегистрировать narrow tools by domain operation;
- определить strict input/output schemas for every tool;
- разделить toolsets by workflow state and role;
- реализовать pre-message policy hook;
- реализовать pre-tool policy hook;
- повторить critical checks inside tool handler/application service;
- добавить versioned Hermes runtime skills для intent interpretation,
  clarification, menu generation, validation-error repair and preview
  explanation;
- подключить application context from DB/API instead of trusting Hermes memory;
- сохранить `agentic` and `guided` modes using the same domain commands;
- добавить fake model/provider for integration tests;
- добавить contract tests for each tool;
- добавить tests that user agent cannot see administrative tools;
- добавить prompt injection test attempting terminal/SQL/commit escalation;
- провести one bounded end-to-end Hermes agent workflow without Telegram UX;
- заполнить M8 report and reflection.

Запрещено на этом этапе:

- создавать Dockerfile for Hermes;
- использовать `docker build` for Hermes or `docker compose build hermes`;
- создавать custom Hermes image;
- использовать `docker commit`;
- использовать `docker cp` для установки plugin code;
- устанавливать packages inside Hermes container;
- редактировать files inside running container;
- создавать невоспроизводимое состояние через `docker exec`;
- импортировать Domain Core напрямую из Hermes plugin/tools;
- позволять Hermes directly write Application DB;
- реализовывать Telegram Alpha, inline buttons, callbacks or Telegram
  production UX;
- подключать real store API, scraper, raw store HTML, live prices or
  availability;
- выбирать production cloud/local model provider без отдельного решения;
- читать, печатать или логировать `.env`, `auth.json`, tokens или credentials;
- помещать business rules only in Hermes skills/prompts;
- давать user toolset access to terminal, filesystem, browser, SQL, secrets,
  model/toolset/skill modification or admin MCP tools;
- считать Hermes memory source of truth for profile, menu, recipes, shopping or
  catalog;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 9:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m7-eval
docker compose ps
docker compose config
```

Проверить, что:

- Gate M7 функционально закрыт или явно отложен человеком;
- `docs/experiments/m7-shopping-list-and-mock-catalog.md` exists and is filled;
- ADR-0010 accepted;
- deterministic shopping list, mock catalog, replacement diff and checklist
  disambiguation work without Hermes, Telegram and external providers;
- M7 did not implement production Hermes plugin, Telegram UX or real store
  integration;
- ready-made Hermes image strategy from ADR-0001 is still respected;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты.

Если Docker socket access нужен для Hermes checks, агент должен запросить
разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 9 считается завершенным, если:

- M8 Codex skill exists and helps keep tasks inside Hermes plugin boundary;
- `docs/briefs/m9-agent-brief.md` is used as primary context for routine tasks;
- ADR-0011 or equivalent decision note fixes Hermes plugin packaging, tools,
  hooks, toolsets, skills, context sourcing, modes and test strategy;
- actual Hermes version/API behavior is inspected and recorded before
  implementation;
- plugin code is reproducibly mounted/configured through host files or accepted
  project packaging, not mutable container state;
- Hermes plugin/tools call Application HTTP API and do not import Domain Core;
- every tool has strict input and structured output schema;
- tool results match the accepted success/error result contract;
- toolsets are restricted by workflow state and user role;
- pre-message hook blocks disallowed channel/user/message/admin attempts;
- pre-tool hook blocks tools outside current toolset/state/policy;
- tool handlers/application services repeat critical checks independently of
  hooks;
- user agent cannot see or call administrative tools;
- memory is not used as source of truth for critical state;
- agentic and guided modes use same domain commands and schemas;
- fake model/provider integration test is deterministic and provider-free;
- prompt injection attempts cannot reach terminal, SQL, arbitrary commit or
  admin tools;
- one bounded end-to-end Hermes agent workflow passes without Telegram UX;
- Domain Core still has no Hermes, Telegram, ORM, HTTP client or model SDK
  imports;
- no custom Hermes image, mutable container install, Telegram Alpha or real
  store integration was added;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke`, M8 integration/eval command and `git diff --check`
  pass or deviations are explicitly recorded;
- создан `docs/experiments/m8-hermes-plugin-integration.md` с результатом Gate
  M8 и рефлексией.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M8

Цель: не дать Stage 9 расползтись в Telegram Alpha, mutable Hermes image work,
real store integration or broad administrative tool access.

Создать:

```text
.agents/skills/m8-hermes-plugin-integration/SKILL.md
```

Содержимое:

```markdown
---
name: m8-hermes-plugin-integration
description: "Use when building the Menu Planner M8 Hermes plugin integration slice: actual Hermes API discovery, reproducible plugin packaging, narrow tools, strict tool schemas, structured tool results, toolsets, pre-message and pre-tool hooks, versioned Hermes runtime skills, DB/API context sourcing, agentic and guided modes, fake model integration tests, prompt-injection tests, and M8 report, without Telegram Alpha, custom Hermes image, mutable container installs, real store integration, direct DB writes from Hermes, admin tools in user toolsets, or production model rollout."
---

# M8 Hermes plugin integration workflow

## Scope

- Build only Hermes plugin integration up to Gate M8.
- Inspect actual Hermes version, CLI help, plugin API, and image behavior
  before implementing. Do not invent Hermes APIs by analogy.
- Add or refine plugin adapter, narrow tools, tool schemas, tool results,
  toolsets, hooks, runtime skills, application context sourcing, fake model
  tests, prompt-injection tests, and M8 report.
- Use Application HTTP API for domain operations. Do not import Domain Core
  directly from Hermes plugin/tools.
- Do not implement Telegram Alpha, real store integration, custom Hermes image,
  mutable container installation, admin tools in user toolsets, or production
  model rollout.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m9-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
Hermes boundary, Docker/runtime configuration, or when the brief is
insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 9.md`
- `docs/experiments/m7-shopping-list-and-mock-catalog.md`
- `docs/decisions/ADR-0001-hermes-container-strategy.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `docs/decisions/ADR-0010-shopping-list-and-mock-catalog.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation and actual Hermes runtime/API before editing
   Hermes integration code.
3. If plugin API, packaging, tool naming, hook semantics, toolset config,
   context source, model/provider, fake model strategy, or guided/agentic mode
   is blocking, ask the user during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and verified Hermes image behavior.
6. Add the smallest testable change.
7. Run targeted schema/tool/hook tests first.
8. Run M8 integration/eval checks when the task changes plugin behavior,
   toolsets, hooks, runtime skills, or agent workflow behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine tool schema, fixture, hook,
  or skill changes when the brief and affected files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Hermes is runtime/adapter, not source of domain authority.
- Free text never calls arbitrary tools directly.
- User toolsets must not expose terminal, arbitrary filesystem/browser, SQL,
  secrets, model/toolset/skill modification, or admin MCP tools.
- Hooks are defense in depth; handlers/application services repeat critical
  checks.
- Memory does not replace Application DB for critical state.
- Business rules must not live only in Hermes skills/prompts.
- Keep Domain Core independent from Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
```

Критерий завершения: skill валиден локально; проверочный prompt не требуется,
если local validation прошла.

### Шаг 2. Зафиксировать Hermes plugin integration strategy

Цель: не смешать plugin API discovery, tool contracts, hooks, runtime skills,
Docker packaging and Telegram UX в одну непроверяемую реализацию.

Создать:

```text
docs/decisions/ADR-0011-hermes-plugin-integration.md
```

ADR должен зафиксировать:

- фактическую Hermes version/API evidence required before implementation;
- plugin packaging/mounting strategy that preserves ready-made image boundary;
- adapter boundary between Hermes plugin and Application HTTP API;
- tool naming and strict schema policy;
- structured tool result contract;
- toolset split by workflow state and role;
- pre-message hook policy;
- pre-tool hook policy;
- handler/application duplicate-check policy;
- versioned Hermes runtime skills policy;
- application context sourcing from DB/API, not memory;
- agentic/guided mode policy;
- fake model/provider integration-test policy;
- prompt-injection/admin-tool test policy;
- what remains out of M8.

Если нужны решения по Hermes plugin API, file layout, config mount, toolset
format, hooks, model provider, fake model or agentic/guided mode, агент задает
вопрос пользователю. Если выбор не блокирует discovery or documentation slice,
агент фиксирует technical assumption and open question.

Критерий завершения:

- ADR-0011 принят;
- no custom Hermes image or mutable container state accepted;
- M8 можно проверить without Telegram Alpha, real store integration and
  production model provider;
- unresolved runtime/model decisions перенесены в
  `docs/decisions/open-questions.md`.

### Шаг 3. Inspect actual Hermes plugin/runtime API

Цель: не реализовывать plugin by analogy.

Проверить локально:

- ready-made Hermes image version;
- relevant CLI help;
- installed plugin/tool/hook/skill examples or docs inside image;
- compose mounts and config behavior;
- available fake/local provider test options, if any.

Запрещено:

- install packages inside container;
- edit files inside running container;
- use `docker cp` to install code;
- mutate image or daemon config.

Критерий завершения:

- evidence recorded in ADR/report or experiment note;
- unknown API details remain explicit open questions;
- no secrets printed;
- no mutable container state left as target solution.

### Шаг 4. Define plugin package and Application HTTP adapter boundary

Цель: Hermes plugin remains adapter layer.

Добавить или уточнить:

- reproducible host-side plugin file layout;
- config/bind-mount strategy, if required by actual Hermes API;
- adapter functions that call Application HTTP API;
- no Domain Core imports from plugin;
- timeout/error mapping policy;
- correlation id propagation.

Критерий завершения:

- plugin adapter cannot bypass Application service transaction boundary;
- Application HTTP API remains owner of state changes;
- tests or static checks cover forbidden imports where feasible.

### Шаг 5. Define narrow tools and strict schemas

Цель: every Hermes tool is a narrow domain operation, not arbitrary execution.

Define tools only for accepted application workflows, for example:

- workflow/status read tools;
- profile preview/commit tools;
- menu draft generation/validation/preview tools;
- recipe generation/persistence/replacement preview tools;
- shopping list build/get/checklist update tools;
- clarification/cancel/status tools.

If a tool would require unfinished product semantics or Telegram UX, agent asks
the user or leaves it out of M8.

Критерий завершения:

- every tool has strict input schema;
- every tool has structured success/error output schema;
- state-changing tools require preview/confirmation policy;
- no terminal/filesystem/browser/SQL/admin tools included.

### Шаг 6. Implement structured tool result contract

Цель: agent and guided modes receive predictable machine-readable results.

Tool result must include:

- success flag;
- operation/correlation id;
- entity id/version where relevant;
- data or warnings;
- structured errors;
- retryable flag;
- next allowed actions.

Критерий завершения:

- success and error fixtures/tests exist;
- validation and policy errors are stable;
- raw exceptions do not cross expected tool boundary.

### Шаг 7. Split toolsets by workflow state and role

Цель: user session sees only minimal allowed tools.

Define toolsets for:

- initial/profile-required state;
- menu planning states;
- recipe/replacement states;
- shopping-list states;
- read-only/status states;
- administrative/dev tools, if any, outside user toolset.

Критерий завершения:

- user toolset excludes terminal, arbitrary filesystem/browser, SQL, secrets,
  model/toolset/skill modification and admin MCP tools;
- toolset fixtures/config are versioned;
- tests verify administrative tools are not visible to user agent.

### Шаг 8. Implement pre-message policy hook

Цель: reject unsafe messages before agent/tool loop.

Hook checks at least:

- allowlist or authenticated user boundary as available in M8;
- message size;
- rate-limit placeholder or technical assumption;
- allowed channel;
- user binding;
- current workflow;
- administrative command attempt.

Критерий завершения:

- hook returns structured policy result;
- disallowed message cannot proceed to arbitrary tool loop;
- tests cover admin attempt and oversized/disallowed message.

### Шаг 9. Implement pre-tool policy hook

Цель: reject unsafe tool calls even if model proposes them.

Hook checks at least:

- tool is in active toolset;
- tool is allowed in current workflow state;
- user has permission;
- parameters validate;
- operation does not bypass required confirmation;
- no secret access;
- correlation id exists.

Критерий завершения:

- disallowed tool call is blocked before handler;
- state-changing action without preview/confirmation is blocked;
- structured error is returned.

### Шаг 10. Duplicate critical checks in tool handlers/application services

Цель: hooks are defense in depth, not the only safety boundary.

Handlers/application services must repeat critical checks:

- workflow state;
- expected version/summary hash for commits;
- permissions;
- idempotency;
- domain invariants;
- payload validation.

Критерий завершения:

- bypassing hook in tests still fails for forbidden action;
- Domain/Application errors remain stable;
- handler does not trust model or Hermes memory for critical state.

### Шаг 11. Add versioned Hermes runtime skills

Цель: use Hermes skills for local agent tasks without moving business rules
into prompts.

Add versioned skills for:

- intent interpretation;
- clarification;
- menu generation;
- repair from validation errors;
- preview explanation.

Каждый skill должен:

- point to structured tools/results rather than hidden business rules;
- avoid secrets/private data;
- be versioned and reproducibly mounted/configured;
- explain that Application/Domain validation is authoritative.

Критерий завершения:

- skills are versioned assets;
- tests or review checklist verifies no business rule exists only in prompt;
- changing a skill does not bypass domain policy.

### Шаг 12. Source application context from DB/API, not Hermes memory

Цель: memory improves conversation but does not become state authority.

Plugin context loading must:

- fetch confirmed profile/menu/recipe/shopping state through Application API;
- include current workflow state;
- include allowed actions/toolset metadata;
- use memory only as optional conversational hint where allowed.

Критерий завершения:

- memory conflict test favors Application DB/API;
- critical state missing from DB/API cannot be invented from memory;
- context payload is structured and bounded.

### Шаг 13. Preserve agentic and guided modes

Цель: strong and weak models use the same domain commands.

Implement or specify:

- `agentic`: Hermes chooses next tool within restricted workflow/toolset;
- `guided`: workflow engine selects next step, model solves local task;
- shared schemas, validators, confirmation model and repositories.

Критерий завершения:

- both modes use same tool schemas and Application API commands;
- guided mode can run one deterministic fake-model workflow;
- mode choice does not require Domain Core changes.

### Шаг 14. Add fake model/provider integration tests

Цель: integration tests must be provider-free and deterministic.

Add:

- fake model/provider or fixture runner accepted by actual Hermes API;
- one bounded workflow using synthetic inputs;
- deterministic tool-call sequence or allowed assertions;
- no real credentials or external providers.

Критерий завершения:

- integration command runs without production model credentials;
- failures are structured enough for debugging;
- no secrets are read or printed.

### Шаг 15. Add tool contract and security tests

Цель: Gate M8 must prove tool and policy safety.

Tests must cover:

- each tool schema accepts valid and rejects invalid input;
- each tool returns structured success/error result;
- user agent cannot see administrative tools;
- pre-tool hook blocks tool outside state/toolset;
- prompt injection cannot reach terminal, SQL, arbitrary commit or admin tool;
- Domain/Application rejects wrong call even if hook is bypassed;
- memory does not replace DB.

Критерий завершения:

- targeted tests pass;
- test fixtures do not contain secrets;
- security failures are machine-readable.

### Шаг 16. Run one bounded end-to-end Hermes workflow without Telegram UX

Цель: prove plugin works inside Hermes runtime before Telegram Alpha.

Workflow should use synthetic user input and fake model/provider where
possible. It may cover one narrow scenario, for example:

- interpret intent;
- fetch context from Application API;
- create/validate draft or shopping-list/status action;
- produce preview/explanation;
- stop before Telegram UX.

Критерий завершения:

- workflow uses restricted toolset;
- no direct DB writes from Hermes;
- no Telegram callbacks/buttons;
- structured transcript/result saved without secrets.

### Шаг 17. Заполнить M8 report and reflection

Цель: остановиться на Gate M8, а не перейти автоматически в Telegram Alpha.

Создать:

```text
docs/experiments/m8-hermes-plugin-integration.md
```

Report должен содержать:

- цель;
- scope;
- Hermes version/API evidence;
- plugin packaging decisions;
- tool/schema/hook/toolset decisions;
- runtime skills decisions;
- agentic/guided mode status;
- fake model/provider status;
- commands run;
- contract/security/integration metrics;
- what was intentionally not implemented;
- Gate M8 result;
- reflection;
- decisions before Telegram Alpha.

Критерий завершения:

- Gate M8 checklist заполнен;
- remaining assumptions listed;
- relevant questions copied to `docs/decisions/open-questions.md`;
- в отчете явно сказано: не переходить к Telegram Alpha без отдельного
  задания.

## 7. Gate M8 checklist

Заполнить в `docs/experiments/m8-hermes-plugin-integration.md`:

```markdown
## Gate M8 Checklist

[ ] M8 Codex skill exists and was used for implementation tasks.
[ ] M8 brief exists and was used for routine tasks.
[ ] ADR-0011 or equivalent decision note fixes Hermes plugin strategy.
[ ] Actual Hermes version/API behavior was inspected and recorded.
[ ] Plugin packaging preserves ready-made image boundary.
[ ] No custom Hermes image or mutable container installation was added.
[ ] Hermes plugin/tools call Application HTTP API and do not import Domain Core.
[ ] Every tool has strict input schema.
[ ] Every tool has structured success/error output schema.
[ ] Tool results include next allowed actions where relevant.
[ ] Toolsets are split by workflow state and role.
[ ] User toolset excludes terminal/filesystem/browser/SQL/secrets/admin tools.
[ ] Pre-message hook blocks disallowed/admin/oversized inputs.
[ ] Pre-tool hook blocks tools outside current toolset/state/policy.
[ ] Tool handlers/application services repeat critical checks independently of
    hooks.
[ ] User agent cannot see administrative tools.
[ ] Prompt injection cannot reach terminal, SQL, arbitrary commit or admin tool.
[ ] Memory does not replace Application DB for critical state.
[ ] Versioned Hermes runtime skills exist where accepted.
[ ] Business rules do not live only in skills/prompts.
[ ] Agentic and guided modes use same domain commands and schemas.
[ ] Fake model/provider integration test is deterministic and provider-free.
[ ] One bounded Hermes workflow passes without Telegram UX.
[ ] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[ ] No Telegram Alpha, real store integration, production model rollout or
    production deployment hardening added.
[ ] `scripts/dev.sh test` passed or deviation recorded.
[ ] `scripts/dev.sh lint` passed or deviation recorded.
[ ] `scripts/dev.sh typecheck` passed or deviation recorded.
[ ] `scripts/dev.sh smoke` passed or deviation recorded.
[ ] M8 integration/eval command passed or skipped with reason.
[ ] `git diff --check` passed.
```

## 8. Reflection M8

Заполнить после Gate M8:

```markdown
## Reflection M8

### Какие возможности Hermes реально сократили код?

- [ответ]

### Где Hermes дублирует application workflow и создает риск?

- [ответ]

### Можно ли еще сузить tools?

- [ответ]

### Достаточно ли guided mode для слабой модели?

- [ответ]

### Какие решения нужны перед Telegram Alpha?

- [ответ]
```

## 9. Sequence of tasks for Codex

Использовать по одному шагу за запрос. Для каждого шага:

1. Прочитать active M8 skill and `docs/briefs/m9-agent-brief.md`.
2. Проверить фактическое состояние файлов и `git status --short`.
3. Сформулировать acceptance criteria для текущего шага.
4. Если появляется blocking question, задать его пользователю до изменения.
5. Если вопрос не блокирует текущий minimal slice, зафиксировать assumption или
   open question.
6. Сделать минимальное изменение.
7. Запустить relevant targeted checks.
8. Запустить `git diff --check`.
9. Сообщить changed files, commands, passed/skipped checks, assumptions and
   remaining decisions.

Не выполнять следующий шаг самостоятельно без отдельного задания пользователя.
