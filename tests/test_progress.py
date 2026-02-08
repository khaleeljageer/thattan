"""Tests for thattan.core.progress – progress persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from thattan.core.progress import LevelProgress, ProgressStore, _default_gamification


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProgressStore:
    """ProgressStore backed by a temp file so tests don't touch ~/.thattan."""
    fake_file = tmp_path / "progress.json"
    monkeypatch.setattr(
        ProgressStore,
        "__init__",
        lambda self: _init_store(self, fake_file),
    )
    return ProgressStore()


def _init_store(self: ProgressStore, file_path: Path) -> None:
    self._file_path = file_path
    self._file_path.parent.mkdir(parents=True, exist_ok=True)
    self._progress, self._gamification = self._load()


# ---------------------------------------------------------------------------
# LevelProgress dataclass
# ---------------------------------------------------------------------------

class TestLevelProgress:
    def test_defaults(self):
        lp = LevelProgress()
        assert lp.completed == 0
        assert lp.best_wpm == 0.0
        assert lp.best_accuracy == 0.0

    def test_custom_values(self):
        lp = LevelProgress(completed=5, best_wpm=45.0, best_accuracy=98.5)
        assert lp.completed == 5
        assert lp.best_wpm == 45.0
        assert lp.best_accuracy == 98.5


# ---------------------------------------------------------------------------
# default gamification helper
# ---------------------------------------------------------------------------

class TestDefaultGamification:
    def test_returns_zeroes(self):
        g = _default_gamification()
        assert g == {"total_score": 0, "current_streak": 0, "best_streak": 0}

    def test_returns_new_dict(self):
        a = _default_gamification()
        b = _default_gamification()
        assert a is not b


# ---------------------------------------------------------------------------
# ProgressStore – fresh state
# ---------------------------------------------------------------------------

class TestProgressStoreFresh:
    def test_no_file_returns_defaults(self, store: ProgressStore):
        lp = store.get_level_progress("level0")
        assert lp == LevelProgress()

    def test_gamification_defaults(self, store: ProgressStore):
        assert store.get_gamification() == (0, 0, 0)


# ---------------------------------------------------------------------------
# ProgressStore – level progress
# ---------------------------------------------------------------------------

class TestUpdateLevelProgress:
    def test_creates_new_entry(self, store: ProgressStore):
        store.update_level_progress("level0", completed=3, wpm=40.0, accuracy=95.0)
        lp = store.get_level_progress("level0")
        assert lp.completed == 3
        assert lp.best_wpm == 40.0
        assert lp.best_accuracy == 95.0

    def test_keeps_max_completed(self, store: ProgressStore):
        store.update_level_progress("level0", completed=5, wpm=30.0, accuracy=90.0)
        store.update_level_progress("level0", completed=3, wpm=50.0, accuracy=99.0)
        lp = store.get_level_progress("level0")
        assert lp.completed == 5  # kept higher value

    def test_keeps_max_wpm(self, store: ProgressStore):
        store.update_level_progress("level0", completed=1, wpm=50.0, accuracy=80.0)
        store.update_level_progress("level0", completed=2, wpm=30.0, accuracy=90.0)
        assert store.get_level_progress("level0").best_wpm == 50.0

    def test_keeps_max_accuracy(self, store: ProgressStore):
        store.update_level_progress("level0", completed=1, wpm=30.0, accuracy=99.0)
        store.update_level_progress("level0", completed=2, wpm=40.0, accuracy=85.0)
        assert store.get_level_progress("level0").best_accuracy == 99.0

    def test_persists_to_disk(self, store: ProgressStore):
        store.update_level_progress("level0", completed=2, wpm=35.0, accuracy=92.0)
        data = json.loads(store._file_path.read_text(encoding="utf-8"))
        assert "level0" in data["levels"]
        assert data["levels"]["level0"]["completed"] == 2

    def test_multiple_levels(self, store: ProgressStore):
        store.update_level_progress("level0", 5, 40.0, 95.0)
        store.update_level_progress("level1", 3, 50.0, 88.0)
        assert store.get_level_progress("level0").completed == 5
        assert store.get_level_progress("level1").completed == 3


# ---------------------------------------------------------------------------
# ProgressStore – gamification
# ---------------------------------------------------------------------------

class TestUpdateGamification:
    def test_updates_all_fields(self, store: ProgressStore):
        store.update_gamification(total_score=100, current_streak=3, best_streak=5)
        assert store.get_gamification() == (100, 3, 5)

    def test_best_streak_keeps_max(self, store: ProgressStore):
        store.update_gamification(total_score=50, current_streak=5, best_streak=10)
        store.update_gamification(total_score=70, current_streak=2, best_streak=7)
        ts, cs, bs = store.get_gamification()
        assert bs == 10  # kept higher
        assert cs == 2   # replaced
        assert ts == 70   # replaced

    def test_persists_to_disk(self, store: ProgressStore):
        store.update_gamification(10, 2, 5)
        data = json.loads(store._file_path.read_text(encoding="utf-8"))
        assert data["gamification"]["total_score"] == 10


# ---------------------------------------------------------------------------
# ProgressStore – reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_level(self, store: ProgressStore):
        store.update_level_progress("level0", 5, 40.0, 95.0)
        store.reset_level("level0")
        lp = store.get_level_progress("level0")
        assert lp == LevelProgress()

    def test_reset_level_does_not_affect_others(self, store: ProgressStore):
        store.update_level_progress("level0", 5, 40.0, 95.0)
        store.update_level_progress("level1", 3, 30.0, 80.0)
        store.reset_level("level0")
        assert store.get_level_progress("level1").completed == 3

    def test_reset_all(self, store: ProgressStore):
        store.update_level_progress("level0", 5, 40.0, 95.0)
        store.update_gamification(100, 5, 10)
        store.reset()
        assert store.get_level_progress("level0") == LevelProgress()
        assert store.get_gamification() == (0, 0, 0)


# ---------------------------------------------------------------------------
# ProgressStore – loading edge cases
# ---------------------------------------------------------------------------

class TestLoadEdgeCases:
    def test_corrupt_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        f = tmp_path / "progress.json"
        f.write_text("NOT VALID JSON", encoding="utf-8")
        monkeypatch.setattr(
            ProgressStore, "__init__", lambda self: _init_store(self, f)
        )
        s = ProgressStore()
        assert s.get_gamification() == (0, 0, 0)

    def test_missing_levels_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        f = tmp_path / "progress.json"
        f.write_text(json.dumps({"gamification": {"total_score": 5, "current_streak": 1, "best_streak": 2}}), encoding="utf-8")
        monkeypatch.setattr(
            ProgressStore, "__init__", lambda self: _init_store(self, f)
        )
        s = ProgressStore()
        assert s.get_level_progress("level0") == LevelProgress()
        assert s.get_gamification() == (5, 1, 2)

    def test_missing_gamification_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        f = tmp_path / "progress.json"
        f.write_text(json.dumps({"levels": {"level0": {"completed": 3, "best_wpm": 40.0, "best_accuracy": 90.0}}}), encoding="utf-8")
        monkeypatch.setattr(
            ProgressStore, "__init__", lambda self: _init_store(self, f)
        )
        s = ProgressStore()
        assert s.get_level_progress("level0").completed == 3
        assert s.get_gamification() == (0, 0, 0)

    def test_gamification_not_dict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        f = tmp_path / "progress.json"
        f.write_text(json.dumps({"levels": {}, "gamification": "bad"}), encoding="utf-8")
        monkeypatch.setattr(
            ProgressStore, "__init__", lambda self: _init_store(self, f)
        )
        s = ProgressStore()
        assert s.get_gamification() == (0, 0, 0)

    def test_level_missing_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        f = tmp_path / "progress.json"
        f.write_text(json.dumps({"levels": {"level0": {}}}), encoding="utf-8")
        monkeypatch.setattr(
            ProgressStore, "__init__", lambda self: _init_store(self, f)
        )
        s = ProgressStore()
        lp = s.get_level_progress("level0")
        assert lp.completed == 0
        assert lp.best_wpm == 0.0
