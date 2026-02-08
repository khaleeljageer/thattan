from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml


@dataclass(frozen=True)
class Level:
    key: str
    name: str
    tasks: List[str]


class LevelRepository:
    def __init__(self) -> None:
        self._levels = self._load_levels()

    def all(self) -> List[Level]:
        return list(self._levels.values())

    def get(self, key: str) -> Level:
        return self._levels[key]

    def _load_levels(self) -> Dict[str, Level]:
        base_dir = Path(__file__).resolve().parent.parent / "data" / "levels"
        if not base_dir.exists():
            raise FileNotFoundError(f"Levels directory not found: {base_dir}")

        levels: Dict[str, Level] = {}

        def _sort_key(p: Path) -> tuple[int, str]:
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
                # allow content as multiline string
                text = str(content).strip()
                tasks = [line.strip() for line in text.splitlines() if line.strip()]
            if not tasks:
                raise ValueError(f"{level_path.name}: 'content' has no tasks")
            levels[key] = Level(key=key, name=title.strip(), tasks=tasks)

        if not levels:
            raise ValueError("No level files (level*.yaml) found in data/levels")
        return levels
