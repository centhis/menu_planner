# Этап 0. Подготовка среды, Codex и исследование контейнера Hermes

## 1. Цель этапа 0

Этап 0 должен дать пять результатов:

1. Подготовленная VM для разработки.
    
2. Настроенный Codex в VS Code Remote-SSH.
    
3. Репозиторий с правилами, skills и минимальным MCP.
    
4. Воспроизводимый запуск готового контейнера Hermes через Docker Compose.
    
5. Проверенные фактические возможности Hermes:
    
    - plugins;
        
    - tools;
        
    - hooks;
        
    - toolsets;
        
    - skills;
        
    - sessions;
        
    - Telegram Gateway;
        
    - bind mounts;
        
    - сохранение состояния.
        

На этом этапе ещё не реализуются:

- Domain Core;
    
- профиль пользователя;
    
- меню;
    
- рецепты;
    
- список покупок;
    
- PostgreSQL;
    
- бизнес-workflow;
    
- production Menu Planner Plugin.
    

Этап 0 отвечает только на вопрос:

> Можно ли использовать выбранный готовый контейнер Hermes как стабильную основу приложения, подключая весь прикладной код декларативно через Docker Compose?

---

# Шаг 1. Проверить подключение VS Code к VM

## Цель

Убедиться, что VS Code, терминал, Codex и файлы проекта действительно работают на VM, а не на локальном компьютере.

VS Code Remote-SSH устанавливает VS Code Server на удалённой машине, а большинство workspace-расширений выполняется на SSH-хосте. Терминал, открытый в удалённом окне, также работает на VM.

## Действия

### 1.1. Подключиться к VM

В локальном VS Code:

1. Открыть Command Palette.
    
2. Выполнить:
    

```text
Remote-SSH: Connect to Host...
```

3. Выбрать вашу VM.
    
4. Убедиться, что в левом нижнем углу отображается:
    

```text
SSH: <имя VM>
```

### 1.2. Открыть терминал VS Code

В удалённом окне:

```text
Terminal → New Terminal
```

Выполнить:

```bash
whoami
hostname
pwd
uname -a
cat /etc/os-release
uname -m
```

Ожидается:

- `Ubuntu 24.04`;
    
- имя вашей VM;
    
- удалённый пользователь;
    
- архитектура, обычно `x86_64` или `aarch64`.
    

### 1.3. Создать рабочий каталог

```bash
mkdir -p ~/projects
cd ~/projects
pwd
```

Рабочий путь далее:

```text
~/projects/menu-planner
```

## Критерий завершения

- VS Code показывает подключение по SSH.
    
- Терминал выполняет команды на VM.
    
- Открываемые файлы находятся на VM.
    
- Локальная файловая система компьютера не используется как рабочая директория проекта.
    

---

# Шаг 2. Проверить базовые инструменты VM

## Цель

Убедиться, что на VM есть минимальный набор инструментов разработки.

## 2.1. Проверить установленные программы

```bash
git --version
curl --version
jq --version
rg --version
docker --version
docker compose version
```

## 2.2. Установить отсутствующие общие инструменты

Эту команду выполняет пользователь, не Codex:

```bash
sudo apt update
sudo apt install -y \
  git \
  curl \
  ca-certificates \
  jq \
  ripgrep
```

## 2.3. Проверить Docker

```bash
docker version
docker compose version
docker info
```

Ubuntu 24.04 поддерживается актуальным Docker Engine. Официальная установка включает Docker Engine, CLI, containerd и Compose plugin.

Если Docker уже работает, ничего переустанавливать не нужно.

## 2.4. Проверить доступ пользователя к Docker

```bash
docker ps
```

Если команда работает без `sudo`, переходите дальше.

Если появляется ошибка доступа к Docker socket, сначала проверить:

```bash
groups
ls -l /var/run/docker.sock
```

Не поручать Codex самостоятельно изменять группы пользователей или права Docker.

## Критерий завершения

Работают команды:

```bash
git --version
docker --version
docker compose version
docker ps
```

---

# Шаг 3. Создать репозиторий проекта

## Цель

Создать одну корневую директорию, которая станет единственным рабочим пространством Codex.

## 3.1. Создать структуру

```bash
cd ~/projects

mkdir -p menu-planner
cd menu-planner

git init -b main

mkdir -p \
  .codex/rules \
  .agents/skills/hermes-container-spike \
  .agents/skills/verified-small-change \
  .vscode \
  config/hermes \
  plugins/menu-planner \
  plugins/menu-planner-probe \
  skills/hermes \
  src/menu_planner \
  tests/capability \
  scripts \
  docs/decisions \
  docs/experiments \
  docs/runbooks \
  runtime
```

## 3.2. Назначение каталогов

```text
.codex/
    Конфигурация и command rules Codex.

.agents/skills/
    Skills самого Codex-разработчика.

config/hermes/
    Конфигурация Hermes, которая позже монтируется в контейнер.

plugins/menu-planner/
    Production Menu Planner Plugin.

plugins/menu-planner-probe/
    Временный plugin для capability spike.

skills/hermes/
    Skills, которые будет использовать Hermes.
    Это не Codex skills.

src/menu_planner/
    Независимый прикладной код и Domain Core.

tests/capability/
    Проверки возможностей контейнера Hermes.

runtime/
    Локальное изменяемое состояние.
    Не коммитится в Git.
```

Важно не путать:

```text
.agents/skills/
→ skills Codex для разработки

skills/hermes/
→ skills runtime Hermes
```

Codex обнаруживает repository skills в `.agents/skills` от текущей директории до корня Git-репозитория.

## 3.3. Создать `.gitignore`

```bash
cat > .gitignore <<'EOF'
# Secrets
.env
.env.*
!.env.example
*.pem
*.key
*.token

# Runtime state
runtime/
data/
logs/
*.log

# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/

# IDE local state
.vscode/settings.json
.idea/

# OS
.DS_Store
Thumbs.db

# Backups
*.bak
*.backup
*.tmp
EOF
```

## 3.4. Поместить документацию

Скопировать в `docs/`:

```text
concept.md
architecture.md
domain-rules.md
implementation-plan.md
```

Итог:

```text
docs/
├── concept.md
├── architecture.md
├── domain-rules.md
├── implementation-plan.md
├── decisions/
├── experiments/
└── runbooks/
```

## 3.5. Создать начальный `README.md`

```bash
cat > README.md <<'EOF'
# Menu Planner for Hermes

Персональный планировщик меню на базе Hermes Agent.

## Runtime model

Hermes запускается из готового Docker-образа через Docker Compose.

Проект не использует собственный Dockerfile для Hermes.

Прикладные компоненты подключаются через bind mounts:

- configuration;
- Menu Planner Plugin;
- Hermes skills;
- application source code.

Изменяемое состояние хранится в named volumes или внешней базе данных.

Ручные изменения внутри работающего контейнера запрещены.

## Current stage

Stage 0: environment setup and Hermes capability spike.
EOF
```

## 3.6. Первый commit

```bash
git add .
git commit -m "chore: initialize menu planner repository"
```

## Критерий завершения

```bash
git status
```

показывает чистое рабочее дерево.

---

# Шаг 4. Установить Codex в удалённое окружение VS Code

## Цель

Codex должен работать с файлами и терминалом VM, а не локального компьютера.

## 4.1. Установить расширение

В окне VS Code, уже подключённом к VM:

1. Открыть Extensions.
    
2. Найти официальное расширение Codex от OpenAI.
    
3. Нажать:
    

```text
Install in SSH: <имя VM>
```

4. После установки перезапустить удалённое окно:
    

```text
Developer: Reload Window
```

В Remote-SSH большинство workspace-расширений устанавливается и выполняется на удалённом SSH-хосте.

Официальное расширение Codex поддерживает VS Code на Linux и предоставляет чтение файлов, редактирование и запуск команд непосредственно из IDE.

## 4.2. Проверить расположение расширения

В Extensions должны быть отдельные группы:

```text
Local - Installed
SSH: <имя VM> - Installed
```

Codex должен отображаться в группе SSH-host.

## 4.3. Открыть проект

В удалённом VS Code:

```text
File → Open Folder
```

Открыть:

```text
/home/<user>/projects/menu-planner
```

## Критерий завершения

- Codex появляется в sidebar VS Code.
    
- Проект открыт с VM.
    
- Codex видит файлы репозитория.
    

---

# Шаг 5. Установить Codex CLI на VM

## Цель

IDE остаётся основным интерфейсом, но CLI нужен для:

- проверки MCP;
    
- проверки command rules;
    
- диагностики конфигурации;
    
- проверки skills;
    
- запуска коротких агентных тестов.
    

Codex CLI и IDE extension используют общие конфигурационные слои.

## 5.1. Скачать установщик

Не передавать скачанный скрипт напрямую в shell без просмотра.

```bash
cd /tmp

curl -fsSL \
  https://chatgpt.com/codex/install.sh \
  -o codex-install.sh

less codex-install.sh
```

После просмотра:

```bash
sh /tmp/codex-install.sh
```

Официальный standalone installer предназначен для macOS и Linux.

## 5.2. Проверить CLI

```bash
command -v codex
codex --version
codex --help
```

## 5.3. Перезапустить terminal при необходимости

```bash
exec "$SHELL" -l
```

Затем:

```bash
codex --version
```

## Критерий завершения

Команда:

```bash
codex --version
```

работает в терминале Remote-SSH.

---

# Шаг 6. Авторизовать Codex на VM

## Цель

Создать авторизацию именно для удалённого пользователя VM.

## Предпочтительный способ

```bash
codex login --device-auth
```

Codex покажет адрес и одноразовый код.

1. Открыть адрес в локальном браузере.
    
2. Войти в ChatGPT.
    
3. Ввести код.
    
4. Вернуться в терминал VM.
    

Device-code authentication предназначена в том числе для удалённых и headless-сред.

## Проверка

```bash
ls -la ~/.codex
```

Файл авторизации, если он существует:

```text
~/.codex/auth.json
```

считается секретом. Его нельзя:

- копировать в репозиторий;
    
- показывать Codex в prompt;
    
- помещать в `.env`;
    
- отправлять в сообщения;
    
- коммитить в Git.
    

Официальная документация прямо указывает, что `auth.json` следует обрабатывать как пароль.

## Критерий завершения

Codex IDE и CLI не требуют повторной авторизации при каждом запуске.

---

# Шаг 7. Настроить базовые permissions Codex

## Цель

Codex может изменять только текущий репозиторий и обязан запрашивать подтверждение перед выходом за его границы.

## 7.1. Создать пользовательскую конфигурацию

```bash
mkdir -p ~/.codex

cat > ~/.codex/config.toml <<'EOF'
approval_policy = "on-request"
sandbox_mode = "workspace-write"
EOF
```

`workspace-write` разрешает Codex работать внутри активного workspace, а `on-request` требует подтверждения для действий, выходящих за обычные границы sandbox.

На этапе 0 не использовать:

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
```

## 7.2. Не включать общий сетевой доступ

Не добавлять:

```toml
[sandbox_workspace_write]
network_access = true
```

Codex должен запрашивать разрешение, когда команде действительно нужен интернет.

## 7.3. Проверить из IDE

В окне Codex выбрать режим, соответствующий:

```text
workspace write
approval on request
```

Не использовать `Full Access`.

## Критерий завершения

Codex:

- может читать и изменять `~/projects/menu-planner`;
    
- не может молча изменять файлы вне проекта;
    
- запрашивает подтверждение для административных операций.
    

---

# Шаг 8. Настроить MCP

## Цель

Добавить только один MCP, реально необходимый на начальном этапе.

## 8.1. Добавить OpenAI Developer Docs MCP

```bash
codex mcp add openaiDeveloperDocs \
  --url https://developers.openai.com/mcp
```

Проверить:

```bash
codex mcp list
```

OpenAI Developer Docs MCP предоставляет read-only поиск и чтение официальной документации OpenAI. CLI и IDE используют общую MCP-конфигурацию.

## 8.2. Проверить конфигурацию

```bash
grep -A5 -B2 \
  'openaiDeveloperDocs' \
  ~/.codex/config.toml
```

Ожидаемая секция:

```toml
[mcp_servers.openaiDeveloperDocs]
url = "https://developers.openai.com/mcp"
```

## 8.3. Не добавлять лишние MCP

На этапе 0 не нужны:

- filesystem MCP;
    
- shell MCP;
    
- Docker MCP;
    
- PostgreSQL MCP;
    
- GitHub write-enabled MCP;
    
- browser automation MCP;
    
- Telegram MCP.
    

Причина:

- Codex уже имеет workspace filesystem и shell через sandbox;
    
- Docker используется через обычный CLI с approval;
    
- базы данных пока нет;
    
- GitHub-интеграция пока не нужна;
    
- лишние MCP увеличивают число полномочий и вариантов недетерминированного поведения.
    

## Критерий завершения

```bash
codex mcp list
```

показывает только необходимый сервер:

```text
openaiDeveloperDocs
```

---

# Шаг 9. Создать глобальные инструкции Codex

## Цель

Задать общие правила работы Codex на VM.

Codex загружает `~/.codex/AGENTS.md`, а затем добавляет project-level `AGENTS.md`. Более близкие к рабочей директории инструкции имеют более высокий приоритет.

## Создать `~/.codex/AGENTS.md`

```bash
cat > ~/.codex/AGENTS.md <<'EOF'
# Global Codex working agreements

## Communication

- Перед изменениями кратко сформулируй цель и ожидаемый результат.
- Для сложных задач сначала составь план.
- Не скрывай ошибки команд, тестов или неопределённости.
- Не утверждай, что проверка пройдена, если команда не запускалась.

## Scope

- Работай только внутри открытого Git workspace.
- Не изменяй файлы вне workspace без отдельного подтверждения.
- Не изменяй системную конфигурацию VM.
- Не устанавливай системные пакеты без явного задания.
- Не изменяй настройки Docker daemon.

## Changes

- Одна задача должна давать одно проверяемое изменение.
- Избегай несвязанных рефакторингов.
- Не добавляй production dependencies без явного согласования.
- Перед завершением покажи изменённые файлы и результаты проверок.
- Не создавай Git commit, если это явно не запрошено.

## Secrets

- Не открывай и не отображай содержимое auth.json, .env, токенов и credentials.
- Не включай секреты в логи, отчёты, diff или commits.
EOF
```

## Критерий завершения

После перезапуска Codex спросить:

```text
Перечисли глобальные инструкции, которые ты загрузил.
Ничего не изменяй.
```

Codex должен пересказать правила из `~/.codex/AGENTS.md`.

---

# Шаг 10. Создать проектный `AGENTS.md`

## Цель

Зафиксировать архитектурные границы проекта так, чтобы Codex не возвращался к Dockerfile, кастомной сборке Hermes или изменениям внутри контейнера.

## Создать файл

```bash
cat > AGENTS.md <<'EOF'
# Menu Planner development instructions

## Sources of truth

Перед работой изучи относящиеся к задаче разделы:

- docs/concept.md
- docs/architecture.md
- docs/domain-rules.md
- docs/implementation-plan.md

Не меняй эти документы без прямого задания.

Не придумывай значения для полей, помеченных:
- [ТРЕБУЕТ РЕШЕНИЯ]
- [ТРЕБУЕТ РЕШЕНИЯ ИЛИ ПРОВЕРКИ]

Неизвестные факты фиксируй в:
docs/decisions/open-questions.md

## Deployment boundary

Hermes запускается только из готового Docker image через Docker Compose.

Запрещено:

- создавать Dockerfile для Hermes;
- использовать docker build;
- использовать docker compose build;
- создавать кастомный Hermes image;
- использовать docker commit;
- использовать docker cp для установки кода;
- устанавливать пакеты внутри Hermes container;
- редактировать файлы внутри работающего контейнера;
- создавать невоспроизводимое состояние через docker exec.

Разрешено:

- редактировать файлы на host VM;
- подключать файлы через bind mounts;
- использовать read-only bind mounts для кода и конфигурации;
- использовать named volumes для изменяемого runtime state;
- использовать docker compose exec только для диагностики;
- перезапускать или пересоздавать контейнер после изменения host-файлов.

## Component boundary

Hermes:
- dialog runtime;
- sessions;
- model providers;
- agent loop;
- skills;
- tools;
- hooks;
- toolsets;
- Telegram Gateway.

Menu Planner Domain Core:
- workflows;
- permissions;
- business rules;
- validation;
- calculations;
- versioning;
- confirmation;
- commit;
- idempotency.

Domain Core не импортирует Hermes или Telegram.

Модель не изменяет подтверждённое состояние напрямую.

## Development workflow

Для каждой задачи:

1. Прочитай относящиеся документы.
2. Сформулируй acceptance criteria.
3. Проверь фактическое состояние репозитория.
4. Сделай минимальное изменение.
5. Запусти релевантные проверки.
6. Выполни git diff --check.
7. Покажи diff summary.
8. Перечисли непроверенные предположения.

Не выполняй соседние задачи самостоятельно.

## Stage 0 restrictions

На этапе 0 разрешены только:

- подготовка среды;
- настройка Codex;
- Docker Compose;
- исследование готового Hermes image;
- bind mounts;
- capability probe;
- техническая документация;
- тесты capability spike.

Не реализуй:

- профиль;
- меню;
- рецепты;
- shopping list;
- PostgreSQL;
- production business workflows.

## Documentation lookup

Используй OpenAI Developer Docs MCP для вопросов о Codex,
OpenAI API и MCP OpenAI без отдельного напоминания.

Для Hermes не придумывай API по аналогии.
Сначала проверяй фактическую версию, CLI help, документацию
и установленный код внутри готового image.

## Completion report

В конце задачи сообщи:

- что изменено;
- какие команды запускались;
- какие проверки прошли;
- какие проверки не запускались;
- какие решения ещё не приняты.
EOF
```

Главные архитектурные ограничения отражают уже принятые документы: Hermes является runtime, а Domain Core остаётся источником бизнес-правил и commit.

## Критерий завершения

В Codex открыть новую сессию и написать:

```text
Прочитай инструкции проекта.

Ответь:
1. Можно ли создавать Dockerfile для Hermes?
2. Можно ли устанавливать Python packages внутри Hermes container?
3. Где должен находиться изменяемый runtime state?
4. Кто принимает окончательное решение о commit?

Ничего не изменяй.
```

Правильные ответы:

```text
1. Нет.
2. Нет.
3. В named volumes или внешнем хранилище.
4. Детерминированный Domain Core.
```

---

# Шаг 11. Настроить Codex command rules

## Цель

Не позволить Codex случайно применить запрещённую стратегию сборки или выполнить разрушительные Git/Docker-команды.

Codex rules управляют командами, запрашивающими выполнение вне sandbox. Формат rules экспериментальный, поэтому его нельзя считать единственной защитой.

## Создать `.codex/rules/project.rules`

```bash
cat > .codex/rules/project.rules <<'EOF'
# Hermes image must never be built by this project.

prefix_rule(
    pattern = ["docker", "build"],
    decision = "forbidden",
    justification = "Do not build a custom Hermes image. Use the ready image from compose.",
    match = [
        "docker build .",
        "docker build -t menu-hermes .",
    ],
)

prefix_rule(
    pattern = ["docker", "compose", "build"],
    decision = "forbidden",
    justification = "This project uses no Dockerfile for Hermes. Use docker compose pull/up.",
    match = [
        "docker compose build",
        "docker compose build hermes",
    ],
)

prefix_rule(
    pattern = ["docker", "cp"],
    decision = "forbidden",
    justification = "Mount files through Docker Compose instead of copying into containers.",
    match = [
        "docker cp plugin.py hermes:/app/plugin.py",
    ],
)

prefix_rule(
    pattern = ["docker", "commit"],
    decision = "forbidden",
    justification = "Never create images from manually changed containers.",
    match = [
        "docker commit hermes custom-hermes",
    ],
)

# Container lifecycle changes require explicit user approval.

prefix_rule(
    pattern = ["docker", "compose", "pull"],
    decision = "prompt",
    justification = "Pulling may change the local image version.",
)

prefix_rule(
    pattern = ["docker", "compose", "up"],
    decision = "prompt",
    justification = "Starting or recreating services changes runtime state.",
)

prefix_rule(
    pattern = ["docker", "compose", "down"],
    decision = "prompt",
    justification = "Stopping services may interrupt the active Hermes runtime.",
)

prefix_rule(
    pattern = ["docker", "compose", "restart"],
    decision = "prompt",
    justification = "Restarting Hermes interrupts active sessions.",
)

prefix_rule(
    pattern = ["docker", "compose", "exec"],
    decision = "prompt",
    justification = "Exec is allowed only for diagnostic commands.",
)

prefix_rule(
    pattern = ["docker", "compose", "run"],
    decision = "prompt",
    justification = "One-off containers may create runtime state.",
)

# Destructive Git actions.

prefix_rule(
    pattern = ["git", "reset", "--hard"],
    decision = "forbidden",
    justification = "Do not discard uncommitted changes. Use git diff and ask the user.",
)

prefix_rule(
    pattern = ["git", "clean"],
    decision = "forbidden",
    justification = "Do not delete untracked project files.",
)

prefix_rule(
    pattern = ["git", "push", "--force"],
    decision = "forbidden",
    justification = "Do not rewrite remote history.",
)

# Machine administration always requires approval.

prefix_rule(
    pattern = ["sudo"],
    decision = "prompt",
    justification = "System-level changes require explicit user approval.",
)

prefix_rule(
    pattern = ["apt"],
    decision = "prompt",
    justification = "Package installation changes the VM.",
)

prefix_rule(
    pattern = ["apt-get"],
    decision = "prompt",
    justification = "Package installation changes the VM.",
)
EOF
```

## Проверить rules

```bash
codex execpolicy check --pretty \
  --rules .codex/rules/project.rules \
  -- docker compose build hermes
```

Ожидается:

```text
forbidden
```

Проверить:

```bash
codex execpolicy check --pretty \
  --rules .codex/rules/project.rules \
  -- docker compose restart hermes
```

Ожидается:

```text
prompt
```

Проверить:

```bash
codex execpolicy check --pretty \
  --rules .codex/rules/project.rules \
  -- git reset --hard HEAD
```

Ожидается:

```text
forbidden
```

Codex предоставляет `execpolicy check` именно для тестирования rules до их применения.

## Критерий завершения

Все три теста дают ожидаемое решение.

---

# Шаг 12. Создать Codex skill `verified-small-change`

## Цель

Научить Codex выполнять одну небольшую задачу за один цикл, а не переписывать сразу весь проект.

Skills состоят из каталога с обязательным `SKILL.md`; Codex может активировать их явно или автоматически по description.

## Создать файл

```bash
cat > .agents/skills/verified-small-change/SKILL.md <<'EOF'
---
name: verified-small-change
description: Use for implementing one small, clearly bounded Menu Planner task with acceptance criteria, tests, diff review, and no unrelated refactoring.
---

# Verified small change workflow

1. Read AGENTS.md and relevant architecture documents.

2. Restate:
   - task goal;
   - files expected to change;
   - acceptance criteria;
   - commands expected to verify the result.

3. Inspect the current implementation before editing.

4. Do not change files outside the declared task scope unless required.
   If additional work is discovered, record it as a follow-up instead.

5. Make the smallest coherent change.

6. Run the narrowest relevant checks first.

7. Run:
   git diff --check

8. Review:
   git status --short
   git diff --stat
   git diff

9. Do not commit unless explicitly instructed.

10. Report:
    - files changed;
    - checks passed;
    - checks not run;
    - assumptions;
    - follow-up tasks.
EOF
```

## Проверка

В Codex:

```text
$verified-small-change

Ничего не меняй.
Опиши, как ты будешь выполнять небольшую задачу в этом проекте.
```

## Критерий завершения

Codex описывает цикл:

```text
контекст → acceptance criteria → минимальный diff →
проверки → review → отчёт
```

---

# Шаг 13. Создать Codex skill `hermes-container-spike`

## Цель

Зафиксировать специальный workflow исследования Hermes без Dockerfile и без изменений внутри контейнера.

## Создать файл

```bash
cat > .agents/skills/hermes-container-spike/SKILL.md <<'EOF'
---
name: hermes-container-spike
description: Use when inspecting, configuring, mounting files into, or testing the ready-made Hermes Docker image during stage 0. Never build or mutate the image.
---

# Hermes container capability spike

## Hard constraints

- Use the existing ready-made Hermes image.
- Do not create a Dockerfile.
- Do not run docker build or docker compose build.
- Do not use docker cp.
- Do not use docker commit.
- Do not install packages inside the container.
- Do not edit files inside the container.
- Do not create production code based on guessed Hermes APIs.

## Allowed mechanisms

- docker compose pull;
- docker compose config;
- docker compose ps;
- docker compose logs;
- docker image inspect;
- docker container inspect;
- read-only diagnostic docker compose exec;
- bind mounts declared in compose;
- named volumes declared in compose;
- editing host files;
- restarting or recreating the service after approval.

## Investigation sequence

1. Locate the active compose project.
2. Record the image name, tag and digest.
3. Record container user, HOME, working directory and command.
4. Run Hermes version and help commands.
5. Discover actual configuration, plugin, skill and state paths.
6. Classify each path as:
   - read-only project input;
   - read-write runtime state;
   - secret;
   - unknown.
7. Test a neutral read-only bind mount.
8. Test plugin discovery using a host-mounted probe.
9. Test tools, hooks, toolsets and session identifiers.
10. Record evidence for every conclusion.

## Evidence requirements

Every finding must include at least one of:

- exact command;
- relevant output excerpt without secrets;
- file path inside the image;
- Hermes help output;
- source-code location;
- reproducible test.

Never mark an item PASS based only on documentation.

## Output

Update:

- docs/experiments/hermes-container-baseline.md
- docs/experiments/hermes-capability-spike.md
- docs/decisions/open-questions.md

Report unknown capabilities rather than inventing an adapter.
EOF
```

## Проверка

В Codex:

```text
$hermes-container-spike

Перечисли запрещённые и разрешённые способы работы с Hermes container.
Ничего не запускай.
```

## Критерий завершения

Codex явно говорит:

- Dockerfile запрещён;
    
- image не изменяется;
    
- bind mounts разрешены;
    
- диагностика выполняется только на чтение;
    
- все выводы подтверждаются экспериментами.
    

---

# Шаг 14. Проверить полную настройку Codex

## Цель

Убедиться, что Codex видит instructions, MCP, rules и skills.

После изменения `AGENTS.md`, rules или skills открыть новую сессию Codex. `AGENTS.md` формирует instruction chain при старте, а изменения skills обычно обнаруживаются автоматически; при проблемах Codex следует перезапустить.

## Проверка CLI

```bash
codex --version
codex mcp list
```

## Проверка rules

```bash
codex execpolicy check --pretty \
  --rules .codex/rules/project.rules \
  -- docker build .
```

## Проверка в IDE

Отправить Codex:

```text
Ничего не изменяй.

Покажи:
1. какие AGENTS.md ты загрузил;
2. какие MCP доступны;
3. какие project skills доступны;
4. какой sandbox используется;
5. требует ли docker compose restart подтверждения;
6. разрешён ли docker compose build.
```

Ожидается:

```text
MCP:
- openaiDeveloperDocs

Skills:
- verified-small-change
- hermes-container-spike

Sandbox:
- workspace-write

docker compose restart:
- prompt

docker compose build:
- forbidden
```

## Зафиксировать результат

Создать:

```bash
cat > docs/experiments/codex-baseline.md <<'EOF'
# Codex baseline

## Environment

VM:
Operating system:
VS Code Remote-SSH:
Codex extension version:
Codex CLI version:

## Authentication

Method:
Result:

## Sandbox

approval_policy:
sandbox_mode:

## MCP

- openaiDeveloperDocs

## Instructions

Global AGENTS:
Project AGENTS:

## Rules

docker build:
docker compose build:
docker compose restart:
git reset --hard:

## Skills

- verified-small-change
- hermes-container-spike

## Result

PASS / FAIL

## Open problems

EOF
```

---

# Шаг 15. Найти текущий Docker Compose Hermes

## Цель

Не создавать новую конфигурацию вслепую, а сначала найти и изучить уже используемый контейнер Hermes.

## 15.1. Посмотреть запущенные контейнеры

```bash
docker ps \
  --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

Найти контейнер Hermes.

## 15.2. Найти Compose metadata

Подставить имя контейнера:

```bash
HERMES_CONTAINER="<имя контейнера>"
```

Получить рабочую директорию Compose:

```bash
docker inspect "$HERMES_CONTAINER" \
  --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}'
```

Получить список Compose-файлов:

```bash
docker inspect "$HERMES_CONTAINER" \
  --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}'
```

Получить имя сервиса:

```bash
docker inspect "$HERMES_CONTAINER" \
  --format '{{ index .Config.Labels "com.docker.compose.service" }}'
```

## 15.3. Перейти в найденный каталог

```bash
cd <НАЙДЕННЫЙ_COMPOSE_WORKING_DIR>
ls -la
```

Не копировать автоматически содержимое `.env`.

## 15.4. Посмотреть безопасные сведения Compose

```bash
docker compose config --services
docker compose config --images
docker compose config --volumes
docker compose ps
```

Не выполнять:

```bash
docker compose config
```

с перенаправлением в Git без проверки, потому что итоговая конфигурация может содержать раскрытые environment values.

## 15.5. Зафиксировать образ

```bash
docker compose config --images
```

Затем:

```bash
HERMES_IMAGE="<образ из предыдущей команды>"

docker image inspect "$HERMES_IMAGE" \
  --format 'ID={{.Id}}'
```

```bash
docker image inspect "$HERMES_IMAGE" \
  --format 'DIGESTS={{json .RepoDigests}}'
```

## Критерий завершения

Известны:

```text
Compose working directory:
Compose file:
Compose service name:
Hermes image:
Hermes tag:
Hermes digest:
Container name:
```

---

# Шаг 16. Создать container baseline

## Цель

Зафиксировать фактическую среду контейнера без изменения его содержимого.

## 16.1. Запустить read-only диагностику

Из каталога Compose:

```bash
docker compose exec -T hermes sh -lc '
set -eu

echo "== identity =="
id

echo "== current directory =="
pwd

echo "== home =="
printf "%s\n" "$HOME"

echo "== hermes executable =="
command -v hermes || true

echo "== hermes version =="
hermes --version || true

echo "== hermes help =="
hermes --help || true
'
```

Если сервис называется не `hermes`, заменить имя на фактическое.

## 16.2. Получить mount information с хоста

```bash
docker inspect "$HERMES_CONTAINER" \
  --format '{{range .Mounts}}{{println .Type "|" .Source "|" .Destination "|" .RW}}{{end}}'
```

## 16.3. Получить image metadata без secrets

```bash
docker image inspect "$HERMES_IMAGE" \
  --format 'USER={{.Config.User}}'
```

```bash
docker image inspect "$HERMES_IMAGE" \
  --format 'WORKDIR={{.Config.WorkingDir}}'
```

```bash
docker image inspect "$HERMES_IMAGE" \
  --format 'ENTRYPOINT={{json .Config.Entrypoint}}'
```

```bash
docker image inspect "$HERMES_IMAGE" \
  --format 'CMD={{json .Config.Cmd}}'
```

Не выводить `.Config.Env` в отчёт.

## 16.4. Создать отчёт

```text
docs/experiments/hermes-container-baseline.md
```

Шаблон:

```markdown
# Hermes container baseline

## Compose

- working directory:
- compose file:
- service:
- container:
- image:
- tag:
- digest:

## Runtime

- user:
- uid:
- gid:
- HOME:
- working directory:
- entrypoint:
- command:
- Hermes executable:
- Hermes version:

## Current mounts

| Type | Host/volume | Container path | Writable |
|---|---|---|---|

## Unknowns

- configuration path:
- plugin path:
- skills path:
- session path:
- memory path:
- logs path:
```

## Критерий завершения

Отчёт содержит только фактически наблюдавшиеся значения и не содержит секретов.

---

# Шаг 17. Определить пути Hermes внутри контейнера

## Цель

Найти фактические директории:

- configuration;
    
- plugins;
    
- skills;
    
- sessions;
    
- memory;
    
- runtime state.
    

## 17.1. Сначала проверить CLI

```bash
docker compose exec -T hermes \
  hermes --help
```

Затем по доступным командам:

```bash
docker compose exec -T hermes \
  hermes plugins --help
```

```bash
docker compose exec -T hermes \
  hermes skills --help
```

```bash
docker compose exec -T hermes \
  hermes tools --help
```

```bash
docker compose exec -T hermes \
  hermes gateway --help
```

Не считать эти подкоманды существующими заранее. Каждую проверять через основной `--help`.

## 17.2. Исследовать HOME

```bash
docker compose exec -T hermes sh -lc '
find "$HOME" \
  -maxdepth 4 \
  -type d \
  \( \
    -name ".hermes" \
    -o -name "plugins" \
    -o -name "skills" \
    -o -name "sessions" \
    -o -name "memory" \
    -o -name "config" \
  \) \
  -print 2>/dev/null | sort
'
```

## 17.3. Искать код загрузки plugin

Сначала найти установленный package:

```bash
docker compose exec -T hermes sh -lc '
python3 - <<'"'"'PY'"'"'
import importlib.util

for name in ("hermes", "hermes_cli", "hermes_agent"):
    spec = importlib.util.find_spec(name)
    print(name, "=>", spec.origin if spec else "not found")
PY
'
```

Затем Codex должен исследовать найденный код только на чтение.

## 17.4. Заполнить карту mounts

Создать:

```text
docs/experiments/hermes-mount-map.md
```

Шаблон:

```markdown
# Hermes mount map

| Purpose | Host path | Container path | Mode | Evidence |
|---|---|---|---|---|
| Configuration | unknown | unknown | ro/rw | |
| Plugin | ./plugins/menu-planner | unknown | ro | |
| Probe plugin | ./plugins/menu-planner-probe | unknown | ro | |
| Hermes skills | ./skills/hermes | unknown | ro | |
| Domain code | ./src | unknown | ro | |
| Sessions | named volume | unknown | rw | |
| Memory | named volume | unknown | rw | |
| Logs | stdout/volume | unknown | rw | |
```

Нельзя заменять `unknown` догадкой.

## Критерий завершения

Для каждого найденного пути есть доказательство:

- CLI output;
    
- исходный код loader;
    
- существующий mount;
    
- успешный эксперимент.
    

---

# Шаг 18. Проверить нейтральный bind mount

## Цель

Доказать, что host-файл можно передать контейнеру read-only через Compose.

## 18.1. Создать probe

В репозитории:

```bash
cd ~/projects/menu-planner

mkdir -p tests/capability/mount-probe

cat > tests/capability/mount-probe/mounted.txt <<'EOF'
menu-planner-mount-probe
EOF
```

## 18.2. Добавить временный mount

В сервис Hermes в Compose добавить:

```yaml
volumes:
  - ./tests/capability/mount-probe:/mnt/menu-planner-probe:ro
```

Путь слева должен считаться относительно каталога Compose. Если Compose пока находится вне репозитория, сначала зафиксировать этот факт и использовать абсолютный путь только как временный эксперимент.

## 18.3. Пересоздать контейнер

Эту операцию пользователь подтверждает:

```bash
docker compose up -d --force-recreate hermes
```

## 18.4. Проверить чтение

```bash
docker compose exec -T hermes \
  cat /mnt/menu-planner-probe/mounted.txt
```

Ожидается:

```text
menu-planner-mount-probe
```

## 18.5. Проверить read-only

```bash
docker compose exec -T hermes sh -lc '
echo forbidden-write \
  > /mnt/menu-planner-probe/should-not-exist.txt
'
```

Ожидается ошибка:

```text
Read-only file system
```

или:

```text
Permission denied
```

Проверить на хосте:

```bash
test ! -e \
  tests/capability/mount-probe/should-not-exist.txt
```

## 18.6. Удалить временный mount

После фиксации результата убрать строку probe из Compose и пересоздать контейнер.

## Критерий завершения

- файл читается внутри контейнера;
    
- запись невозможна;
    
- после пересоздания контейнера результат воспроизводится.
    

---

# Шаг 19. Перенести Compose под управление проекта

## Цель

Сделать Compose частью репозитория, не создавая собственного image.

## Правило

В итоговом `compose.yaml` сервис Hermes должен использовать только:

```yaml
image: ...
```

и не должен содержать:

```yaml
build:
```

## Рекомендуемая структура

```text
menu-planner/
├── compose.yaml
├── .env.example
├── config/hermes/
├── plugins/
├── skills/hermes/
├── src/
└── runtime/
```

## Порядок переноса

1. Скопировать существующий Compose в репозиторий.
    
2. Удалить из копии секреты.
    
3. Заменить секретные значения переменными.
    
4. Сохранить только фактический готовый image.
    
5. Не добавлять mounts, пути которых ещё не подтверждены.
    
6. Проверить итоговую конфигурацию.
    
7. Только после проверки переключить рабочий запуск на новый Compose.
    

## Проверка

```bash
docker compose config --services
docker compose config --images
docker compose config --volumes
```

Проверить отсутствие build:

```bash
rg -n '^\s*build\s*:' compose.yaml
```

Ожидается отсутствие результата.

Также проверить отсутствие Dockerfile:

```bash
find . -iname 'Dockerfile*' -print
```

Ожидается отсутствие результата.

## Критерий завершения

```text
git clone
→ создать .env
→ docker compose pull
→ docker compose up
```

достаточно для запуска неизменённого Hermes image.

---

# Шаг 20. Создать probe plugin по фактическому API Hermes

## Цель

Проверить интеграционные возможности Hermes, не начиная разработку production plugin.

## Важное ограничение

На этом шаге нельзя заранее придумывать:

- формат manifest;
    
- имя entrypoint;
    
- Python imports;
    
- signature tool handler;
    
- hook names;
    
- plugin discovery path.
    

Codex сначала исследует установленную версию Hermes.

## Задание Codex

В IDE запустить:

```text
$hermes-container-spike

Задача: исследовать фактический plugin API текущего Hermes container.

Сначала ничего не изменяй.

Найди и зафиксируй:

1. Путь поиска plugins.
2. Формат manifest.
3. Entry point plugin.
4. Способ регистрации tool.
5. Способ регистрации hook.
6. Способ назначения toolset.
7. Нужно ли явное enable.
8. Нужен ли restart.
9. Какие dependencies уже доступны в image.
10. Какие correlation/session identifiers получает handler.

Используй только:
- CLI help;
- read-only просмотр файлов контейнера;
- официальную документацию;
- исходный код установленной версии.

Не используй Dockerfile.
Не устанавливай packages.
Не изменяй container.

Запиши результаты в:
docs/experiments/hermes-plugin-api.md
```

## После отчёта

Отдельной задачей Codex:

```text
$verified-small-change
$hermes-container-spike

На основании docs/experiments/hermes-plugin-api.md создай
минимальный probe plugin в plugins/menu-planner-probe.

Plugin должен:

1. Регистрировать ровно один tool.
2. Принимать строковый request_id и payload.
3. Возвращать структурированный JSON success.
4. Уметь вернуть структурированную validation error.
5. Не писать на диск.
6. Не использовать сеть.
7. Не иметь внешних dependencies.
8. Не содержать бизнес-логики Menu Planner.

Добавь только необходимые файлы.
Не изменяй production plugin.
```

## Критерий завершения

Probe plugin:

- расположен на host VM;
    
- подключается через read-only bind mount;
    
- обнаруживается Hermes;
    
- не требует копирования в контейнер;
    
- не требует установки package;
    
- не требует изменения image.
    

---

# Шаг 21. Проверить capabilities Hermes

## Цель

Заполнить capability matrix экспериментальными результатами.

## Проверки

### 21.1. Plugin discovery

```text
Контейнер видит plugin после bind mount:
PASS / FAIL
```

### 21.2. Explicit enablement

```text
Требуется явное включение:
YES / NO
```

Если включение создаёт изменяемую конфигурацию, определить, где она хранится:

```text
bind mount:
named volume:
другой механизм:
```

### 21.3. Tool registration

```text
Tool появился у Hermes:
PASS / FAIL
```

### 21.4. Structured arguments

Передать:

```json
{
  "request_id": "stage0-success-001",
  "payload": "hello"
}
```

Проверить точность аргументов.

### 21.5. Structured success

Ожидаемый логический контракт:

```json
{
  "success": true,
  "operation_id": "stage0-success-001",
  "data": {
    "payload": "hello"
  }
}
```

Точный wrapper определяется фактическим Hermes API.

### 21.6. Structured error

Проверить, что handler может вернуть машинную ошибку, не разрушая agent loop.

### 21.7. Hooks

Проверить:

```text
pre-tool hook вызывается:
post-tool hook вызывается:
pre-tool hook может блокировать call:
```

Даже если hook блокирует вызов, архитектура всё равно требует повторять критические проверки внутри tool handler.

### 21.8. Toolsets

Проверить:

```text
Tool можно включить:
Tool можно отключить:
Нужна новая session:
Нужен restart:
```

### 21.9. Correlation

Проверить наличие:

```text
task_id:
session_id:
turn_id:
user_id:
platform:
```

Доменные `operation_id` должны генерироваться приложением и не зависеть от внутренних ID Hermes.

### 21.10. Skills

Проверить:

```text
Путь skills:
Формат:
Автообнаружение:
Reload или restart:
```

### 21.11. Telegram Gateway

Проверить:

```text
Inline buttons существуют:
Custom callback API доступен plugin:
Telegram user ID передаётся:
Callback data доступна:
Confirmation ID можно связать с callback:
```

Это остаётся открытым вопросом архитектуры до экспериментальной проверки установленной версии Hermes.

---

# Шаг 22. Проверить runtime state и volumes

## Цель

Разделить read-only проектные данные и изменяемое состояние Hermes.

## Классификация

### Bind mounts `ro`

```text
config/hermes/
plugins/menu-planner/
plugins/menu-planner-probe/
skills/hermes/
src/
```

### Named volumes `rw`

```text
sessions
memory
runtime state
cache, если нужен
```

### Не хранить в volume без необходимости

```text
application source
plugin source
skills source
versioned configuration
```

## Проверка сохранения состояния

1. Зафиксировать существующую session или тестовый runtime marker штатным способом Hermes.
    
2. Выполнить:
    

```bash
docker compose down
docker compose up -d
```

3. Проверить сохранение state.
    

После этого отдельно:

```bash
docker compose down -v
```

использовать только с явным подтверждением, потому что команда удаляет named volumes проекта.

## Критерий завершения

Известно:

- какие данные переживают пересоздание контейнера;
    
- какие данные переживают `docker compose down`;
    
- какие данные удаляются вместе с volumes;
    
- какие данные должны переноситься при миграции.
    

---

# Шаг 23. Проверить воспроизводимость с нуля

## Цель

Доказать, что система не зависит от ручных изменений контейнера.

## Последовательность

Сохранить необходимые runtime данные, затем:

```bash
docker compose down
```

Проверить отсутствие Dockerfile:

```bash
find . -iname 'Dockerfile*' -print
```

Проверить отсутствие build:

```bash
rg -n '^\s*build\s*:' compose.yaml
```

Запустить:

```bash
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=100 hermes
```

Проверить:

- Hermes запущен;
    
- probe plugin обнаружен;
    
- Hermes skills доступны;
    
- mounts работают;
    
- config применяется;
    
- state хранится в ожидаемом volume;
    
- никаких команд установки внутри контейнера не требуется.
    

## Критерий завершения

Полный запуск выполняется только командами:

```bash
docker compose pull
docker compose up -d
```

и файлами из репозитория плюс `.env`.

---

# Шаг 24. Заполнить итоговый отчёт этапа 0

Создать:

```text
docs/experiments/hermes-capability-spike.md
```

Структура:

```markdown
# Hermes capability spike

## Environment

- Ubuntu:
- architecture:
- Docker:
- Docker Compose:
- Hermes image:
- Hermes digest:
- Hermes version:
- Codex version:

## Deployment constraints

- ready image only:
- Dockerfile absent:
- build absent:
- project files mounted:
- runtime state externalized:

## Capability matrix

| Capability | Result | Evidence | Decision |
|---|---|---|---|
| Plugin discovery | | | |
| Plugin enablement | | | |
| Tool registration | | | |
| Structured arguments | | | |
| Structured success | | | |
| Structured errors | | | |
| Pre-tool hook | | | |
| Post-tool hook | | | |
| Hook blocking | | | |
| Toolsets | | | |
| Sessions | | | |
| Correlation IDs | | | |
| Hermes skills | | | |
| Telegram callbacks | | | |
| State persistence | | | |

## Mount map

| Purpose | Host | Container | Mode |
|---|---|---|---|

## Missing capabilities

## Required adapters

## Documentation conflicts

## Security observations

## Open questions

## Final recommendation
```

---

# Шаг 25. Принять решение о завершении этапа

## Этап 0 завершён, когда выполнены все пункты

```text
[ ] VS Code подключается к VM через Remote-SSH.
[ ] Codex extension работает на SSH-host.
[ ] Codex CLI установлен на VM.
[ ] Codex авторизован.
[ ] sandbox = workspace-write.
[ ] approval policy = on-request.
[ ] OpenAI Developer Docs MCP подключён.
[ ] Global AGENTS.md загружается.
[ ] Project AGENTS.md загружается.
[ ] Project rules проверены.
[ ] Codex skills обнаруживаются.
[ ] Репозиторий создан.
[ ] Документы проекта находятся в docs/.
[ ] Docker и Docker Compose работают.
[ ] Найден текущий Compose Hermes.
[ ] Зафиксирован Hermes image digest.
[ ] В Compose отсутствует build.
[ ] Dockerfile отсутствует.
[ ] Определены user, HOME и workdir контейнера.
[ ] Определён путь конфигурации Hermes.
[ ] Определён путь plugins.
[ ] Определён путь Hermes skills.
[ ] Определены runtime state paths.
[ ] Read-only bind mount проверен.
[ ] Probe plugin подключён bind mount.
[ ] Tool registration проверена.
[ ] Hooks проверены.
[ ] Toolsets проверены.
[ ] Sessions и correlation IDs исследованы.
[ ] Telegram callback capability исследована.
[ ] State persistence проверена.
[ ] Контейнер воспроизводимо пересоздаётся.
[ ] В контейнере не выполнялись ручные установки.
[ ] Capability report заполнен.
[ ] Open questions записаны.
```

## Финальный commit

Перед commit:

```bash
git status --short
git diff --check
git diff --stat
```

Затем:

```bash
git add .
git commit -m "chore: complete stage 0 environment and Hermes capability setup"
```

---

# Последовательность работы с Codex на этапе 0

Каждая задача передаётся отдельно.

## Задача 1

```text
$verified-small-change

Проверь структуру репозитория и AGENTS.md.
Ничего не меняй.
Сообщи, соответствует ли структура этапу 0.
```

## Задача 2

```text
$verified-small-change

Создай только документацию baseline VM и Codex.
Не работай с Hermes.
```

## Задача 3

```text
$hermes-container-spike

Исследуй существующий Compose и контейнер Hermes.
Ничего не изменяй.
Создай baseline report.
```

## Задача 4

```text
$verified-small-change
$hermes-container-spike

Добавь только нейтральный read-only mount probe.
Не создавай plugin.
```

## Задача 5

```text
$hermes-container-spike

Определи фактический plugin API Hermes.
Сначала создай отчёт.
Не создавай plugin.
```

## Задача 6

```text
$verified-small-change
$hermes-container-spike

Создай минимальный capability probe plugin
по подтверждённому API.
```

## Задача 7

```text
$hermes-container-spike

Выполни capability tests и заполни matrix.
Не создавай production Menu Planner functionality.
```

Такой порядок не позволяет Codex сразу перейти к большой реализации на основании непроверенных предположений.