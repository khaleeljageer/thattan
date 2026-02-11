"""Typing practice UI: letter sequence and hero letter label."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QWidget

from thattan.ui.colors import HomeColors


class LetterSequenceWidget(QWidget):
    """Horizontal row of boxes: completed (✓), current (teal), upcoming (gray)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._letters: list[str] = []
        self._current_index: int = 0
        self.setFixedHeight(60)
        self.setMinimumWidth(200)

    def set_letters(self, letters: list[str]) -> None:
        """Set the letter sequence to display."""
        self._letters = list(letters)
        self.update()

    def set_current(self, index: int) -> None:
        """Set the index of the current letter (clamped to valid range)."""
        self._current_index = max(0, min(index, len(self._letters)))
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the letter sequence boxes (completed, current, upcoming)."""
        super().paintEvent(event)
        if not self._letters:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        s: float = getattr(self, "_scale", 1.0)
        box_size = max(28, int(44 * s))
        spacing = max(4, int(10 * s))
        radius = max(6, int(10 * s))
        current_pt = max(10, int(16 * s))
        other_pt = max(9, int(14 * s))

        total_width = len(self._letters) * (box_size + spacing) - spacing
        start_x = max(0, (self.width() - total_width) // 2)
        y = (self.height() - box_size) // 2
        for i, letter in enumerate(self._letters):
            x = start_x + i * (box_size + spacing)
            if i < self._current_index:
                painter.setBrush(QColor("#e8f5e9"))
                painter.setPen(QPen(QColor(HomeColors.PRIMARY), 2))
                text_color = QColor(HomeColors.PRIMARY)
                display = "✓"
            elif i == self._current_index:
                painter.setBrush(QColor("#e0f7fa"))
                painter.setPen(QPen(QColor(HomeColors.PRIMARY), 2))
                text_color = QColor(HomeColors.PRIMARY)
                display = letter
            else:
                painter.setBrush(QColor(255, 255, 255, 100))
                painter.setPen(QPen(QColor("#b0bec5"), 1))
                text_color = QColor("#b0bec5")
                display = letter
            painter.drawRoundedRect(x, y, box_size, box_size, radius, radius)
            painter.setPen(text_color)
            font = painter.font()
            font.setPointSize(current_pt if i == self._current_index else other_pt)
            font.setBold(i == self._current_index)
            painter.setFont(font)
            painter.drawText(x, y, box_size, box_size, Qt.AlignCenter, display)


class HeroLetterLabel(QLabel):
    """Large teal circle with current character (like test.py HeroLetter)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(120, 120)
        self.setStyleSheet(
            f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {HomeColors.PRIMARY_LIGHT}, stop:1 {HomeColors.PRIMARY});
                color: white;
                border-radius: 60px;
                font-size: 48px;
                font-weight: 900;
            }}
            """
        )
