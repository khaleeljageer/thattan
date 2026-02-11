"""Data models used by the UI."""

from __future__ import annotations

from dataclasses import dataclass

from thattan.core.levels import Level


@dataclass
class LevelState:
    """UI state for a single level: progress, unlock status, and selection."""

    level: Level
    unlocked: bool
    completed: int
    is_current: bool = False
