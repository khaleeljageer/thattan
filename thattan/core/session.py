from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TaskResult:
    """Result of a single typing task submission."""

    accuracy: float
    wpm: float
    cpm: float
    errors: int


class TypingSession:
    """Tracks a typing practice session across multiple tasks.

    Speed metrics follow the Tux Typing / standard methodology:
      * **CPM** – correct characters per minute.
      * **Gross WPM** – (total characters / 5) / elapsed minutes.
      * **Net WPM** – (total chars − 5 × errors) / 5 / elapsed minutes,
        floored at 0.  This penalises errors the way Tux Typing does.

    The public ``wpm`` / ``aggregate_wpm`` surfaces the *net* WPM so that
    the displayed speed already accounts for mistakes.
    """

    def __init__(self, tasks: list[str], start_index: int = 0) -> None:
        """Initialize a session with the given tasks, optionally starting at a specific index."""
        self._tasks = tasks
        self._index = start_index
        self._start_time = time.time()
        self._total_chars = 0
        self._total_correct = 0
        self._total_errors = 0

    @property
    def index(self) -> int:
        """Index of the current task (0-based)."""
        return self._index

    @property
    def start_time(self) -> float:
        """Unix timestamp when the session started."""
        return self._start_time

    @property
    def total_tasks(self) -> int:
        """Total number of tasks in the session."""
        return len(self._tasks)

    @property
    def total_correct(self) -> int:
        """Total number of correct characters typed so far."""
        return self._total_correct

    def current_task(self) -> str:
        """Return the text of the current task."""
        return self._tasks[self._index]

    def is_complete(self) -> bool:
        """Return True if all tasks have been submitted."""
        return self._index >= len(self._tasks)

    def submit(self, typed: str) -> TaskResult:
        """Submit the user's typed text for the current task and advance to the next."""
        if self._index >= len(self._tasks):
            return TaskResult(accuracy=0.0, wpm=0.0, cpm=0.0, errors=0)
        target = self._tasks[self._index]
        correct = sum(1 for a, b in zip(typed, target) if a == b)
        total = max(len(target), len(typed))
        errors = total - correct
        self._total_chars += total
        self._total_correct += correct
        self._total_errors += errors

        elapsed_minutes = max((time.time() - self._start_time) / 60.0, 1e-6)
        cpm = self._total_correct / elapsed_minutes
        net_wpm = max(0.0, (self._total_chars - 5 * self._total_errors) / 5.0 / elapsed_minutes)

        accuracy = (correct / total) * 100.0 if total else 0.0
        self._index += 1

        return TaskResult(
            accuracy=accuracy,
            wpm=net_wpm,
            cpm=cpm,
            errors=errors,
        )

    def aggregate_accuracy(self) -> float:
        """Overall accuracy (correct chars / total chars) as a percentage."""
        total = max(self._total_chars, 1)
        return (self._total_correct / total) * 100.0

    def aggregate_cpm(self) -> float:
        """Correct characters per minute."""
        elapsed_minutes = max((time.time() - self._start_time) / 60.0, 1e-6)
        return self._total_correct / elapsed_minutes

    def aggregate_wpm(self) -> float:
        """Net WPM (error-adjusted): (total_chars − 5 × errors) / 5 / minutes."""
        elapsed_minutes = max((time.time() - self._start_time) / 60.0, 1e-6)
        return max(0.0, (self._total_chars - 5 * self._total_errors) / 5.0 / elapsed_minutes)

    def aggregate_gross_wpm(self) -> float:
        """Gross WPM (no error penalty): total_chars / 5 / minutes."""
        elapsed_minutes = max((time.time() - self._start_time) / 60.0, 1e-6)
        return (self._total_chars / 5.0) / elapsed_minutes

    def aggregate_errors(self) -> int:
        """Total number of errors across all submitted tasks."""
        return self._total_errors
