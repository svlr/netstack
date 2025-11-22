# netstack_core/commands_base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .profiles import ProfileManager, PathsConfig
from .singbox_runner import SingBoxRunner


@dataclass
class AppContext:
    paths: PathsConfig
    profiles: ProfileManager
    runner: SingBoxRunner
    running: bool = True


class Command(Protocol):
    name: str
    description: str

    def execute(self, ctx: AppContext) -> None:
        ...
