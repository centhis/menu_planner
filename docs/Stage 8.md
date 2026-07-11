# Этап 8. M7 deterministic shopping list and mock catalog

## 1. Цель этапа 8

Этап 8 должен довести проект до ближайшей рефлексивной вехи M7:

> Подтвержденное меню, версии рецептов и snapshot mock-каталога превращаются
> детерминированным кодом в версионированный shopping list, связанный с
> конкретной версией меню и snapshot, без модельной арифметики и без реального
> магазина.

Главный вопрос этапа:

> Достаточна ли модель данных ингредиентов, единиц и catalog snapshot, чтобы
> повторный расчет покупок был детерминированным, тестируемым и безопасным при
> замене блюда?

Этап 8 заканчивается на Gate M7 и точке решения о ценах/наличии в MVP. После
Gate M7 не переходить автоматически к Hermes plugin, Telegram UX, real store
integration или production model-backed matching без отдельного задания.

## 2. Основания

Routine M7 tasks начинают с brief, skill и непосредственно затронутых файлов:

- `docs/briefs/m8-agent-brief.md`

Полный контекст открывать только при изменении ADR/stage plan/component
boundary или если brief недостаточен:

- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 7.md`
- `docs/experiments/m6b-recipes-and-replacements.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0008-menu-draft-generation.md`
- `docs/decisions/ADR-0009-recipes-and-replacements.md`
- `docs/decisions/open-questions.md`

Решения из M0-M6B для этого этапа:

- Domain Core не импортирует Hermes, Telegram, ORM, HTTP clients или model SDK.
- Application service владеет persistence, repositories и transaction boundary.
- M6B recipes сохраняются версионированно через application boundary.
- M6B replacement локален и меняет ровно один meal slot.
- M6B не реализовал shopping list, store catalog, product matching, prices,
  packages, aisle data or purchase arithmetic.
- Итоговый shopping list должен строиться только deterministic code.
- Сырые store pages and external catalog data are untrusted.

## 3. Scope

Разрешено:

- создать Codex skill для M7;
- принять ADR для shopping-list contracts, unit policy, mock catalog snapshot,
  matching policy, versioning, checklist updates and disambiguation;
- создать dictionary of normalized ingredients and supported units;
- реализовать conversions only for supported dimensions;
- масштабировать ingredients by recipe portions;
- объединять одинаковые normalized ingredients;
- вычитать leftovers/pantry только если ADR-0010 явно принимает источник
  таких данных; otherwise record as out of M7 or zero-default assumption;
- создать `StoreCatalogProvider` interface;
- реализовать deterministic `MockStoreCatalogProvider` with snapshot;
- сделать product matching fixed or confirmable for first M7 step;
- рассчитывать packages and cost кодом;
- создать shopping list version linked to menu version and catalog snapshot;
- реализовать exact checklist item update by `shopping_item_id`;
- для текстового "молоко куплено" требовать disambiguation при нескольких
  совпадениях;
- добавить property tests для units, packages and rounding;
- добавить predictable shopping-list diff after one-slot replacement;
- заполнить M7 report and decision point.

Запрещено на этом этапе:

- подключать real store API, scraper, live prices, live availability or raw
  store HTML;
- использовать модель для arithmetic, unit conversion, matching, rounding,
  package calculation or checklist mutation;
- подключать production Hermes plugin, Hermes tools/hooks/toolsets или
  Telegram business UX;
- выбирать production cloud/local model provider без отдельного решения;
- читать, печатать или логировать `.env`, `auth.json`, tokens или credentials;
- добавлять production model/API dependency без отдельного решения;
- менять confirmed menu/recipe state при построении shopping list;
- делать implicit product matching from free text without confirmation or
  deterministic rule;
- создавать или менять custom Hermes image;
- подставлять значения для полей, помеченных `[ТРЕБУЕТ РЕШЕНИЯ]`.

## 4. Entry criteria

Перед началом Stage 8:

```bash
git status --short
git diff --check
scripts/dev.sh test
scripts/dev.sh lint
scripts/dev.sh typecheck
scripts/dev.sh smoke
scripts/dev.sh m6b-eval
```

Проверить, что:

- Gate M6B функционально закрыт или явно отложен человеком;
- `docs/experiments/m6b-recipes-and-replacements.md` существует и заполнен;
- ADR-0009 принят;
- recipes are versioned and replacement changes exactly one meal slot;
- M6B не реализовал shopping list, store catalog, product matching, prices,
  packages, aisle data or purchase arithmetic;
- `.env`, credentials, `auth.json`, tokens и private keys не открывались и не
  попадают в отчеты.

Если `scripts/dev.sh ...` требует Docker socket access, агент должен запросить
разрешение на команду и не скрывать отказ или ошибку.

## 5. Acceptance criteria

Этап 8 считается завершенным, если:

- M7 Codex skill существует и помогает удерживать задачи в границах M7;
- `docs/briefs/m8-agent-brief.md` используется как первичный контекст для
  routine tasks;
- ADR-0010 или equivalent decision note фиксирует shopping-list contracts,
  unit policy, mock catalog snapshot, matching, versioning, checklist updates
  and disambiguation;
- normalized ingredient and unit contracts have `schema_version`, valid and
  invalid fixtures;
- unknown unit or unsupported dimension returns controlled error, not guess;
- ingredient scaling and merging are deterministic and property-tested;
- package and cost calculations are performed by code and property-tested;
- `MockStoreCatalogProvider` returns deterministic snapshot data;
- product matching is fixed or explicitly confirmable for M7;
- shopping list version is linked to menu version and catalog snapshot;
- same inputs create the same shopping list;
- one-slot replacement creates predictable shopping-list diff;
- checklist item status changes only by exact `shopping_item_id`;
- ambiguous text checklist update requires disambiguation;
- failure leaves confirmed menu, recipes and shopping list state unchanged;
- Domain Core still has no Hermes, Telegram, ORM, HTTP client or model SDK
  imports;
- `scripts/dev.sh test`, `scripts/dev.sh lint`, `scripts/dev.sh typecheck`,
  `scripts/dev.sh smoke`, M7 golden/eval command and `git diff --check` pass
  or deviations are explicitly recorded;
- создан `docs/experiments/m7-shopping-list-and-mock-catalog.md` с результатом
  Gate M7 и точкой решения о prices/availability.

## 6. Шаги этапа

### Шаг 1. Создать Codex skill для M7

Цель: не дать Stage 8 расползтись в real store integration, Hermes/Telegram
или model-driven arithmetic.

Создать:

```text
.agents/skills/m7-shopping-list-catalog/SKILL.md
```

Содержимое:

```markdown
---
name: m7-shopping-list-catalog
description: "Use when building the Menu Planner M7 deterministic shopping list and mock catalog slice: normalized ingredients, supported units, deterministic conversions, portion scaling, ingredient merging, StoreCatalogProvider, MockStoreCatalogProvider snapshots, package and cost calculation, shopping list versions, checklist item updates, disambiguation, property tests, and M7 report, without real store integration, raw store HTML, Hermes plugin, Telegram UX, model arithmetic, or production model dependency."
---

# M7 shopping list and mock catalog workflow

## Scope

- Build only deterministic shopping list and mock catalog up to Gate M7.
- Add or refine normalized ingredients, units, conversions, catalog snapshot,
  product matching, package/cost calculation, shopping list versioning,
  checklist updates, disambiguation, golden/property tests, and M7 report.
- Use confirmed menu/recipe versions and reviewed catalog snapshots only.
- Do not implement real store integration, raw store scraping, production
  Hermes plugin/tools, Telegram UX, model arithmetic, or production model
  dependency.
- Do not read or display secrets.

## Required context

Read first:

- `docs/briefs/m8-agent-brief.md`
- files directly affected by the task

Read full context only when changing ADRs, stage plans, component boundaries,
or when the brief is insufficient:

- `AGENTS.md`
- `docs/concept.md`
- `docs/architecture.md`
- `docs/domain-rules.md`
- `docs/implementation-plan.md`
- `docs/Stage 8.md`
- `docs/experiments/m6b-recipes-and-replacements.md`
- `docs/decisions/ADR-0005-safe-commit-and-persistence.md`
- `docs/decisions/ADR-0009-recipes-and-replacements.md`
- `docs/decisions/open-questions.md`

## Work cycle

1. Restate the single task, expected files, acceptance criteria, and checks.
2. Inspect current implementation before editing.
3. If normalized ingredient taxonomy, unit dimensions, pantry/leftovers,
   product matching, package rounding, prices/availability, checklist
   disambiguation, or versioning policy is blocking, ask the user during that
   step.
4. If a non-blocking uncertainty remains, record it in
   `docs/decisions/open-questions.md`.
5. Prefer existing project toolchain and patterns.
6. Add the smallest testable change.
7. Run targeted unit/contract/property tests first.
8. Run M7 eval/golden checks when the task changes shopping calculation,
   catalog matching, checklist behavior, or replacement diff behavior.
9. Run `git diff --check`.
10. Report changed files, commands, passed checks, skipped checks,
    assumptions, and follow-up tasks.

## Message economy

- For small scoped tasks, send one short update before edits and one final
  report.
- Do not reread every source document for routine fixture, conversion,
  property-test, mock-catalog, or checklist changes when the brief and affected
  files are sufficient.
- For documentation-only or skill-only tasks, do not run the full application
  suite unless explicitly requested.

## Guardrails

- Shopping-list arithmetic is code-owned and deterministic.
- Unknown units or dimensions produce controlled errors.
- Model/fake output must never calculate packages, prices, or checklist state.
- Shopping list versions must link to menu version and catalog snapshot.
- Checklist mutation requires exact item identity or disambiguation.
- Keep real store integration and raw HTML out of M7.
- Keep Domain Core independent from Hermes, Telegram, ORM, HTTP clients, and
  model SDKs.
- Keep secrets out of Git, logs, eval artifacts, reports, and diffs.
```

Критерий завершения: skill валиден локально; проверочный prompt не требуется,
если local validation прошла.

### Шаг 2. Зафиксировать shopping-list and mock-catalog strategy

Цель: не смешать deterministic shopping calculation, catalog snapshots, real
store integration и Hermes/Telegram в одну непроверяемую реализацию.

Создать:

```text
docs/decisions/ADR-0010-shopping-list-and-mock-catalog.md
```

ADR должен зафиксировать:

- source policy: confirmed menu and recipe versions only;
- normalized ingredient and unit model;
- supported unit dimensions and conversion policy;
- rounding and package calculation policy;
- pantry/leftovers policy for M7;
- `StoreCatalogProvider` contract;
- mock catalog snapshot shape and versioning;
- product matching policy: fixed or confirmable;
- shopping list versioning and link to menu/catalog snapshot;
- checklist update and disambiguation policy;
- replacement impact/diff policy;
- what remains out of M7.

Если нужны product decisions по ingredient taxonomy, units, pantry,
product matching, package rounding, price/availability or checklist UX, агент
задает вопрос пользователю. Если выбор не блокирует deterministic minimal
slice, агент фиксирует technical assumption и open question.

Критерий завершения:

- ADR-0010 принят;
- no real store/Hermes/Telegram decisions hidden inside shopping calculation;
- M7 можно проверить без Hermes, Telegram, external model provider and live
  store access;
- unresolved product/provider decisions перенесены в
  `docs/decisions/open-questions.md`.

### Шаг 3. Определить normalized ingredient and unit contracts

Цель: создать проверяемую основу расчетов до shopping-list implementation.

Добавить или уточнить:

- normalized ingredient identifier;
- quantity and unit representation;
- supported dimensions;
- unit conversion table;
- valid/invalid fixtures;
- stable errors for unknown unit and unsupported dimension.

Критерий завершения:

- every changed contract has `schema_version`;
- valid fixtures pass;
- invalid fixtures return stable errors;
- conversion does not guess unknown units.

### Шаг 4. Реализовать deterministic scaling, conversion and merge

Цель: вся арифметика ингредиентов должна быть code-owned and testable.

Реализовать:

- scale ingredients by recipe portions;
- convert only supported units within same dimension;
- merge same normalized ingredients;
- reject incompatible dimensions;
- deterministic rounding accepted by ADR-0010.

Критерий завершения:

- unit tests cover happy and failure paths;
- property tests cover associativity/order stability where applicable;
- same inputs produce same normalized ingredient totals.

### Шаг 5. Реализовать StoreCatalogProvider and mock snapshot

Цель: проверить catalog boundary без реального магазина.

Добавить:

- `StoreCatalogProvider` interface;
- `MockStoreCatalogProvider`;
- reviewed catalog snapshot fixture;
- snapshot id/version;
- normalized product cards without raw HTML or external instructions.

Критерий завершения:

- provider returns deterministic results for same snapshot;
- no network or live store access required;
- raw external data is not treated as trusted instructions.

### Шаг 6. Реализовать M7 product matching policy

Цель: matching должен быть fixed or confirmable, а не guessed by model.

Реализовать policy from ADR-0010:

- fixed mapping for reviewed fixtures; or
- confirmable candidate list with controlled unresolved state.

Критерий завершения:

- ambiguous/unmatched ingredient produces controlled error or confirmation
  requirement;
- model does not choose products;
- matching result links ingredient to catalog snapshot item.

### Шаг 7. Реализовать package and cost calculation

Цель: упаковки, количество и стоимость рассчитываются кодом.

Реализовать:

- package count calculation;
- supported rounding rules;
- cost calculation if ADR-0010 includes snapshot prices;
- controlled behavior if price is absent/out of M7.

Критерий завершения:

- property tests cover rounding and package counts;
- arithmetic does not call model/provider;
- unknown package shape returns controlled error.

### Шаг 8. Создать shopping list version

Цель: shopping list должен быть воспроизводимо связан с источниками.

Shopping list version должен включать:

- `schema_version`;
- user id;
- source menu version;
- recipe version references;
- catalog snapshot id;
- generated shopping items;
- calculation metadata without secrets/private data.

Критерий завершения:

- same source versions and snapshot create same list;
- changed recipe/menu/catalog snapshot changes relevant version/hash;
- failure leaves confirmed menu/recipe state unchanged.

### Шаг 9. Реализовать predictable diff after one-slot replacement

Цель: замена блюда должна давать предсказуемый diff списка покупок.

Добавить:

- recomputation from old and new menu/recipe versions;
- item-level added/removed/changed quantities;
- stable ordering;
- no model arithmetic.

Критерий завершения:

- one-slot replacement produces deterministic shopping-list diff;
- unaffected ingredients/items remain unchanged by test;
- diff links to source menu/replacement references.

### Шаг 10. Реализовать precise checklist item updates

Цель: status changes must target exact shopping item identity.

Добавить:

- exact update by `shopping_item_id`;
- idempotent status update where existing patterns require it;
- controlled error for missing/stale item;
- audit metadata without secrets.

Критерий завершения:

- status update by id is test-covered;
- stale/missing item is rejected deterministically;
- update does not mutate unrelated items.

### Шаг 11. Добавить text disambiguation for checklist updates

Цель: свободный текст не должен менять checklist ambiguously.

Для text command like "молоко куплено":

- resolve exact item only if one clear match exists;
- require disambiguation if multiple matches exist;
- return controlled error/state if no match exists;
- do not rely on model confidence alone.

Критерий завершения:

- one-match text update covered;
- multiple-match disambiguation covered;
- no-match controlled error covered.

### Шаг 12. Добавить M7 eval/golden command

Цель: Gate M7 должен проверяться одной воспроизводимой командой.

Eval должен покрывать:

- normalized unit conversion;
- ingredient scaling/merge;
- mock catalog snapshot matching;
- package/cost calculation;
- shopping list version identity;
- replacement diff;
- checklist update and disambiguation.

Критерий завершения:

- command added to `scripts/dev.sh` if useful;
- report is deterministic;
- failures are machine-readable enough for debugging.

### Шаг 13. Заполнить M7 report and decision point

Цель: остановиться на Gate M7, а не перейти автоматически в Hermes plugin or
real store integration.

Создать:

```text
docs/experiments/m7-shopping-list-and-mock-catalog.md
```

Report должен содержать:

- цель;
- scope;
- contract/calculation/catalog decisions;
- matching/checklist decisions;
- commands run;
- property/eval metrics;
- what was intentionally not implemented;
- Gate M7 result;
- decision point: prices and availability in MVP;
- decisions before Hermes plugin and real store integration.

Критерий завершения:

- Gate M7 checklist заполнен;
- remaining assumptions listed;
- relevant questions copied to `docs/decisions/open-questions.md`;
- в отчете явно сказано: не переходить к Hermes plugin, Telegram UX or real
  store integration без отдельного задания.

## 7. Gate M7 checklist

Заполнить в `docs/experiments/m7-shopping-list-and-mock-catalog.md`:

```markdown
## Gate M7 Checklist

[ ] M7 Codex skill exists and was used for implementation tasks.
[ ] M7 brief exists and was used for routine tasks.
[ ] ADR-0010 or equivalent decision note fixes shopping-list strategy.
[ ] Normalized ingredient and unit contracts have schema_version and fixtures.
[ ] Unknown unit returns controlled error, not guess.
[ ] Unsupported dimension returns controlled error, not guess.
[ ] Ingredient scaling and merging are deterministic.
[ ] Unit/package/rounding property tests pass.
[ ] MockStoreCatalogProvider returns deterministic snapshot data.
[ ] Product matching is fixed or explicitly confirmable.
[ ] Shopping list version links to menu version and catalog snapshot.
[ ] Same inputs create the same shopping list.
[ ] Shopping-list arithmetic is not performed by a model.
[ ] One-slot replacement creates predictable shopping-list diff.
[ ] Checklist item status changes only by exact item id or disambiguated match.
[ ] Ambiguous text checklist update requires disambiguation.
[ ] Failure leaves confirmed menu, recipes and shopping list state unchanged.
[ ] Domain Core has no Hermes, Telegram, ORM, HTTP client or model SDK imports.
[ ] No real store integration, raw store HTML, production Hermes plugin,
    Telegram UX, or production model dependency added.
[ ] `scripts/dev.sh test` passed or deviation recorded.
[ ] `scripts/dev.sh lint` passed or deviation recorded.
[ ] `scripts/dev.sh typecheck` passed or deviation recorded.
[ ] `scripts/dev.sh smoke` passed or deviation recorded.
[ ] M7 golden/eval command passed or skipped with reason.
[ ] `git diff --check` passed.
```

## 8. Decision Point After M7

Заполнить после Gate M7:

```markdown
## Decision Point: Prices And Availability

### Нужны ли цены в MVP?

- [ответ]

### Нужно ли наличие товара в MVP?

- [ответ]

### Достаточен ли mock catalog для Hermes plugin stage?

- [ответ]

### Что должно остаться out of scope до real store integration?

- [ответ]
```

## 9. Sequence of tasks for Codex

Использовать по одному шагу за запрос. Для каждого шага:

1. Прочитать active M7 skill and `docs/briefs/m8-agent-brief.md`.
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
