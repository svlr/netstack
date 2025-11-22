# netstack

Portable, profile-based VPN/proxy client built around [`sing-box`](https://sing-box.sagernet.org/) and Python.

All you need is:

- a `sing-box` binary,
- Python 3,
- this repo.

No installers, no system-wide config magic. Drop it on a USB stick, plug into any Linux machine with Python 3, paste your VLESS URL — and you have:

- a local SOCKS5 proxy, or
- a full TUN-based VPN tunnel,

running off your own server.

---

- [English](#english)
- [Русский](#русский)

---

## English

### Idea

`netstack` is a **minimal portable client** for people who:

- already have a VLESS/Reality server (e.g. via `3x-ui`),
- don’t want to install heavy GUI clients everywhere,
- want something they can carry around (flash drive, external disk),
- and like to see exactly what the client is doing.

It wraps `sing-box` in a small, modular Python CLI with:

- profile management,
- config auto-generation from VLESS URLs,
- SOCKS and TUN modes,
- pluggable commands.

---

### Features

- **Portable**: just Python 3 + `sing-box` binary in `netstack_core/`.
- **Profiles based on VLESS URLs**:
  - paste a `vless://...` link,
  - netstack generates both:
    - `<profile>-socks.json` (local proxy),
    - `<profile>-tun.json` (VPN).
- **Profile manager**:
  - auto-naming (`my-server`, `my-server-2`, …),
  - list & select profiles from CLI.
- **SOCKS mode**:
  - starts `sing-box` as a local SOCKS5 proxy (`127.0.0.1:1080`),
  - opens a subshell with proxy environment vars set.
- **VPN (TUN) mode**:
  - creates a `tun0` interface,
  - routes (almost) all traffic through your server,
  - excludes local LAN by default.
- **Logging**:
  - all `sing-box` output goes into `netstack_core/logs/*.log`,
  - your terminal stays clean.
- **Extensible**:
  - drop a `netstack_core/commands_*.py` with a `register()` function,
  - it shows up as a new menu item automatically.

---

### Project layout

```text
netstack/
├─ netstack.py              # main entrypoint / CLI
└─ netstack_core/
   ├─ __init__.py
   ├─ sing-box             # sing-box binary (executable)
   ├─ configs/             # generated profile configs
   ├─ logs/                # sing-box log files
   ├─ vless.py             # VLESS URL parser
   ├─ profiles.py          # profile & config management
   ├─ singbox_runner.py    # sing-box process wrapper (SOCKS/TUN)
   ├─ commands_base.py     # AppContext + Command protocol
   └─ commands_builtin.py  # built-in CLI commands
```

---

### Requirements

- Linux (TUN mode is Linux-oriented; SOCKS mode is more portable).
- Python **3.10+** recommended.
- `sing-box` binary compatible with your system:
  - downloaded or built, placed as `netstack_core/sing-box`,
  - must be executable (`chmod +x netstack_core/sing-box`).

---

### Quick start

1. Clone / copy the repo structure:

   ```bash
   git clone <this-repo> netstack
   cd netstack
   mkdir -p netstack_core/configs netstack_core/logs
   # put your sing-box binary here:
   cp /path/to/sing-box netstack_core/sing-box
   chmod +x netstack_core/sing-box
   ```

2. Run the CLI:

   ```bash
   python3 netstack.py
   ```

3. Create a profile (option `1`):

   - Paste your `vless://...` URL.
   - Accept or override the suggested profile name.

4. Use:

   - **SOCKS proxy mode** (option `3`):
     - opens a subshell where all traffic goes through `127.0.0.1:1080`.
   - **VPN (TUN) mode** (option `4`, run with `sudo`):
     - routes system traffic through `tun0` and your server.

---

### How profiles & configs work

**Input**: a VLESS URL, e.g.:

```text
vless://89d0...8517@166.1.160.59:443?type=tcp&security=reality&pbk=...&fp=chrome&sni=www.google.com&sid=...&spx=%2F#my-cool-server
```

`netstack_core.vless.parse_vless_url` extracts:

- `uuid`
- `server`, `server_port`
- Reality parameters:
  - `security`, `pbk`, `sid`, `sni`, `fp`
- optional name (from URL fragment, e.g. `#my-cool-server`)

`ProfileManager.create_profile_from_vless` then builds two configs:

- `netstack_core/configs/<profile>-socks.json`
- `netstack_core/configs/<profile>-tun.json`

They are standard `sing-box` JSON configs with:

- outbound: VLESS with Reality,
- inbound:
  - SOCKS: local proxy,
  - TUN: `tun0` TUN interface, `auto_route`, `auto_redirect`, DNS detour, etc.

You can inspect or tweak them manually if needed.

---

### SOCKS mode: local proxy

Menu option: **“Run local SOCKS proxy and open proxied shell”**

What happens:

1. `SingBoxRunner.run_socks_shell()`:
   - starts `sing-box` with `<profile>-socks.json`,
   - logs → `logs/<profile>-socks-YYYYMMDD-HHMMSS.log`,
   - sets environment variables in a new `bash` subshell:

     ```bash
     ALL_PROXY="socks5h://127.0.0.1:1080"
     all_proxy="$ALL_PROXY"
     http_proxy="$ALL_PROXY"
     https_proxy="$ALL_PROXY"
     ```

2. Inside that subshell you can run:

   ```bash
   curl ifconfig.me
   pacman -Syu
   git clone ...
   ```

3. When you `exit` or press `Ctrl+D`, netstack kills `sing-box` and returns to the main menu.

#### Using SOCKS mode with GUI/apps

Because only the subshell has proxy env vars, GUI apps launched from that shell will also use the proxy (if they respect `http_proxy`/`ALL_PROXY`).

Alternatively, **manually configure SOCKS in apps**:

- Address: `127.0.0.1`
- Port: `1080`
- Type: SOCKS5 (SOCKS5h for DNS over proxy if supported)

Examples:

- Firefox / Chromium:
  - Settings → Network → Manual proxy config → SOCKS host `127.0.0.1`, port `1080`.
- Some launchers/DEs:
  - run your GUI apps from the proxied shell so they inherit env vars.

---

### VPN mode: TUN interface

Menu option: **“Run VPN (TUN mode)”**

> ⚠️ Requires root: run `sudo python3 netstack.py`.

What happens:

1. `SingBoxRunner.run_vpn_blocking()`:
   - starts `sing-box` with `<profile>-tun.json`,
   - logs → `logs/<profile>-tun-YYYYMMDD-HHMMSS.log`,
   - TUN inbound:
     - `interface_name: "tun0"`,
     - address: `172.19.0.1/30`,
     - `auto_route`, `auto_redirect`, `strict_route`,
     - DNS via DoH (`1.1.1.1`) detoured through VLESS outbound,
     - local networks (e.g. `192.168.0.0/16`) excluded and kept direct.

2. Your system traffic now flows through `tun0` and your VLESS/Reality server, except LAN.

3. While VPN is running, netstack shows a small prompt:

   ```text
   [netstack vpn] > 
   ```

   Type `q`, `quit`, or `exit` + Enter to stop VPN and return to the menu.

---

### Logs

All `sing-box` output is redirected to log files:

- directory: `netstack_core/logs/`
- names: `<profile>-socks-YYYYMMDD-HHMMSS.log`, `<profile>-tun-YYYYMMDD-HHMMSS.log`

This keeps the CLI clean while still letting you debug:

```bash
tail -f netstack_core/logs/my-server-tun-20250101-133700.log
```

---

### Extending netstack with custom commands

netstack has a tiny plugin system:

- Any module named `netstack_core/commands_*.py`
- that implements:

  ```python
  def register(commands: list[Command]) -> None:
      ...
  ```

will be auto-loaded and can append its own commands to the main menu.

#### Example: simple “show logs dir” command

Create `netstack_core/commands_info.py`:

```python
from netstack_core.commands_base import Command, AppContext


class ShowPathsCommand:
    name = "Show paths info"
    description = "Print base, config and logs directories"

    def execute(self, ctx: AppContext) -> None:
        print("Base directory:  ", ctx.paths.base_dir)
        print("Configs directory:", ctx.paths.config_dir)
        print("Logs directory:   ", ctx.paths.log_dir)


def register(commands: list[Command]) -> None:
    commands.append(ShowPathsCommand())
```

On next run of `python3 netstack.py` you’ll see a new menu item with that name.

You can:

- add diagnostic commands,
- build profile editors,
- add quick-connect shortcuts,
- or anything else that can be expressed in a function `execute(ctx: AppContext)`.

---

### FAQ

**Q: Does it support Windows/macOS?**  
A: The design is portable, but TUN/VPN mode is Linux-specific as written. SOCKS mode may work elsewhere if `sing-box` does.

**Q: Can I edit the generated configs by hand?**  
A: Yes. They are just `sing-box` JSON configs under `netstack_core/configs/`.

**Q: How do I… you know…?**  
A: Just don’t do it in the repository root. 😄

---

## Русский

### Что это вообще такое

`netstack` — это **портативный VPN/прокси-клиент**, собранный вокруг:

- бинарника `sing-box`,
- небольшого CLI на Python.

Идея:

- У тебя уже есть VLESS/Reality-сервер (например через `3x-ui`).
- Ты не хочешь везде ставить тяжёлые GUI-клиенты.
- Хочешь иметь **одну папку**, которую можно кинуть:
  - на флешку,
  - на внешний диск,
  - в домашнюю директорию,
  - и запускать хоть на «чужой» машине.

В этой папке — всё:

- Python-скрипт `netstack.py` (вход),
- папка `netstack_core/` с:
  - `sing-box`,
  - автогенератором конфигов,
  - менеджером профилей,
  - SOCKS-режимом,
  - TUN/VPN-режимом.

---

### Возможности

- **Портативность**: нужен только Python 3 и `sing-box` в `netstack_core/`.
- **Профили на основе VLESS-ключа**:
  - вставляешь `vless://...`,
  - `netstack` создаёт:
    - `<профиль>-socks.json` — режим локального прокси,
    - `<профиль>-tun.json` — режим VPN (TUN).
- **Менеджер профилей**:
  - автогенерация имён (`my-server`, `my-server-2`, …),
  - список профилей и выбор из меню.
- **SOCKS-режим**:
  - поднимает `sing-box` как SOCKS5-прокси `127.0.0.1:1080`,
  - открывает подсhell с выставленными прокси-переменными окружения.
- **VPN (TUN-режим)**:
  - создаёт интерфейс `tun0`,
  - гонит почти весь трафик через твой сервер,
  - исключает локальную сеть (LAN) по умолчанию.
- **Логирование**:
  - вывод `sing-box` пишется в `netstack_core/logs/*.log`,
  - терминал не засирается логами.
- **Расширяемость**:
  - свои файлы `netstack_core/commands_*.py`,
  - регистрируешь команды — они появляются в меню.

---

### Структура проекта

```text
netstack/
├─ netstack.py              # точка входа / CLI
└─ netstack_core/
   ├─ __init__.py
   ├─ sing-box             # бинарник sing-box
   ├─ configs/             # сгенерированные конфиги профилей
   ├─ logs/                # логи sing-box
   ├─ vless.py             # парсер VLESS URL
   ├─ profiles.py          # профили и генерация конфигов
   ├─ singbox_runner.py    # запуск sing-box (SOCKS/TUN)
   ├─ commands_base.py     # AppContext + протокол Command
   └─ commands_builtin.py  # встроенные команды меню
```

---

### Требования

- Linux (TUN-режим написан под Linux; SOCKS-режим более универсален).
- Python **3.10+**.
- Бинарник `sing-box`:
  - кладёшь в `netstack_core/sing-box`,
  - делаешь исполняемым: `chmod +x netstack_core/sing-box`.

---

### Быстрый старт

1. Структура:

   ```bash
   git clone <этот-репозиторий> netstack
   cd netstack
   mkdir -p netstack_core/configs netstack_core/logs
   cp /куда-то/там/sing-box netstack_core/sing-box
   chmod +x netstack_core/sing-box
   ```

2. Запуск CLI:

   ```bash
   python3 netstack.py
   ```

3. Создание профиля (пункт `1`):

   - вставляешь `vless://...` URL,
   - принимаешь или меняешь предложенное имя профиля.

4. Использование:

   - **SOCKS-режим** (пункт `3`):
     - открывается shell, где весь трафик идёт через `127.0.0.1:1080`.
   - **VPN (TUN-режим)** (пункт `4`, запуск через `sudo`):
     - весь системный трафик (кроме LAN) идёт через `tun0` и твой сервер.

---

### Как работают профили и конфиги

**Вход**: VLESS-ссылка, например:

```text
vless://89d0...8517@166.1.160.59:443?type=tcp&security=reality&pbk=...&fp=chrome&sni=www.google.com&sid=...&spx=%2F#my-cool-server
```

Модуль `netstack_core.vless` вытаскивает:

- `uuid`
- `server`, `server_port`
- параметры Reality:
  - `security`, `pbk`, `sid`, `sni`, `fp`
- имя профиля (из `#fragment`, если есть)

`ProfileManager.create_profile_from_vless` создаёт два конфига:

- `netstack_core/configs/<профиль>-socks.json`
- `netstack_core/configs/<профиль>-tun.json`

Это обычные JSON-конфиги `sing-box`:

- outbound: VLESS + Reality;
- inbound:
  - **SOCKS**: локальный прокси,
  - **TUN**: `tun0` с `auto_route`, `auto_redirect`, DNS через VLESS, исключения для LAN.

При желании можно править их руками.

---

### SOCKS-режим: локальный прокси

Меню: **“Run local SOCKS proxy and open proxied shell”**

Что делает:

1. `SingBoxRunner.run_socks_shell()`:
   - запускает `sing-box` с `<профиль>-socks.json`,
   - пишет логи в `logs/<профиль>-socks-YYYYMMDD-HHMMSS.log`,
   - открывает `bash` с:

     ```bash
     ALL_PROXY="socks5h://127.0.0.1:1080"
     all_proxy="$ALL_PROXY"
     http_proxy="$ALL_PROXY"
     https_proxy="$ALL_PROXY"
     ```

2. Внутри этого shell можно:

   ```bash
   curl ifconfig.me
   pacman -Syu
   git clone ...
   ```

3. Выход из shell (`exit` / `Ctrl+D`) → `sing-box` останавливается, возврат в меню.

#### Ручное управление системным прокси / приложениями

Если хочешь, чтобы **GUI-приложения** шли через прокси:

- запускай их из этого прокси-shell (унаследуют переменные окружения),
- или пропиши SOCKS вручную в настройках:

  - адрес: `127.0.0.1`,
  - порт: `1080`,
  - тип: SOCKS5.

Примеры:

- **Браузер**:
  - Firefox/Chromium: настройки → сеть → ручная настройка → SOCKS `127.0.0.1`, порт `1080`.
- **Отдельные программы**:
  - многие умеют читать `http_proxy` / `ALL_PROXY` (если запускать из shell с этими переменными).

---

### VPN (TUN-режим)

Меню: **“Run VPN (TUN mode)”**

> ⚠️ Нужны root-права: `sudo python3 netstack.py`.

Что происходит:

1. `SingBoxRunner.run_vpn_blocking()`:
   - запускает `sing-box` c `<профиль>-tun.json`,
   - логи → `logs/<профиль>-tun-YYYYMMDD-HHMMSS.log`,
   - поднимает `tun0`:
     - адрес `172.19.0.1/30`,
     - `auto_route`, `auto_redirect`, `strict_route`,
     - DNS через `1.1.1.1` (DoH) **через VLESS**,
     - локальные подсети (192.168.x.x, 10.x.x.x и т.д.) идут напрямую.

2. Системный трафик теперь гонится через этот туннель.

3. Внизу показывается промпт:

   ```text
   [netstack vpn] > 
   ```

   Чтобы выйти из VPN и вернуться в меню, введи:

   ```text
   q
   ```

   или `quit` / `exit` + Enter.

---

### Логи

Всё, что пишет `sing-box`, сохраняется в:

- каталог `netstack_core/logs/`,
- файлы вида:
  - `<профиль>-socks-YYYYMMDD-HHMMSS.log`,
  - `<профиль>-tun-YYYYMMDD-HHMMSS.log`.

Можно в любой момент смотреть:

```bash
tail -f netstack_core/logs/my-server-tun-20250101-133700.log
```

---

### Как добавить свои функции/команды

Есть простая плагин-система:

- Любой файл `netstack_core/commands_*.py`,
- В нём — функция:

  ```python
  def register(commands: list[Command]) -> None:
      ...
  ```

- Внутри `register()` добавляешь свои команды в список.

Команда — это любой объект, у которого есть:

- `name` (строка),
- `description` (строка),
- метод `execute(self, ctx: AppContext) -> None`.

#### Пример кастомной команды

`netstack_core/commands_info.py`:

```python
from netstack_core.commands_base import Command, AppContext


class ShowPathsCommand:
    name = "Show paths info"
    description = "Print base, config and logs directories"

    def execute(self, ctx: AppContext) -> None:
        print("Base directory:  ", ctx.paths.base_dir)
        print("Configs directory:", ctx.paths.config_dir)
        print("Logs directory:   ", ctx.paths.log_dir)


def register(commands: list[Command]) -> None:
    commands.append(ShowPathsCommand())
```

После этого при запуске `python3 netstack.py` в меню появится пункт:

```text
X) Show paths info
```

Так можно:

- добавлять свои диагностические утилиты,
- делать редактор профилей,
- скрипты быстрого подключения,
- экспериментальные фичи.

---

### Немного философии (и “как какать”)

> **Q: Как какать?**  
> A: Главное — не в репозиторий. Всё остальное обычно само получается 😄

---
