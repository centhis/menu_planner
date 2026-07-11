# Этап 7. M6B recipes and local meal replacement

## 1. Цель этапа 7

Этап 7 должен довести проект до ближайшей рефлексивной вехи M6B:

> Валидируемые recipe drafts создаются и сохраняются версионированно для
> принятого меню, а замена одного meal slot создает новую menu draft/version с
> точным diff, не меняя остальные slots и не повреждая подтвержденное
> состояние.

Главный вопрос этапа:

> Можно ли безопасно связать меню, рецепты и локальную замену блюда так, чтобы
> генерация оставалась проверяемой кодом, stale confirmations отлавливались, а
> зависимые данные не менялись скрыто?

Этап 7 заканчивается на Gate M6B и рефлексии M6. После Gate M6B не переходить
автоматически к shopping list, store catalog, Hermes plugin, Telegram UX или
production model-backed generation без отдельного задания.

## 2. Основания

Routine M6B tasks начинают с brief, skill и непосредственно затронутых файлов:

- `docs/briefs/m7-agent-brief.md`

Полный контекст открывать только при изменении ADR/stage plan/component
boundary или если brief недостаточен:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 6.md`
- `docs/experiments/m6a-menu-draft-generation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0006-profile-vertical-slice.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `docs/decisions/ADR-0008-menu-draft-generation.md`
- `docs/decisions/open-questions.md`

Решения из M0-M6A для этого этапа:

- Domain Core не импортирует Hermes, Telegram, ORM, HTTP clients или model SDK.
- Application service владеет persistence, repositories и transaction boundary.
- M6A proof строится на deterministic fake generator и one-day menu draft.
- M6A не активирует меню и не пишет confirmed menu state.
- M6A model-backed generation и week draft expansion skipped.
- Recipe output и replacement output считаются untrusted до deterministic
  validation.
- Модель не изменяет подтвержденное состояние напрямую.

## 3. Scope

Разрешено:

- создать Codex skill для M6B;
- принять ADR для recipe draft contract, recipe timing policy, replacement
  semantics, stale confirmation behavior и model experiment boundaries;
- определить `RecipeDraft` schema, fixtures и stable validation errors;
- добавить deterministic fake recipe generator и golden tests;
- валидировать ингредиенты и количества, порции, оборудование, active/total
  time, steps, temperatures/methods, storage and reheating;
- сохранять рецепты версионированно через application boundary;
- добавить минимальный confirmed-menu/accepted-menu path или fixture, если он
  нужен для безопасной recipe/replacement проверки;
- реализовать замену ровно одного meal slot как новую menu draft/version;
- после подтвержденной замены пересчитать только зависимые данные, принятые
  ADR-0009 для M6B;
- добавить tests, что остальные meal slots не изменились;
- добавить stale confirmation tests для параллельной замены;
- добавить user-facing exact diff for replacement;
- заполнить M6B report и рефлексию M6.

Запрещено на этом этапе:

- реализовывать shopping list, store catalog, product matching, prices,
  packages, aisle data или shopping checklist;
- делать арифметику покупок или упаковок;
- подключать production Hermes plugin, Hermes tools/hooks/toolsets или
  Telegram business UX;
- выбирать production cloud/local model provider без отдельного решения;
- читать, печатать или логировать `.env`, `auth.json`, tokens или credentials;
- добавлять production model/API dependency без отдельного решения;
- активировать replacement или recipe changes напрямую из model/fake output;
- менять больше одного meal slot в операции replacement;
- считать M6A technical fixtures final product semantics;
- создавать или менять custom Hermes image;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 7:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m6a-eval
```

Проверить, что:

- Gate M6A функционально закрыт или явно отложен человеком;
- `docs/experiments/m6a-menu-draft-generation.md` существует и заполнен;
- ADR-0008 принят;
- M6A fake generation, validation, repair and preview work without Hermes,
  Telegram and external model provider;
- M6A не реализовал recipes, substitutions, shopping list, store catalog или
  direct menu activation;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты.

Если `scripts/dev.sh ...` требует Docker socket access, агент должен запросить
разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 7 считается завершенным, если:

- M6B Codex skill существует и помогает удерживать задачи в границах M6B;
- `docs/briefs/m7-agent-brief.md` используется как первичный контекст для
  routine tasks;
- ADR-0009 или equivalent decision note фиксирует recipe contract, timing
  policy, replacement semantics, stale confirmation behavior and model
  experiment boundaries;
- `RecipeDraft` имеет `schema_version`, valid/invalid fixtures и deterministic
  validation;
- invalid recipe returns stable machine-readable errors;
- fake recipe generator deterministic, side-effect free and provider-free;
- recipes сохраняются версионированно через application boundary;
- recipe generation не изменяет active menu by itself;
- replacement changes exactly one meal slot and creates a new draft/version;
- unaffected meal slots remain unchanged according to accepted comparison
  rules;
- user-facing replacement diff is exact and test-covered;
- stale confirmation after parallel replacement is rejected deterministically;
- failure leaves confirmed menu and recipes unchanged;
- optional model-backed recipe/replacement experiment is measured or explicitly
  skipped with reason;
- Domain Core still has no Hermes, Telegram, ORM, HTTP client or model SDK
  imports;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke`, M6B golden/eval command and `git diff --check` pass
  or deviations are explicitly recorded;
- создан `docs/experiments/m6b-recipes-and-replacements.md` с результатом Gate
  M6B и рефлексией M6.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M6B

Цель: не дать Stage 7 расползтись в shopping list, store catalog,
Hermes/Telegram или production model dependency.

Создать:

```text
.agents/skills/m6b-recipes-replacements/SKILL.md
```

Содержимое:

```markdown
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
```

Критерий завершения: skill валиден локально; проверочный prompt не требуется,
если local validation прошла.

### Шаг 2. Зафиксировать recipe and replacement strategy

Цель: не смешать recipe contract, menu activation, replacement, stale
confirmation and shopping-list concerns в одну непроверяемую реализацию.

Создать:

```text
docs/decisions/ADR-0009-recipes-and-replacements.md
```

ADR должен зафиксировать:

- нужен ли в M6B minimal confirmed-menu path или достаточно accepted fixture;
- когда генерируются recipes: after menu confirmation или explicit pregen
  policy;
- `RecipeDraft` schema and versioning;
- validator strategy and stable error codes;
- fake recipe generator policy;
- recipe persistence/versioning policy;
- one-slot replacement semantics;
- exact diff semantics for user-facing preview;
- stale confirmation behavior after parallel replacement;
- what dependent data recalculation means in M6B;
- model-backed recipe/replacement experiment policy;
- что остается out of M6B.

Если нужны product decisions по recipe fields, units, portions, storage,
reheating, replacement diff, confirmed-menu activation or repair limits, агент
задает вопрос пользователю. Если выбор не блокирует minimal fake-generator
slice, агент фиксирует technical assumption и open question.

Критерий завершения:

- ADR-0009 принят;
- no shopping list/catalog decisions hidden inside recipes;
- M6B можно проверить без Hermes, Telegram и production model provider;
- unresolved product/model decisions перенесены в
  `docs/decisions/open-questions.md`.

### Шаг 3. Определить RecipeDraft contract and fixtures

Цель: создать проверяемый recipe contract до generator implementation.

Добавить или уточнить:

- `RecipeDraft`;
- recipe ingredient entry;
- recipe step entry;
- valid/invalid fixtures;
- JSON-compatible schema rules;
- contract validation tests.

Минимум recipe validation должен покрывать:

- ingredients and quantities;
- portions;
- equipment;
- active and total time;
- ingredient usage in steps;
- no new ingredients only in steps;
- temperature/method consistency;
- storage and reheating.

Неизвестные продуктовые поля не придумывать. Если поле влияет на смысл recipe,
агент должен спросить пользователя или оставить поле вне M6B.

Критерий завершения:

- every changed contract has `schema_version`;
- valid fixtures pass;
- invalid fixtures return stable errors;
- Domain Core remains infrastructure-independent.

### Шаг 4. Реализовать deterministic fake RecipeDraftGenerator

Цель: получить reproducible recipe generation surface before model-backed
behavior.

Добавить:

- generator port/interface;
- fake generator implementation;
- golden fixtures for recipes tied to accepted menu items;
- malformed/invalid fake outputs for validator tests.

Критерий завершения:

- same fixture input produces same recipe draft;
- fake generator has no side effects;
- generator output is validated before persistence or preview;
- no external provider, network or secrets required.

### Шаг 5. Реализовать recipe validators and errors

Цель: код, а не модель, решает допустимость recipe draft.

Validators минимум покрывают правила из ADR-0009 и Step 3.

Если validator требует product choice по units, nutrition, cookware taxonomy or
temperature semantics, агент спрашивает пользователя или фиксирует technical
assumption в ADR/open questions.

Критерий завершения:

- validators have unit/contract tests;
- errors are machine-readable;
- invalid recipes cannot be persisted as valid recipe versions.

### Шаг 6. Добавить versioned recipe persistence

Цель: recipe generation не должна менять active menu и не должна терять
историю изменений.

Реализовать через application boundary:

- recipe version entity/repository as needed;
- link to menu version or accepted menu fixture according to ADR-0009;
- transaction boundary;
- audit metadata without secrets/private prompt data;
- idempotency/concurrency behavior where existing patterns require it.

Критерий завершения:

- recipe generation does not change active menu;
- invalid recipe does not create valid version;
- persistence tests cover versioning and failure rollback;
- no Domain Core imports infrastructure.

### Шаг 7. Реализовать local one-slot replacement

Цель: замена блюда должна быть локальной и проверяемой.

Replacement должен:

- принимать explicit replacement request;
- validate target menu version and target meal slot;
- produce a new menu draft/version according to ADR-0009;
- change exactly one meal slot;
- keep unaffected slots unchanged;
- not create shopping list changes;
- not commit model/fake output without validation and confirmation policy.

Критерий завершения:

- happy replacement path covered;
- missing/unknown slot covered;
- multiple-slot change rejected;
- unaffected slots unchanged by test.

### Шаг 8. Добавить exact replacement diff

Цель: пользователь должен видеть точный diff замены до подтверждения.

Diff должен показывать:

- source menu version/draft identifier;
- target meal slot;
- old item;
- new item;
- recipe/version impact accepted by ADR-0009;
- no shopping-list impact in M6B.

Критерий завершения:

- diff changes when committed-relevant replacement data changes;
- diff is stable for same input;
- user-facing summary is test-covered.

### Шаг 9. Добавить stale confirmation protection

Цель: параллельная замена не должна подтверждать устаревший preview.

Добавить tests and behavior for:

- confirmation based on stale source menu version;
- replacement after another replacement changed the same menu;
- recipe version conflict if relevant;
- controlled error and unchanged confirmed state.

Критерий завершения:

- stale confirmation is rejected deterministically;
- latest state remains unchanged after stale attempt;
- error is stable and machine-readable.

### Шаг 10. Добавить optional model-backed experiment, если выбран ADR

Цель: измерить real recipe/replacement generation only after explicit
decision.

Если ADR-0009 выбирает model-backed experiment, добавить bounded adapter/port
и eval command. Если нет, записать skipped reason.

Требования:

- provider/model/prompt/schema version recorded;
- credentials are never read or printed;
- raw output stored only if synthetic inputs and sanitization policy allow it;
- model output validated before persistence/replacement/preview;
- failure leaves confirmed state unchanged.

Критерий завершения:

- experiment measured or explicitly skipped;
- fake generator remains Gate M6B runnable without external provider.

### Шаг 11. Заполнить M6B report and Gate M6B checklist

Цель: остановиться на рефлексии M6, а не продолжить автоматически в shopping
list or Hermes/Telegram.

Создать:

```text
docs/experiments/m6b-recipes-and-replacements.md
```

Report должен содержать:

- цель;
- scope;
- contract/generator/validator decisions;
- recipe persistence decisions;
- replacement/stale-confirmation decisions;
- model-backed experiment status;
- commands run;
- golden/eval metrics;
- what was intentionally not implemented;
- Gate M6B result;
- reflection M6;
- decisions before shopping list/store catalog.

Критерий завершения:

- Gate M6B checklist заполнен;
- remaining assumptions listed;
- relevant questions copied to `docs/decisions/open-questions.md`;
- в отчете явно сказано: не переходить к shopping list/store catalog без
  отдельного задания.

## 7. Gate M6B checklist

Заполнить в `docs/experiments/m6b-recipes-and-replacements.md`:

```markdown
## Gate M6B Checklist

[ ] M6B Codex skill exists and was used for implementation tasks.
[ ] M6B brief exists and was used for routine tasks.
[ ] ADR-0009 or equivalent decision note fixes recipe and replacement strategy.
[ ] RecipeDraft contract has schema_version and fixtures.
[ ] Invalid RecipeDraft returns machine-readable validation errors.
[ ] Fake RecipeDraftGenerator is deterministic and side-effect free.
[ ] Recipe generation does not change active menu by itself.
[ ] Recipes are persisted as versions through application boundary.
[ ] Replacement changes exactly one meal slot.
[ ] Replacement creates a new menu draft/version.
[ ] Unaffected meal slots remain unchanged by tests.
[ ] User-facing replacement diff is exact and stable.
[ ] Stale confirmation after parallel replacement is rejected.
[ ] Recipe/replacement failure leaves confirmed state unchanged.
[ ] Optional model-backed experiment is measured or explicitly skipped.
[ ] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[ ] No shopping list, store catalog, product matching, production Hermes
    plugin, Telegram UX, or direct model writes added.
[ ] `scripts/dev.sh test` passed or deviation recorded.
[ ] `scripts/dev.sh lint` passed or deviation recorded.
[ ] `scripts/dev.sh typecheck` passed or deviation recorded.
[ ] `scripts/dev.sh smoke` passed or deviation recorded.
[ ] M6B golden/eval command passed or skipped with reason.
[ ] `git diff --check` passed.
```

## 8. Reflection M6

Заполнить после Gate M6B:

```markdown
## Reflection M6

### Что оказалось действительно детерминированным?

- [ответ]

### Где нужна модель-судья, а где достаточно кода?

- [ответ]

### Насколько repair loop улучшает результат против повторной генерации?

- [ответ]

### Не стал ли формат слишком сложным для будущей локальной модели?

- [ответ]

### Какие решения нужны перед shopping list and mock catalog?

- [ответ]
```

## 9. Sequence of tasks for Codex

Использовать по одному шагу за запрос. Для каждого шага:

1. Прочитать active M6B skill and `docs/briefs/m7-agent-brief.md`.
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
