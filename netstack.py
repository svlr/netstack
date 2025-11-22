#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
from pathlib import Path
from typing import List

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

from netstack_core.profiles import PathsConfig, ProfileManager
from netstack_core.singbox_runner import SingBoxRunner
from netstack_core.commands_base import AppContext, Command
from netstack_core.commands_builtin import get_builtin_commands


def load_custom_commands() -> List[Command]:
    """
    Плагины: любые файлы netstack_core/commands_*.py
    c функцией register(commands: list[Command]) -> None.
    """
    import importlib
    commands: List[Command] = []
    core_dir = Path(__file__).resolve().parent / "netstack_core"

    for path in core_dir.glob("commands_*.py"):
        module_name = f"netstack_core.{path.stem}"
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "register"):
                module.register(commands)
        except Exception as e:
            print(f"Failed to load custom module {module_name}: {e}")
    return commands


def show_menu(commands: List[Command]) -> int | None:
    print("\n========== netstack CLI ==========")
    for idx, cmd in enumerate(commands, start=1):
        print(f"{idx}) {cmd.name}")
    print("==================================")
    choice = input("Your choice: ").strip()
    if not choice.isdigit():
        print("Invalid input.")
        return None
    num = int(choice)
    if num < 1 or num > len(commands):
        print("Number out of range.")
        return None
    return num - 1


def main():
    root_dir = Path(__file__).resolve().parent
    core_dir = root_dir / "netstack_core"

    paths = PathsConfig(
        base_dir=core_dir,
        config_dir=core_dir / "configs",
        log_dir=core_dir / "logs",
        sing_box_bin=core_dir / "sing-box",
    )

    if not paths.sing_box_bin.exists() or not paths.sing_box_bin.is_file():
        print(f"Error: sing-box binary not found: {paths.sing_box_bin}")
        return

    profiles = ProfileManager(paths)
    runner = SingBoxRunner(paths)
    ctx = AppContext(paths=paths, profiles=profiles, runner=runner)

    def handle_sigint(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handle_sigint)

    commands: List[Command] = []
    commands.extend(get_builtin_commands())
    commands.extend(load_custom_commands())
    
    try:
        while ctx.running:
            clear_screen()
            idx = show_menu(commands)
            if idx is None:
                continue
            cmd = commands[idx]
            cmd.execute(ctx)
            if ctx.running:
                input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        runner.stop()


if __name__ == "__main__":
    main()
