# Этап 6. M6A menu draft generation: валидируемый черновик меню без активации

## 1. Цель этапа 6

Этап 6 должен довести проект до ближайшей рефлексивной вехи M6A:

> Подтвержденный профиль и явный planning request превращаются в
> `PlanningContext`, затем в `MenuDraft`, который детерминированно валидируется,
> может пройти bounded repair loop и может получить safe preview, но модель не
> может активировать меню или изменить подтвержденное состояние напрямую.

Главный вопрос этапа:

> Может ли вероятностная или fake generation surface создавать menu drafts,
> которые код проверяет, ремонтирует ограниченно и безопасно останавливает без
> повреждения подтвержденных данных?

Этап 6 заканчивается на Gate M6A и рефлексии M6A. После Gate M6A не переходить
автоматически к recipes, substitutions, shopping list, Hermes plugin,
Telegram UX или production model-backed generation без отдельного задания.

## 2. Основания

Routine M6A tasks начинают с brief, skill и непосредственно затронутых файлов:

- `docs/briefs/m6-agent-brief.md`

Полный контекст открывать только при изменении ADR/stage plan/component
boundary или если brief недостаточен:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 5.md`
- `docs/experiments/m5-intent-router.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0006-profile-vertical-slice.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `docs/decisions/open-questions.md`

Решения из M0-M5 для этого этапа:

- Domain Core не импортирует Hermes, Telegram, ORM, HTTP clients или model SDK.
- Application service владеет transaction boundary и confirmed-state writes.
- M5 оставил menu/recipe/shopping/store/substitution intents unsupported или
  deferred до появления production contracts/workflows.
- Router output не выполняет commit и не создает confirmation напрямую.
- ADR-0006 profile shape остается M4 technical assumption; OQ-004 final
  product profile schema remains open.
- M6A должен начинаться с deterministic fake generator и golden fixtures.
- Model/provider/prompt/logging policy для generation является отдельным
  решением M6A, не наследуется из M5 routing.

## 3. Scope

Разрешено:

- создать Codex skill для M6A;
- принять ADR для menu draft contract, generation strategy, validation,
  repair loop и model experiment boundaries;
- уточнить `PlanningContext`, `MealSlot`, `MenuDraft` и related fixtures;
- определить минимальный one-day menu draft shape, затем расширить до week
  только после зеленых one-day checks;
- построить `PlanningContext` только из confirmed profile data и explicit
  request parameters;
- добавить deterministic fake `MenuDraftGenerator` port/implementation;
- добавить validators для полноты периода, meal slots, strict restrictions,
  equipment, active time, portions, repetition и referential integrity;
- добавить stable machine-readable menu validation errors;
- реализовать bounded repair loop на structured validation errors;
- добавить golden tests на fake generator и repair loop;
- создать safe `OperationPreview` для validated menu draft, если это не
  обходит confirmation/commit;
- добавить M6A eval/golden command, если это нужно для Gate M6A;
- заполнить M6A report и рефлексию.

Запрещено на этом этапе:

- активировать меню напрямую из model/fake output;
- выполнять menu commit без explicit confirmation и safe commit boundary;
- реализовывать recipes, substitutions, shopping list, store catalog или
  product matching;
- подключать production Hermes plugin, Hermes tools/hooks/toolsets или
  Telegram business UX;
- считать M5 router menu intents готовыми к production execution без M6A
  contract/workflow update;
- выбирать production cloud/local model provider без отдельного решения;
- читать, печатать или логировать `.env`, `auth.json`, tokens или credentials;
- добавлять production model/API dependency без отдельного решения;
- трактовать ADR-0006 fixture values as final menu-generation product
  semantics;
- создавать или менять custom Hermes image;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 6:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m5-eval
```

Проверить, что:

- Gate M5 функционально закрыт или явно отложен человеком;
- `docs/experiments/m5-intent-router.md` существует и заполнен;
- ADR-0007 принят;
- M5 router keeps menu/recipe/shopping/store/substitution intents unsupported
  или deferred;
- M4 profile flow и M5 eval runner работают без Hermes, Telegram и external
  model provider;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты.

Если `scripts/dev.sh ...` требует Docker socket access, агент должен запросить
разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 6 считается завершенным, если:

- M6A Codex skill существует и помогает удерживать задачи в границах M6A;
- `docs/briefs/m6-agent-brief.md` используется как первичный контекст для
  routine tasks;
- ADR-0008 или equivalent decision note фиксирует menu draft contract,
  generation strategy, validation, repair loop и model experiment boundaries;
- минимальный `PlanningContext` строится только из confirmed profile data и
  explicit request parameters;
- неизвестные product profile/menu fields не подменены догадками;
- `MenuDraft` имеет `schema_version`, valid/invalid fixtures и deterministic
  validation;
- invalid draft returns stable machine-readable errors;
- fake generator creates deterministic menu drafts from fixtures;
- bounded repair loop has max attempts, logs structured attempts, and stops
  predictably on failure;
- invalid draft cannot become preview for commit;
- model/fake output cannot activate a menu or write confirmed state;
- failure leaves active/confirmed menu state unchanged;
- one-day happy path is green before week expansion;
- week draft, if included in M6A, is covered by golden fixtures;
- optional model-backed generation experiment is measured or explicitly
  skipped with reason;
- Domain Core still has no Hermes, Telegram, ORM, HTTP client or model SDK
  imports;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke`, M6A golden/eval command and `git diff --check`
  pass or deviations are explicitly recorded;
- создан `docs/experiments/m6a-menu-draft-generation.md` с результатом Gate
  M6A и рефлексией.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M6A

Цель: не дать Stage 6 расползтись в recipes, substitutions, shopping list,
Hermes plugin, Telegram UX или direct menu activation.

Создать:

```text
.agents/skills/m6a-menu-draft-generation/SKILL.md
```

Содержимое:

```markdown
---
name: m6a-menu-draft-generation
description: "Use when building the Menu Planner M6A menu draft generation and validation slice: PlanningContext, MealSlot, MenuDraft, deterministic fake generator, validators, bounded repair loop, golden fixtures, safe preview, and M6A report, without recipes, substitutions, shopping list, Hermes plugin, Telegram UX, direct menu activation, or production model dependency."
---

# M6A menu draft generation workflow

## Scope

- Build only validated menu draft generation up to Gate M6A.
- Use confirmed profile data and explicit planning request parameters to build
  `PlanningContext`.
- Add or refine `PlanningContext`, `MealSlot`, `MenuDraft`, generator port,
  fake generator, validators, bounded repair loop, golden fixtures, and safe
  preview.
- Do not implement recipes, substitutions, shopping list, store catalog,
  production Hermes plugin/tools, Telegram UX, or direct menu activation.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m6-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
or when the brief is insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 6.md`
- `docs/experiments/m5-intent-router.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0006-profile-vertical-slice.md`
- `docs/decisions/ADR-0007-intent-router-and-evals.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If profile-field semantics, menu shape, model/provider choice, prompt
   logging, repair limit, or activation policy is blocking, ask the user during
   that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run targeted contract/unit/golden checks first.
8. Run M6A eval/golden checks when the task changes generator, validators, or
   repair behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine fixture, validator, or fake
  generator changes when the brief and affected files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Generator output is untrusted until validated.
- Model/fake output must never activate menu or write confirmed state.
- Invalid drafts must not become commit previews.
- Repair loop must be bounded and use structured validation errors.
- Keep Domain Core independent from Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
```

Критерий завершения: skill валиден локально; проверочный prompt не требуется,
если local validation прошла.

### Шаг 2. Зафиксировать menu draft generation strategy

Цель: не смешать contract, model prompt, repair loop и menu activation в одну
непроверяемую реализацию.

Создать:

```text
docs/decisions/ADR-0008-menu-draft-generation.md
```

ADR должен зафиксировать:

- минимальный M6A menu draft scope: one-day first, week later if accepted;
- `PlanningContext` source policy;
- M6A `MenuDraft` / `MealSlot` shape;
- validator strategy and stable error codes;
- fake generator policy;
- model-backed generation experiment policy;
- prompt/schema versioning, if model experiment is selected;
- raw output logging policy without secrets/private data;
- bounded repair loop max attempts and stop condition;
- preview policy for validated menu draft;
- what remains out of M6A.

Если нужны product decisions по meal slots, profile fields, nutrition, budget,
provider/model или repair limit, агент задает вопрос пользователю. Если выбор
не блокирует minimal fake-generator slice, агент фиксирует technical assumption
и open question.

Критерий завершения:

- ADR-0008 принят;
- нет новых production dependencies без решения;
- M6A можно проверить без Hermes, Telegram и production model provider;
- unresolved product/model decisions перенесены в
  `docs/decisions/open-questions.md`.

### Шаг 3. Уточнить PlanningContext и menu contracts

Цель: создать проверяемый contract до generator implementation.

Добавить или уточнить:

- `PlanningContext`;
- `MealSlot`;
- `MenuDraft`;
- valid/invalid fixtures;
- JSON-compatible schema rules;
- contract validation tests.

Неизвестные продуктовые поля не придумывать. Если поле влияет на смысл меню,
агент должен спросить пользователя или оставить поле вне M6A.

Критерий завершения:

- every changed contract has `schema_version`;
- valid fixtures pass;
- invalid fixtures return stable errors;
- Domain Core remains infrastructure-independent.

### Шаг 4. Реализовать PlanningContext builder

Цель: вход генерации должен быть controlled data, а не raw conversation.

Builder должен использовать только:

- confirmed profile data;
- explicit planning request parameters;
- deterministic defaults accepted by ADR-0008;
- current workflow/user identity where needed for policy.

Запрещено использовать:

- Hermes memory as source of truth;
- raw Telegram text;
- unverified model output;
- final product profile semantics not accepted by decision.

Критерий завершения:

- context builder covered by unit tests;
- missing/unsafe profile fields produce controlled errors or documented
  technical assumptions;
- OQ-004 unresolved fields remain unresolved.

### Шаг 5. Реализовать deterministic fake MenuDraftGenerator

Цель: получить reproducible generation surface before model-backed behavior.

Добавить:

- generator port/interface;
- fake generator implementation;
- golden fixtures for one-day menu draft;
- malformed/invalid fake outputs for validator/repair tests.

Критерий завершения:

- same fixture input produces same draft;
- fake generator has no side effects;
- generator output is validated before further use;
- no external provider, network or secrets required.

### Шаг 6. Реализовать menu validators

Цель: код, а не модель, решает допустимость menu draft.

Validators минимум покрывают:

- period completeness;
- meal slots;
- strict restrictions;
- equipment;
- active time;
- portions;
- repetition;
- referential integrity.

Если для validator нужен product choice, агент спрашивает пользователя или
фиксирует technical assumption в ADR/open questions.

Критерий завершения:

- validators have unit/contract tests;
- errors are machine-readable and suitable for repair loop;
- invalid drafts cannot produce safe preview.

### Шаг 7. Реализовать bounded repair loop

Цель: repair должен быть конечным, измеримым и безопасным.

Repair loop должен:

- принимать structured validation errors;
- иметь explicit max attempts;
- логировать attempt metadata без secrets/private data;
- останавливаться с controlled failure;
- never activate or commit a menu;
- keep active/confirmed state unchanged on failure.

Критерий завершения:

- happy repair path covered with fake generator;
- max-attempt failure covered;
- malformed output covered;
- failure leaves confirmed state unchanged.

### Шаг 8. Добавить safe preview для validated MenuDraft

Цель: проверить путь к будущему confirmation без прямой активации меню.

Preview допустим только для validated draft и должен:

- use canonical payload for summary hash;
- include user-facing summary suitable for later adapter copy;
- not create active menu version by itself;
- not bypass M3 confirmation/safe commit boundary.

Если activation commit semantics нужны уже в M6A, агент должен спросить
пользователя. Default M6A: preview only, no active menu commit.

Критерий завершения:

- invalid draft cannot create preview;
- preview hash changes when committed-relevant menu data changes;
- no confirmed menu state is written by preview.

### Шаг 9. Добавить optional model-backed experiment, если выбран ADR

Цель: измерить real model generation only after explicit decision.

Если ADR-0008 выбирает model-backed experiment, добавить bounded adapter/port
и eval command. Если нет, записать skipped reason.

Требования:

- provider/model/prompt/schema version recorded;
- credentials are never read or printed;
- raw output stored only if synthetic inputs and sanitization policy allow it;
- model output validated before repair/preview;
- failure leaves confirmed state unchanged.

Критерий завершения:

- experiment measured or explicitly skipped;
- fake generator remains Gate M6A runnable without external provider.

### Шаг 10. Расширить one-day draft до week draft, если one-day gate green

Цель: не усложнять неделю до того, как один день доказан.

Расширять до week draft только если:

- one-day contracts, fake generation, validators and repair are green;
- ADR-0008 accepts period shape;
- golden fixtures remain readable.

Критерий завершения:

- week fixtures pass golden checks;
- same fixture input produces same domain result;
- validation covers missing/extra days or slots.

### Шаг 11. Заполнить M6A report и Gate M6A checklist

Цель: остановиться на рефлексии, а не продолжить автоматически в recipes or
shopping.

Создать:

```text
docs/experiments/m6a-menu-draft-generation.md
```

Report должен содержать:

- цель;
- scope;
- contract/generator/validator decisions;
- model-backed experiment status;
- commands run;
- golden/eval metrics;
- what was intentionally not implemented;
- Gate M6A result;
- reflection;
- decisions before recipes/substitutions/shopping.

Критерий завершения:

- Gate M6A checklist заполнен;
- remaining assumptions listed;
- relevant questions copied to `docs/decisions/open-questions.md`;
- в отчете явно сказано: не переходить к recipes/substitutions/shopping без
  отдельного задания.

## 7. Gate M6A checklist

Заполнить в `docs/experiments/m6a-menu-draft-generation.md`:

```markdown
## Gate M6A Checklist

[ ] M6A Codex skill exists and was used for implementation tasks.
[ ] M6A brief exists and was used for routine tasks.
[ ] ADR-0008 or equivalent decision note fixes menu draft generation strategy.
[ ] PlanningContext uses only confirmed profile data and explicit request
    parameters.
[ ] Unknown final product profile/menu fields are not invented.
[ ] MenuDraft and MealSlot contracts have schema_version and fixtures.
[ ] Invalid MenuDraft returns machine-readable validation errors.
[ ] Fake MenuDraftGenerator is deterministic and side-effect free.
[ ] One-day golden happy path passes before week expansion.
[ ] Week draft, if included, is covered by golden fixtures.
[ ] Bounded repair loop has explicit max attempts and controlled failure.
[ ] Malformed/invalid generator output cannot create preview.
[ ] Invalid draft cannot become preview for commit.
[ ] Model/fake output cannot activate menu or write confirmed state.
[ ] Failure leaves active/confirmed menu state unchanged.
[ ] Optional model-backed experiment is measured or explicitly skipped.
[ ] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[ ] No recipes, substitutions, shopping list, store catalog, production Hermes
    plugin, Telegram UX, or direct menu activation added.
[ ] No Hermes image mutation or custom Hermes image added.
[ ] scripts/dev.sh test passes.
[ ] scripts/dev.sh lint passes.
[ ] scripts/dev.sh typecheck passes.
[ ] scripts/dev.sh smoke passes.
[ ] M6A golden/eval command passes.
[ ] git diff --check passes.
[ ] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[ ] M6A report is filled.
```

## 8. Рефлексия M6A

Ответить перед переходом к recipes/substitutions:

- Достаточно ли `PlanningContext` отделен от raw conversation и Hermes memory?
- Какие profile fields реально понадобились для menu draft generation?
- Какие menu validators действительно deterministic, а где нужен human/model
  judgment later?
- Насколько repair loop улучшает результат против полной regeneration?
- Не стал ли `MenuDraft` format слишком сложным для future local model?
- Какие validation errors должны стать user-facing?
- Нужно ли менять M5 taxonomy, чтобы menu generation requests стали
  draft-producing instead of unsupported?
- Какой model/provider/prompt policy нужен перед real model generation?
- Какие решения нужны перед recipes, substitutions and shopping list?

## 9. Последовательность задач для Codex

Каждую задачу передавать отдельно. Агент должен задавать вопросы по ходу
выполнения конкретного шага, если обнаруживает блокирующее решение. Если
вопрос не блокирует минимальный проверяемый шаг, агент должен продолжить с
явным technical assumption и зафиксировать вопрос в
`docs/decisions/open-questions.md`.

### Задача 1

```text
Используй $m6a-menu-draft-generation.
Ничего не реализуй в application code.
Создай .agents/skills/m6a-menu-draft-generation/SKILL.md по Stage 6.
В конце запусти git diff --check и покажи измененные файлы.
```

### Задача 2

```text
Используй $m6a-menu-draft-generation.
Создай ADR-0008 для menu draft contract, generation strategy, validation,
repair loop и model experiment boundaries.
Если нужны решения по meal slots, profile fields, model/provider или repair
limit, задай вопрос по ходу задачи.
```

### Задача 3

```text
Используй $m6a-menu-draft-generation.
Уточни только PlanningContext, MealSlot, MenuDraft contracts, fixtures и
contract tests.
Не реализуй generator, repair loop, recipes, shopping list, Hermes или
Telegram.
```

### Задача 4

```text
Используй $m6a-menu-draft-generation.
Реализуй PlanningContext builder только из confirmed profile data и explicit
planning request parameters.
Если profile field semantics недостаточны, задай вопрос или зафиксируй
technical assumption.
```

### Задача 5

```text
Используй $m6a-menu-draft-generation.
Добавь deterministic fake MenuDraftGenerator и one-day golden fixtures.
Не подключай external model provider.
```

### Задача 6

```text
Используй $m6a-menu-draft-generation.
Добавь menu validators и stable machine-readable validation errors.
Покрой invalid drafts; не создавай preview или commit в этой задаче.
```

### Задача 7

```text
Используй $m6a-menu-draft-generation.
Реализуй bounded repair loop на fake generator и structured validation errors.
Покрой max-attempt failure и malformed output.
```

### Задача 8

```text
Используй $m6a-menu-draft-generation.
Добавь safe OperationPreview только для validated MenuDraft.
Preview не должен активировать меню или писать confirmed state.
```

### Задача 9

```text
Используй $m6a-menu-draft-generation.
Если ADR-0008 выбрал model-backed experiment, добавь bounded experiment и
eval report.
Если нужны credentials/provider/model decisions, сначала задай вопрос.
Если experiment не нужен для Gate M6A, зафиксируй skipped reason.
```

### Задача 10

```text
Используй $m6a-menu-draft-generation.
Если one-day gate green и ADR-0008 разрешает, расширь golden fixtures и
validators до week draft.
Не добавляй recipes, substitutions или shopping list.
```

### Задача 11

```text
Используй $m6a-menu-draft-generation.
Заполни docs/experiments/m6a-menu-draft-generation.md и Gate M6A checklist.
Не переходи к recipes, substitutions, shopping list, Hermes plugin или
Telegram UX.
```
