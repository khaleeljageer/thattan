from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TaskResult:
    accuracy: float
    wpm: float
    errors: int


class TypingSession:
    def __init__(self, tasks: list[str], start_index: int = 0) -> None:
        self._tasks = tasks
        self._index = start_index
        self._start_time = time.time()
        self._total_chars = 0
        self._total_correct = 0
        self._total_errors = 0

    @property
    def index(self) -> int:
        return self._index

    @property
    def total_tasks(self) -> int:
        return len(self._tasks)

    def current_task(self) -> str:
        return self._tasks[self._index]

    def is_complete(self) -> bool:
        return self._index >= len(self._tasks)

    def submit(self, typed: str) -> TaskResult:
        target = self._tasks[self._index]
        correct = sum(1 for a, b in zip(typed, target) if a == b)
        total = max(len(target), len(typed))
        errors = total - correct
        self._total_chars += total
        self._total_correct += correct
        self._total_errors += errors

        elapsed_minutes = max((time.time() - self._start_time) / 60.0, 1e-6)
        gross_wpm = (self._total_chars / 5.0) / elapsed_minutes
        accuracy = (correct / total) * 100.0 if total else 0.0
        self._index += 1

        return TaskResult(
            accuracy=accuracy,
            wpm=gross_wpm,
            errors=errors,
        )

    def aggregate_accuracy(self) -> float:
        total = max(self._total_chars, 1)
        return (self._total_correct / total) * 100.0

    def aggregate_wpm(self) -> float:
        elapsed_minutes = max((time.time() - self._start_time) / 60.0, 1e-6)
        return (self._total_chars / 5.0) / elapsed_minutes

    def aggregate_errors(self) -> int:
        return self._total_errors
