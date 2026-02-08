"""Level selection UI: LevelCard and LevelMapWidget."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from thattan.ui.colors import blend_hex
from thattan.ui.models import LevelState


class LevelCard(QWidget):
    """A clickable, styled level card with optional progress ring."""

    def __init__(
        self,
        *,
        base_color: str,
        text_color: str,
        on_click: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._base_color = base_color
        self._text_color = text_color
        self._on_click = on_click
        self._level_key: str = ""
        self._unlocked: bool = True
        self._progress: float = 0.0
        self._is_current: bool = False
        self._is_completed: bool = False

        self.setObjectName("levelCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        # Header strip
        header = QWidget()
        header.setObjectName("levelCardHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        self._title = QLabel("")
        self._title.setObjectName("levelCardTitle")
        self._title.setWordWrap(True)
        self._title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._lock_badge = QLabel("🔒")
        self._lock_badge.setObjectName("levelCardLockBadge")
        self._lock_badge.setAlignment(Qt.AlignCenter)
        self._lock_badge.setFixedSize(24, 24)

        header_layout.addWidget(self._title, 1)
        header_layout.addWidget(self._lock_badge, 0, Qt.AlignRight)

        # Center: percent/lock/check
        self._center = QLabel("")
        self._center.setObjectName("levelCardCenter")
        self._center.setAlignment(Qt.AlignCenter)
        self._center.setMinimumHeight(86)

        # Start pill for the current playable level
        self._start_pill = QLabel("காண்போம்")
        self._start_pill.setObjectName("levelCardStartPill")
        self._start_pill.setAlignment(Qt.AlignCenter)
        self._start_pill.setFixedHeight(30)
        self._start_pill.setVisible(False)

        # XP bar + text
        self._xp_bar = QProgressBar()
        self._xp_bar.setObjectName("levelCardXpBar")
        self._xp_bar.setTextVisible(False)
        self._xp_bar.setFixedHeight(10)
        self._xp_bar.setRange(0, 100)

        self._progress_text = QLabel("")
        self._progress_text.setObjectName("levelCardXpText")
        self._progress_text.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(header, 0)
        layout.addStretch(1)
        layout.addWidget(self._center, 0, Qt.AlignCenter)
        layout.addWidget(self._start_pill, 0, Qt.AlignHCenter)
        layout.addStretch(1)
        layout.addWidget(self._xp_bar)
        layout.addWidget(self._progress_text)

        # Soft shadow like the reference cards
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(26)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(15, 23, 42, 80))
        self.setGraphicsEffect(shadow)

        self._apply_styles()

    def _apply_styles(self) -> None:
        card_top = blend_hex(self._base_color, "#FFFFFF", 0.18)
        card_bottom = blend_hex(self._base_color, "#000000", 0.08)
        self.setStyleSheet(
            f"""
            QWidget#levelCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {card_top},
                    stop:1 {card_bottom}
                );
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.40);
            }}
            QWidget#levelCard:hover {{
                border: 1px solid rgba(255, 255, 255, 0.68);
            }}
            QWidget#levelCardHeader {{
                background: rgba(255, 255, 255, 0.18);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.22);
            }}
            QLabel#levelCardTitle {{
                color: rgba(255, 255, 255, 0.95);
                font-weight: 900;
                font-size: 13px;
            }}
            QLabel#levelCardLockBadge {{
                background: rgba(255, 255, 255, 0.30);
                border-radius: 12px;
                font-size: 13px;
            }}
            QLabel#levelCardCenter {{
                color: rgba(255, 255, 255, 0.96);
                font-weight: 900;
                font-size: 18px;
            }}
            QLabel#levelCardStartPill {{
                background: rgba(255, 255, 255, 0.92);
                color: rgba(15, 23, 42, 0.74);
                padding: 0px 14px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: 900;
            }}
            QProgressBar#levelCardXpBar {{
                border: none;
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.22);
            }}
            QProgressBar#levelCardXpBar::chunk {{
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.70);
            }}
            QLabel#levelCardXpText {{
                color: rgba(255, 255, 255, 0.92);
                font-weight: 800;
                font-size: 12px;
            }}
            """
        )

    def set_state(self, state: LevelState) -> None:
        task_count = max(1, len(state.level.tasks))
        completed = max(0, min(int(state.completed), task_count))
        self._level_key = state.level.key
        self._unlocked = bool(state.unlocked)
        self._progress = completed / float(task_count)
        self._is_current = bool(state.is_current)
        self._is_completed = completed >= task_count

        title = state.level.name
        if state.level.key == "level0":
            title = f"{title} • தொடக்கம்"
        self._title.setText(title)
        self._progress_text.setText(f"{completed}/{task_count} XP")
        self._xp_bar.setRange(0, task_count)
        self._xp_bar.setValue(completed)

        if self._unlocked and self._is_completed:
            self._lock_badge.setVisible(False)
            self._center.setText("✓")
            self._start_pill.setVisible(False)
            self.setToolTip(f"{title}\nமுடிந்தது: {completed}/{task_count}")
        elif self._unlocked:
            self._lock_badge.setVisible(False)
            self._center.setText(f"{self._progress * 100:.1f}%")
            self._start_pill.setVisible(self._is_current)
            self.setToolTip(f"{title}\nமுன்னேற்றம்: {completed}/{task_count}")
        else:
            self._lock_badge.setVisible(True)
            self._center.setText("🔒")
            self._start_pill.setVisible(False)
            self.setToolTip(f"{title}\nபூட்டப்பட்டது")
        self.update()

    def mousePressEvent(self, event) -> None:
        if self._unlocked and self._level_key:
            self._on_click(self._level_key)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if (not self._unlocked) or self._is_completed:
            return
        # Draw progress ring behind the center label
        r = self._center.geometry()
        size = min(r.width(), r.height())
        pad = max(10, int(size * 0.15))
        ring_rect = QRectF(
            r.x() + pad,
            r.y() + pad,
            max(10, r.width() - 2 * pad),
            max(10, r.height() - 2 * pad),
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # background ring
        bg_pen = QPen(QColor(255, 255, 255, 90))
        bg_pen.setWidth(max(6, int(ring_rect.width() * 0.09)))
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(ring_rect, 90 * 16, -360 * 16)

        # progress arc
        grad = QLinearGradient(ring_rect.topLeft(), ring_rect.bottomRight())
        grad.setColorAt(0.0, QColor(255, 255, 255, 230))
        grad.setColorAt(1.0, QColor(255, 255, 255, 170))
        pen = QPen(QBrush(grad), bg_pen.width())
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(ring_rect, 90 * 16, -int(360 * 16 * self._progress))


class LevelMapWidget(QWidget):
    """A canvas that places LevelCards like a 'journey map' and draws connectors."""

    def __init__(
        self,
        *,
        on_level_clicked: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._on_level_clicked = on_level_clicked
        self._cards: list[LevelCard] = []
        self._states: list[LevelState] = []

        # Palette inspired by the reference screen
        self._palette = ["#19A7D9", "#F5B23B", "#F26A5A", "#F0A93B", "#2FBF93", "#4D79FF"]
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        # Relative positions (x,y) in [0..1] for the first few nodes
        self._positions = [
            (0.14, 0.18),
            (0.50, 0.05),
            (0.80, 0.20),
            (0.55, 0.34),
            (0.30, 0.58),
            (0.70, 0.62),
        ]

    def set_level_states(self, states: list[LevelState]) -> None:
        self._states = states
        while len(self._cards) < len(states):
            idx = len(self._cards)
            card = LevelCard(
                base_color=self._palette[idx % len(self._palette)],
                text_color="#FFFFFF",
                on_click=self._on_level_clicked,
                parent=self,
            )
            self._cards.append(card)

        for i, state in enumerate(states):
            self._cards[i].show()
            self._cards[i].set_state(state)

        for j in range(len(states), len(self._cards)):
            self._cards[j].hide()

        self._relayout_cards()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout_cards()

    def _relayout_cards(self) -> None:
        visible = [c for c in self._cards if c.isVisible()]
        if not visible:
            return
        w = max(1, self.width())
        h = max(1, self.height())

        # A bit smaller + closer to the reference sizing
        card_w = max(170, min(250, int(w * 0.22)))
        card_h = max(160, min(225, int(card_w * 0.84)))

        pad_x = 16
        pad_y = 12

        for i, card in enumerate(visible):
            if i < len(self._positions):
                rx, ry = self._positions[i]
            else:
                # fallback: a gentle grid
                cols = 3
                row = i // cols
                col = i % cols
                rx = 0.12 + col * 0.34
                ry = 0.10 + row * 0.28
            x = int(pad_x + rx * max(1, (w - card_w - 2 * pad_x)))
            y = int(pad_y + ry * max(1, (h - card_h - 2 * pad_y)))
            card.setGeometry(x, y, card_w, card_h)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        visible = [c for c in self._cards if c.isVisible()]
        if len(visible) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(120, 130, 150, 90))
        pen.setWidth(6)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        for a, b in zip(visible, visible[1:]):
            pa = a.geometry().center()
            pb = b.geometry().center()
            start = QPointF(pa.x(), pa.y())
            end = QPointF(pb.x(), pb.y())
            midx = (start.x() + end.x()) / 2.0
            path = QPainterPath(start)
            path.cubicTo(QPointF(midx, start.y()), QPointF(midx, end.y()), end)
            painter.drawPath(path)
