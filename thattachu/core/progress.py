from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict


@dataclass
class LevelProgress:
    completed: int = 0
    best_wpm: float = 0.0
    best_accuracy: float = 0.0


class ProgressStore:
    def __init__(self) -> None:
        self._file_path = Path.home() / ".thattachu" / "progress.json"
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._progress = self._load()

    def get_level_progress(self, level_key: str) -> LevelProgress:
        return self._progress.get(level_key, LevelProgress())

    def update_level_progress(
        self,
        level_key: str,
        completed: int,
        wpm: float,
        accuracy: float,
    ) -> None:
        current = self._progress.get(level_key, LevelProgress())
        current.completed = max(current.completed, completed)
        current.best_wpm = max(current.best_wpm, wpm)
        current.best_accuracy = max(current.best_accuracy, accuracy)
        self._progress[level_key] = current
        self._save()

    def reset(self) -> None:
        self._progress = {}
        self._save()

    def _load(self) -> Dict[str, LevelProgress]:
        if not self._file_path.exists():
            return {}
        try:
            payload = json.loads(self._file_path.read_text())
        except json.JSONDecodeError:
            return {}

        result: Dict[str, LevelProgress] = {}
        for key, value in payload.get("levels", {}).items():
            result[key] = LevelProgress(
                completed=int(value.get("completed", 0)),
                best_wpm=float(value.get("best_wpm", 0.0)),
                best_accuracy=float(value.get("best_accuracy", 0.0)),
            )
        return result

    def _save(self) -> None:
        payload = {"levels": {key: asdict(value) for key, value in self._progress.items()}}
        self._file_path.write_text(json.dumps(payload, indent=2))
