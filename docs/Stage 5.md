# Этап 5. M5 Intent Router: eval harness и безопасная маршрутизация текста

## 1. Цель этапа 5

Этап 5 должен довести проект до вехи M5:

> Свободный текст превращается в schema-valid `ParsedIntent` и
> `PolicyDecision` с измеримым качеством, контролируемыми ошибками и нулевыми
> опасными автокоммитами, без Hermes plugin, Telegram UX, menu generation,
> recipes, shopping list и production business workflows за пределами M4
> profile vertical slice.

Главный вопрос этапа:

> Какой Intent Router достаточно безопасен, чтобы позже подключить Hermes и
> Telegram, не передавая свободному тексту право напрямую менять состояние?

Этап 5 заканчивается на Gate M5 и рефлексии M5. После Gate M5 не переходить
автоматически к M6 menu/recipe generation, Hermes plugin, Telegram UX или
реальному пользователю без отдельного задания.

## 2. Основания

Routine M5 tasks начинают с brief, skill и непосредственно затронутых файлов:

- `docs/briefs/m5-agent-brief.md`

Полный контекст открывать только при изменении ADR/stage plan/component
boundary или если brief недостаточен:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 4.md`
- `docs/experiments/m4-profile-vertical-slice.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0006-profile-vertical-slice.md`
- `docs/decisions/open-questions.md`

Решения из M0-M4 для этого этапа:

- `ParsedIntent`, `PolicyDecision`, operation classes, state machine и stable
  errors уже существуют в Domain Core.
- M4 доказал deterministic profile flow через CLI/test API без Hermes,
  Telegram и LLM.
- Router не должен выполнять commit, писать в БД или вызывать business command
  напрямую. Он возвращает intent, policy decision или controlled error.
- Policy decision должен строиться через M2/M4 workflow/policy surface, а не
  через догадки модели.
- User-facing confirmation TTL/copy, adapter-level idempotency key mapping и
  production Hermes/Telegram mapping остаются открытыми adapter decisions.
- Финальная продуктовая схема профиля остаётся открытым вопросом OQ-004.

## 3. Scope

Разрешено:

- создать Codex skill для M5;
- принять ADR для Intent Router placement, eval strategy и risk thresholds;
- определить M5 intent taxonomy, привязанную к текущим `WorkflowAction` и
  operation classes;
- добавить versioned eval dataset для свободного текста;
- разделить eval dataset на development и holdout;
- включить в dataset read-only, draft-producing, state-changing,
  administrative, unsupported, incomplete, ambiguous, conflicting,
  prompt-injection и mixed-intent cases;
- реализовать offline eval runner и метрики;
- реализовать deterministic/rule-based baseline router;
- добавить router port/interface и fake/model-backed candidates, если они
  явно выбраны ADR;
- измерять schema-valid rate, intent accuracy, parameter extraction,
  ambiguity/missing-field recall, dangerous misroute rate, latency и cost,
  если cost доступен без раскрытия secrets;
- соединить router output с существующим policy decision без исполнения
  state-changing command;
- заполнить M5 report и рефлексию.

Запрещено на этом этапе:

- выполнять commit из router;
- автоматически применять state-changing intent без preview/confirmation;
- добавлять menu generation, recipe generation, shopping list, store catalog
  или substitutions;
- реализовывать production Hermes plugin, Hermes tools, hooks, toolsets или
  Telegram business UX;
- считать Telegram callback или Hermes turn metadata выбранным idempotency
  source;
- создавать или менять custom Hermes image;
- читать, печатать или логировать `.env`, `auth.json`, tokens или credentials;
- добавлять production model/API dependency без отдельного решения;
- считать self-reported confidence достаточным без eval-калибровки;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 5:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
```

Проверить, что:

- Gate M4 функционально закрыт или явно отложен человеком;
- `docs/experiments/m4-profile-vertical-slice.md` существует и заполнен;
- ADR-0004, ADR-0005 и ADR-0006 приняты;
- M4 profile flow работает без Hermes, Telegram и LLM;
- `compose.yaml` по-прежнему не содержит `build:` для Hermes;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты;
- существующие tests не требуют реального Hermes agent turn или Telegram.

Если `scripts/dev.sh ...` требует Docker socket access, агент должен запросить
разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 5 считается завершенным, если:

- M5 Codex skill существует и помогает удерживать задачи в границах M5;
- ADR-0007 или equivalent decision note фиксирует router placement, eval
  strategy, candidate variants, confidence policy и Gate thresholds;
- intent taxonomy M5 явно связана с текущими workflow actions и operation
  classes;
- eval dataset versioned, воспроизводим и разделён на development/holdout;
- dataset покрывает dangerous state-changing, administrative, ambiguous,
  incomplete, unsupported, prompt-injection и mixed-intent cases;
- router всегда возвращает schema-valid `ParsedIntent` либо controlled
  machine-readable error;
- policy decision строится через существующий workflow/policy code;
- administrative intent/action не становится пользовательски исполняемым;
- ambiguous or incomplete dangerous input routes to clarification;
- state-changing input routes to preview/confirmation policy, not commit;
- false automatic execution rate для state-changing/admin cases равен `0` на
  M5 eval set;
- confidence thresholds основаны на eval result или явно оставлены open
  question, если выбранный router не готов к threshold;
- eval runner сохраняет model/provider/version, router version,
  prompt/schema version, parsed output, policy decision, errors, latency и
  metrics без secrets;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke`, M5 eval command и `git diff --check` проходят или
  отклонения явно зафиксированы;
- создан `docs/experiments/m5-intent-router.md` с результатом Gate M5 и
  рефлексией.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M5

Цель: не дать Stage 5 расползтись в M6 generation, Hermes plugin, Telegram UX
или production menu workflows.

Создать:

```text
.agents/skills/m5-intent-router/SKILL.md
```

Содержимое:

```markdown
---
name: m5-intent-router
description: "Use when building the Menu Planner M5 Intent Router and eval harness: intent taxonomy, versioned eval datasets, router candidates, ParsedIntent validation, policy decisions, ambiguity handling, safety metrics, and M5 reports, without menu generation, Hermes plugin, Telegram UX, recipes, shopping list, or direct commit."
---

# M5 Intent Router workflow

## Scope

- Build only the measured Intent Router and eval harness.
- Convert user text into schema-valid `ParsedIntent`, controlled errors, and
  `PolicyDecision`.
- Reuse existing Domain Core contracts, workflow policy, operation classes,
  stable errors, and M4 profile flow boundaries.
- Add versioned eval datasets, runner, metrics, and safety tests.
- Do not execute commits, generate menus/recipes, create shopping lists, build
  production Hermes plugin/tools, or add Telegram UX.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m5-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
or when the brief is insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 5.md`
- `docs/experiments/m4-profile-vertical-slice.md`
- `docs/decisions/ADR-0004-domain-contracts-and-validation.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0006-profile-vertical-slice.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If router placement, model/provider choice, confidence threshold, or
   dangerous-action policy is blocking, ask the user during that step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run the narrowest relevant checks first.
8. Run M5 eval checks when the task changes router behavior or dataset.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine fixture, test, or router
  changes when the brief and affected files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Router returns intent/policy/error only; it must not commit application
  state.
- Workflow policy remains the authority for allowed actions and confirmation.
- State-changing intents require preview/confirmation and never direct commit.
- Administrative intents are denied in user workflow.
- Self-reported confidence is not trusted without eval calibration.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
```

Проверка:

```text
$m5-intent-router

Ничего не меняй.
Опиши границы M5, safety metrics и что нельзя реализовывать на этом этапе.
```

Критерий завершения: Codex явно говорит, что M5 ограничен Intent Router/evals,
не включает menu generation, production Hermes plugin, Telegram UX или direct
commit.

### Шаг 2. Зафиксировать Intent Router и eval strategy

Цель: не строить router как набор случайных prompt или rules без измеримой
границы.

Создать:

```text
docs/decisions/ADR-0007-intent-router-and-evals.md
```

ADR должен зафиксировать:

- где живет router в M5: application service, adapter layer, model adapter или
  другой boundary;
- какие router variants сравниваются в M5;
- какие variants являются target, baseline или experiment;
- как router output валидируется как `ParsedIntent`;
- как применяется existing workflow/policy decision;
- какие intent names входят в M5 и какие намеренно unsupported;
- как разделены development и holdout eval sets;
- какие метрики считаются Gate metrics;
- policy по confidence и почему self-reported confidence не является
  достаточным доказательством;
- как логировать raw/model output без secrets;
- что не решается в M5.

Если нужен выбор model/provider, confidence threshold, dangerous-action policy
или router placement, агент задает вопрос пользователю. Если выбор не
блокирует минимальный eval harness, агент фиксирует technical assumption и
open question.

Критерий завершения:

- ADR-0007 принят;
- нет новых production dependencies без решения;
- M5 можно проверить без Hermes, Telegram и production user channel;
- unresolved product/safety decisions перенесены в
  `docs/decisions/open-questions.md`.

### Шаг 3. Определить M5 intent taxonomy и expected outputs

Цель: создать измеримую поверхность до подключения модели.

Зафиксировать M5 taxonomy, связанную с текущими `WorkflowAction`:

- `show_status`;
- `submit_profile_draft`;
- `confirm_profile_draft`;
- `cancel_workflow`;
- `install_skill` или equivalent administrative denial fixture;
- `unsupported`;
- будущие menu/recipe/shopping intents только как unsupported или deferred,
  если их workflow ещё не реализован как production slice.

Для каждого intent указать:

- operation class;
- required parameters;
- missing field policy;
- ambiguity policy;
- scope/persistence;
- whether confirmation is required;
- expected policy decision in representative workflow states.

Критерий завершения:

- taxonomy покрыта tests или fixtures;
- unknown/future intents не становятся allowed по умолчанию;
- administrative action denied проверяется через existing policy/error path.

### Шаг 4. Создать versioned eval dataset

Цель: качество router должно обсуждаться по данным, а не по впечатлению.

Создать eval fixtures в выбранном ADR-0007 месте, например:

```text
fixtures/evals/intent_router/
```

Dataset должен содержать минимум:

- однозначные read-only сообщения;
- profile draft-producing сообщения;
- profile state-changing confirmation/cancel messages;
- administrative requests;
- unsupported food/menu requests, если M6 ещё не реализован;
- incomplete messages;
- ambiguous strict restriction vs soft preference messages;
- conflicting workflow-state messages;
- prompt injection attempts;
- mixed-intent messages;
- typos and conversational variants.

Для каждого case зафиксировать expected:

- `ParsedIntent`;
- `operation_class`;
- parameters;
- missing fields;
- ambiguities;
- scope/persistence;
- `requires_confirmation`;
- expected `PolicyDecision` outcome for a stated workflow state;
- safety labels, including dangerous state-changing/admin where applicable.

Критерий завершения:

- dataset has schema/version metadata;
- development и holdout split reproducible;
- fixtures не содержат secrets или private user data;
- reviewable negative cases присутствуют до реализации model-backed router.

### Шаг 5. Реализовать eval runner и metrics skeleton

Цель: получить воспроизводимую команду оценки до оптимизации router.

Runner должен:

- загрузить eval dataset;
- вызвать выбранный router candidate;
- валидировать `ParsedIntent`;
- вызвать existing policy decision для заданного workflow state;
- сравнить expected vs actual;
- посчитать metrics;
- сохранить machine-readable report без secrets.

Минимальные metrics:

- schema-valid rate;
- exact intent accuracy;
- operation-class accuracy;
- parameter extraction accuracy;
- ambiguity recall;
- missing-field recall;
- expected policy outcome accuracy;
- dangerous false automatic execution rate;
- administrative denial rate;
- unsupported intent handling rate;
- latency, если измеряется локально;
- cost, если доступен без раскрытия credentials.

Критерий завершения:

- eval command запускается локально;
- failing cases печатаются как короткий machine-readable summary;
- no secrets in output;
- runner можно запускать в CI/local check без real Hermes/Telegram.

### Шаг 6. Реализовать deterministic baseline router

Цель: иметь понятный нижний baseline и safety fallback до model-backed
экспериментов.

Baseline может быть rule-based и обязан:

- возвращать schema-valid `ParsedIntent` или controlled error;
- покрывать очевидные M5 cases из development set;
- отдавать unsupported/clarify для неизвестных или рискованных формулировок;
- не доверять user text как команде на commit;
- не выполнять side effects.

Критерий завершения:

- baseline проходит contract/unit tests;
- policy decision применён отдельно от parsing;
- dangerous state-changing/admin cases не становятся automatic allow;
- failures пригодны для анализа и улучшения dataset/router.

### Шаг 7. Добавить model-backed router experiment, если выбран ADR

Цель: сравнить модельный routing с baseline без превращения модели в
исполнителя команд.

Если ADR-0007 выбирает model-backed candidate, добавить только adapter/port и
bounded experiment.

Требования:

- model/provider/version явно записываются в eval report;
- prompt/schema version явно записываются в eval report;
- raw output сохраняется только если не содержит secrets/private data;
- output проходит `ParsedIntent` validation;
- invalid output становится controlled error;
- confidence калибруется через eval и не является самостоятельным правом на
  execution;
- внешние provider credentials не читаются и не печатаются.

Если для шага нужны credentials, network или provider/model выбор, агент
должен спросить пользователя. Если модельный experiment не нужен для Gate M5,
оставить его skipped с причиной в M5 report.

Критерий завершения:

- model-backed candidate либо измерен, либо явно skipped;
- skipped reason documented;
- baseline router остается runnable без external provider.

### Шаг 8. Соединить router output с policy decision без execution

Цель: доказать безопасную цепочку:

```text
text
→ ParsedIntent
→ validation
→ PolicyDecision
→ allowed next action / clarification / deny / confirm
```

Запрещено на этом шаге:

- вызывать profile commit;
- создавать confirmation;
- писать confirmed application state;
- подключать Hermes/Telegram callbacks.

Критерий завершения:

- policy decision проверяется для representative workflow states;
- state-changing intent возвращает confirmation policy, not commit;
- administrative intent denied;
- unsupported intent controlled;
- ambiguous dangerous intent routes to clarification.

### Шаг 9. Покрыть safety и regression tests

Цель: сделать опасные misroutes невозможными как тихая регрессия.

Покрыть минимум:

- prompt injection asking to ignore rules and commit;
- "delete/update/save permanently" profile-like messages without required
  fields;
- ambiguous strict restriction vs soft preference;
- mixed read-only plus state-changing request;
- administrative tool/model/skill/secret request;
- unsupported menu generation request before M6;
- malformed router output;
- router confidence high but policy denies;
- workflow state conflict.

Критерий завершения:

- negative tests проходят;
- dangerous automatic execution metric remains zero;
- controlled errors use stable machine-readable codes;
- failures do not mutate M4 profile state.

### Шаг 10. Выбрать router variant и threshold policy

Цель: принять M5 decision на основании eval evidence.

На основе runner report обновить ADR-0007 или decision log:

- chosen router variant for next milestone;
- confidence thresholds by operation class, если выбраны;
- fallback behavior below threshold;
- clarification behavior;
- unsupported/admin behavior;
- known weaknesses and dataset gaps;
- whether model-backed routing is accepted, rejected or deferred.

Если evidence недостаточно, агент должен задать вопрос пользователю:
отложить Gate M5, сузить intent taxonomy или принять более conservative
baseline.

Критерий завершения:

- decision основан на metrics;
- state-changing/admin dangerous false automatic execution rate is zero;
- unresolved choices recorded in open questions;
- M5 не выбирает production Telegram/Hermes UX.

### Шаг 11. Заполнить M5 report и Gate M5 checklist

Цель: остановиться на рефлексии, а не продолжить автоматически в M6.

Создать:

```text
docs/experiments/m5-intent-router.md
```

Report должен содержать:

- цель;
- scope;
- router variants;
- dataset version and split;
- commands run;
- metrics;
- dangerous failures, if any;
- selected/accepted/deferred router decision;
- what was intentionally not implemented;
- Gate M5 result;
- reflection;
- decisions before M6.

Критерий завершения:

- Gate M5 checklist заполнен;
- eval artifacts documented;
- remaining assumptions listed;
- relevant questions copied to `docs/decisions/open-questions.md`;
- в отчете явно сказано: не переходить к M6 без отдельного задания.

## 7. Gate M5 checklist

Заполнить в `docs/experiments/m5-intent-router.md`:

```markdown
## Gate M5 Checklist

[ ] M5 Codex skill exists and was used for implementation tasks.
[ ] ADR-0007 or equivalent decision note fixes router/eval strategy.
[ ] Intent taxonomy is tied to current workflow actions and operation classes.
[ ] Unknown/future intents do not become allowed by default.
[ ] Eval dataset is versioned and split into development/holdout.
[ ] Dataset covers read-only, draft-producing, state-changing, administrative,
    unsupported, incomplete, ambiguous, conflicting, prompt-injection, and
    mixed-intent cases.
[ ] Router returns schema-valid ParsedIntent or controlled machine-readable
    error.
[ ] PolicyDecision is produced through existing workflow/policy code.
[ ] Administrative user-channel requests are denied.
[ ] Ambiguous dangerous input routes to clarification.
[ ] State-changing input routes to preview/confirmation policy, not commit.
[ ] Dangerous state-changing/admin false automatic execution rate is zero.
[ ] Confidence thresholds are eval-based or explicitly deferred.
[ ] Eval runner records router/model/schema versions, parsed output, policy
    decision, errors, latency and metrics without secrets.
[ ] Baseline router runs without Hermes, Telegram, external provider, or
    secrets.
[ ] Model-backed candidate is measured or explicitly skipped with reason.
[ ] No menu generation, recipes, shopping list, store catalog, production
    Hermes plugin, Telegram UX, or direct commit added.
[ ] No Hermes image mutation or custom Hermes image added.
[ ] scripts/dev.sh test passes.
[ ] scripts/dev.sh lint passes.
[ ] scripts/dev.sh typecheck passes.
[ ] scripts/dev.sh smoke passes.
[ ] M5 eval command passes.
[ ] git diff --check passes.
[ ] Secret scan/reporting does not expose .env, auth.json, tokens or
    credentials.
[ ] M5 report is filled.
```

## 8. Рефлексия M5

Ответить перед переходом к M6:

- Достаточно ли текущей intent taxonomy для следующего menu generation
  milestone?
- Какие intents нужно удалить, сузить или оставить unsupported?
- Где rules надежнее и дешевле model-backed routing?
- Достаточно ли eval dataset покрывает dangerous state-changing/admin
  misroutes?
- Какие thresholds действительно подтверждены measurements?
- Какие ambiguity cases лучше переводить в guided buttons/forms?
- Может ли router placement позже перейти в Hermes adapter без изменения
  Domain Core?
- Какие fields profile остаются слишком техническими для menu workflows?
- Какие данные можно безопасно передавать модели, а какие должны оставаться
  только в deterministic code?
- Какие решения нужно принять перед M6 menu draft generation?

## 9. Последовательность задач для Codex

Каждую задачу передавать отдельно. Агент должен задавать вопросы по ходу
выполнения конкретного шага, если обнаруживает блокирующее решение. Если
вопрос не блокирует минимальный проверяемый шаг, агент должен продолжить с
явным technical assumption и зафиксировать вопрос в
`docs/decisions/open-questions.md`.

### Задача 1

```text
Используй $m5-intent-router.
Ничего не реализуй в application code.
Создай .agents/skills/m5-intent-router/SKILL.md по Stage 5.
В конце запусти git diff --check и покажи измененные файлы.
```

### Задача 2

```text
Используй $m5-intent-router.
Создай ADR-0007 для Intent Router placement, eval strategy, candidate
variants, metrics и Gate thresholds.
Если нужен выбор model/provider, confidence threshold или router boundary,
задай вопрос по ходу задачи.
```

### Задача 3

```text
Используй $m5-intent-router.
Определи только M5 intent taxonomy и expected outputs fixtures.
Не реализуй router, eval runner, Hermes, Telegram или menu generation.
```

### Задача 4

```text
Используй $m5-intent-router.
Создай versioned eval dataset для Intent Router с development/holdout split.
Покрой dangerous state-changing/admin, ambiguity, prompt injection,
unsupported и mixed-intent cases.
```

### Задача 5

```text
Используй $m5-intent-router.
Добавь eval runner и metrics skeleton.
Runner должен валидировать ParsedIntent и PolicyDecision, но не выполнять
business commands или commit.
```

### Задача 6

```text
Используй $m5-intent-router.
Реализуй deterministic baseline router для M5 dataset.
Не подключай external model provider, Hermes или Telegram.
```

### Задача 7

```text
Используй $m5-intent-router.
Если ADR-0007 выбрал model-backed candidate, добавь bounded model router
experiment с eval report.
Если нужны credentials/provider/model decisions, сначала задай вопрос.
Если experiment не нужен для Gate M5, зафиксируй skipped reason.
```

### Задача 8

```text
Используй $m5-intent-router.
Соедини router output с existing workflow/policy decision без execution.
State-changing intent должен возвращать confirmation policy, not commit.
```

### Задача 9

```text
Используй $m5-intent-router.
Добавь safety/regression tests для prompt injection, admin requests,
ambiguous dangerous text, high-confidence deny, malformed router output и
workflow state conflict.
```

### Задача 10

```text
Используй $m5-intent-router.
На основании eval metrics обнови ADR-0007 или decision log выбранным router
variant и threshold/fallback policy.
Если evidence недостаточно, задай вопрос: сузить taxonomy, принять conservative
baseline или отложить Gate M5.
```

### Задача 11

```text
Используй $m5-intent-router.
Заполни docs/experiments/m5-intent-router.md и Gate M5 checklist.
Не переходи к M6.
```
