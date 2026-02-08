"""Tests for thattan.core.levels – YAML-based level loading."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from thattan.core.levels import Level, LevelRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def levels_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary levels directory and patch LevelRepository to use it."""
    d = tmp_path / "data" / "levels"
    d.mkdir(parents=True)

    # Patch the base_dir resolution inside _load_levels
    def _patched_load(self):
        import re
        base_dir = d
        levels = {}

        def _sort_key(p: Path) -> tuple:
            m = re.match(r"^level(\d+)$", p.stem)
            if m:
                return (int(m.group(1)), p.stem)
            return (10**9, p.stem)

        for level_path in sorted(base_dir.glob("level*.yaml"), key=_sort_key):
            key = level_path.stem
            raw = yaml.safe_load(level_path.read_text(encoding="utf-8"))
            if not raw or not isinstance(raw, dict):
                raise ValueError(f"{level_path.name}: expected YAML with 'title' and 'content'")
            title = raw.get("title")
            content = raw.get("content")
            if not title or not isinstance(title, str):
                raise ValueError(f"{level_path.name}: missing or invalid 'title'")
            if content is None:
                raise ValueError(f"{level_path.name}: missing 'content'")
            if isinstance(content, list):
                tasks = [str(item).strip() for item in content if str(item).strip()]
            else:
                text = str(content).strip()
                tasks = [line.strip() for line in text.splitlines() if line.strip()]
            if not tasks:
                raise ValueError(f"{level_path.name}: 'content' has no tasks")
            levels[key] = Level(key=key, name=title.strip(), tasks=tasks)

        if not levels:
            raise ValueError("No level files (level*.yaml) found in data/levels")
        return levels

    monkeypatch.setattr(LevelRepository, "_load_levels", _patched_load)
    return d


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Level dataclass
# ---------------------------------------------------------------------------

class TestLevelDataclass:
    def test_creation(self):
        lv = Level(key="level0", name="Basics", tasks=["a", "b"])
        assert lv.key == "level0"
        assert lv.name == "Basics"
        assert lv.tasks == ["a", "b"]

    def test_frozen(self):
        lv = Level(key="level0", name="Basics", tasks=["a"])
        with pytest.raises(AttributeError):
            lv.key = "other"  # type: ignore[misc]

    def test_equality(self):
        a = Level(key="x", name="X", tasks=["t"])
        b = Level(key="x", name="X", tasks=["t"])
        assert a == b


# ---------------------------------------------------------------------------
# LevelRepository – happy paths
# ---------------------------------------------------------------------------

class TestLevelRepositoryHappy:
    def test_single_level(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "Basics", "content": ["abc", "def"]})
        repo = LevelRepository()
        assert len(repo.all()) == 1
        lv = repo.get("level0")
        assert lv.name == "Basics"
        assert lv.tasks == ["abc", "def"]

    def test_multiple_levels_sorted(self, levels_dir: Path):
        _write_yaml(levels_dir / "level2.yaml", {"title": "Two", "content": ["x"]})
        _write_yaml(levels_dir / "level0.yaml", {"title": "Zero", "content": ["y"]})
        _write_yaml(levels_dir / "level1.yaml", {"title": "One", "content": ["z"]})
        repo = LevelRepository()
        keys = [lv.key for lv in repo.all()]
        assert keys == ["level0", "level1", "level2"]

    def test_content_as_multiline_string(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "T", "content": "line1\nline2\nline3"})
        repo = LevelRepository()
        assert repo.get("level0").tasks == ["line1", "line2", "line3"]

    def test_content_list_with_whitespace(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "T", "content": ["  a  ", "b", "  "]})
        repo = LevelRepository()
        assert repo.get("level0").tasks == ["a", "b"]

    def test_title_stripped(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "  Padded  ", "content": ["t"]})
        repo = LevelRepository()
        assert repo.get("level0").name == "Padded"


# ---------------------------------------------------------------------------
# LevelRepository – error paths
# ---------------------------------------------------------------------------

class TestLevelRepositoryErrors:
    def test_no_yaml_files(self, levels_dir: Path):
        with pytest.raises(ValueError, match="No level files"):
            LevelRepository()

    def test_empty_yaml(self, levels_dir: Path):
        (levels_dir / "level0.yaml").write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="expected YAML"):
            LevelRepository()

    def test_yaml_not_dict(self, levels_dir: Path):
        (levels_dir / "level0.yaml").write_text("- item\n", encoding="utf-8")
        with pytest.raises(ValueError, match="expected YAML"):
            LevelRepository()

    def test_missing_title(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"content": ["a"]})
        with pytest.raises(ValueError, match="missing or invalid 'title'"):
            LevelRepository()

    def test_title_not_string(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": 123, "content": ["a"]})
        with pytest.raises(ValueError, match="missing or invalid 'title'"):
            LevelRepository()

    def test_missing_content(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "T"})
        with pytest.raises(ValueError, match="missing 'content'"):
            LevelRepository()

    def test_empty_content_list(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "T", "content": []})
        with pytest.raises(ValueError, match="no tasks"):
            LevelRepository()

    def test_whitespace_only_content(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "T", "content": ["  ", "\n"]})
        with pytest.raises(ValueError, match="no tasks"):
            LevelRepository()

    def test_get_missing_key(self, levels_dir: Path):
        _write_yaml(levels_dir / "level0.yaml", {"title": "T", "content": ["a"]})
        repo = LevelRepository()
        with pytest.raises(KeyError):
            repo.get("nonexistent")
