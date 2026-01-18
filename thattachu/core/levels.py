from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict


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
        for level_path in sorted(base_dir.glob("level*.txt")):
            key = level_path.stem
            tasks = [line.strip() for line in level_path.read_text().splitlines() if line.strip()]
            if not tasks:
                raise ValueError(f"{level_path.name} has no tasks")
            name = key.replace("level", "நிலை ")
            levels[key] = Level(key=key, name=name, tasks=tasks)

        if not levels:
            raise ValueError("No level files found in data/levels")
        return levels
