"""Tests for thattan.ui.models – LevelState dataclass."""

from __future__ import annotations

import pytest

from thattan.core.levels import Level
from thattan.ui.models import LevelState


# ===========================================================================
# LevelState dataclass
# ===========================================================================

class TestLevelState:
    @pytest.fixture()
    def sample_level(self) -> Level:
        return Level(key="level0", name="Basics", tasks=["a", "b"])

    def test_creation(self, sample_level: Level):
        ls = LevelState(level=sample_level, unlocked=True, completed=5)
        assert ls.level is sample_level
        assert ls.unlocked is True
        assert ls.completed == 5
        assert ls.is_current is False  # default

    def test_is_current_default(self, sample_level: Level):
        ls = LevelState(level=sample_level, unlocked=False, completed=0)
        assert ls.is_current is False

    def test_is_current_explicit(self, sample_level: Level):
        ls = LevelState(level=sample_level, unlocked=True, completed=3, is_current=True)
        assert ls.is_current is True

    def test_equality(self, sample_level: Level):
        a = LevelState(level=sample_level, unlocked=True, completed=3, is_current=False)
        b = LevelState(level=sample_level, unlocked=True, completed=3, is_current=False)
        assert a == b

    def test_inequality_different_completed(self, sample_level: Level):
        a = LevelState(level=sample_level, unlocked=True, completed=3)
        b = LevelState(level=sample_level, unlocked=True, completed=5)
        assert a != b

    def test_mutable(self, sample_level: Level):
        ls = LevelState(level=sample_level, unlocked=False, completed=0)
        ls.unlocked = True
        ls.completed = 10
        ls.is_current = True
        assert ls.unlocked is True
        assert ls.completed == 10
        assert ls.is_current is True

    def test_level_reference(self, sample_level: Level):
        ls = LevelState(level=sample_level, unlocked=True, completed=0)
        assert ls.level.key == "level0"
        assert ls.level.name == "Basics"
        assert ls.level.tasks == ["a", "b"]
