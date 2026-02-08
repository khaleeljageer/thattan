"""Data models used by the UI."""

from __future__ import annotations

from dataclasses import dataclass

from thattan.core.levels import Level


@dataclass
class LevelState:
    level: Level
    unlocked: bool
    completed: int
    is_current: bool = False
