"""Home screen widgets: background, cards, progress bar, stat cards, level row cards."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ezhuthaali.ui.colors import HomeColors


class AspectRatioWidget(QWidget):
    """Widget that maintains a fixed aspect ratio"""
    def __init__(self, aspect_ratio: float = 2.45, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._aspect_ratio = aspect_ratio
        # Use Expanding policy for both to allow proper scaling
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setAspectRatio(self, aspect_ratio: float) -> None:
        """Set the aspect ratio (width/height)"""
        self._aspect_ratio = aspect_ratio
        self.updateGeometry()

    def hasHeightForWidth(self) -> bool:
        """Return True to indicate this widget has height-for-width behavior"""
        return True

    def heightForWidth(self, width: int) -> int:
        """Return the height that maintains aspect ratio for given width"""
        if width > 0:
            return int(width / self._aspect_ratio)
        return 400

    def sizeHint(self) -> QSize:
        """Return a size hint that maintains aspect ratio"""
        # Default size based on aspect ratio
        width = 980
        height = int(width / self._aspect_ratio)
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        """Return minimum size hint"""
        return QSize(980, int(980 / self._aspect_ratio))

    def resizeEvent(self, event) -> None:
        """Override resize to maintain aspect ratio when layout doesn't respect heightForWidth"""
        # Don't constrain height - let the layout handle it via heightForWidth
        # This allows the keyboard to expand and show all text properly
        super().resizeEvent(event)


class CoolBackground(QWidget):
    """Gradient background with subtle decorative shapes (light theme)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(HomeColors.BG_TOP))
        gradient.setColorAt(0.5, QColor(HomeColors.BG_MIDDLE))
        gradient.setColorAt(1.0, QColor(HomeColors.BG_BOTTOM))
        painter.fillRect(self.rect(), gradient)

        painter.setPen(Qt.NoPen)

        # Soft bubble glows
        radial1 = QRadialGradient(self.width() * 0.85, self.height() * 0.15, 220)
        radial1.setColorAt(0, QColor(255, 255, 255, 70))
        radial1.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(radial1)
        painter.drawEllipse(QPoint(int(self.width() * 0.85), int(self.height() * 0.15)), 220, 220)

        radial2 = QRadialGradient(self.width() * 0.12, self.height() * 0.82, 170)
        radial2.setColorAt(0, QColor(255, 255, 255, 55))
        radial2.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(radial2)
        painter.drawEllipse(QPoint(int(self.width() * 0.12), int(self.height() * 0.82)), 170, 170)

        small_circles = [(0.2, 0.3, 90), (0.7, 0.62, 70), (0.9, 0.78, 80), (0.15, 0.62, 60)]
        for x_ratio, y_ratio, radius in small_circles:
            radial = QRadialGradient(self.width() * x_ratio, self.height() * y_ratio, radius)
            radial.setColorAt(0, QColor(255, 255, 255, 40))
            radial.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(radial)
            painter.drawEllipse(QPoint(int(self.width() * x_ratio), int(self.height() * y_ratio)), radius, radius)

        # Very subtle Tamil letters
        painter.setOpacity(0.06)
        font = painter.font()
        font.setPointSize(90)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(HomeColors.PRIMARY_DARK))
        letters = [('அ', 0.08, 0.22), ('இ', 0.86, 0.35), ('உ', 0.14, 0.78), ('எ', 0.78, 0.83), ('ஒ', 0.48, 0.52)]
        for letter, x, y in letters:
            painter.drawText(int(self.width() * x), int(self.height() * y), letter)


class HomeProgressBar(QWidget):
    """Rounded gradient progress bar (ported from `test.py`)."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        track_color: Optional[str] = None,
        show_percentage: bool = False,
        height: int = 10,
    ) -> None:
        super().__init__(parent)
        self._value = 0
        self._max_value = 100
        self._color_start = HomeColors.PRIMARY_LIGHT
        self._color_end = HomeColors.PRIMARY
        self._track_color = track_color  # None = default dark translucent
        self._show_percentage = show_percentage
        self.setFixedHeight(height)
        self.setMinimumWidth(100)

    def set_progress(self, value: int, max_value: int, color_start: Optional[str] = None, color_end: Optional[str] = None) -> None:
        self._value = int(value)
        self._max_value = int(max_value) if int(max_value) > 0 else 1
        if color_start:
            self._color_start = color_start
        if color_end:
            self._color_end = color_end
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Track
        if self._track_color:
            painter.setBrush(QColor(self._track_color))
        else:
            painter.setBrush(QColor(0, 0, 0, 25))
        painter.setPen(Qt.NoPen)
        radius = min(8, self.height() // 2)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), radius, radius)

        progress_width = int((self._value / self._max_value) * self.width()) if self._max_value else 0
        if progress_width > 0:
            gradient = QLinearGradient(0, 0, progress_width, 0)
            gradient.setColorAt(0, QColor(self._color_start))
            gradient.setColorAt(1, QColor(self._color_end))
            painter.setBrush(gradient)
            painter.drawRoundedRect(0, 0, progress_width, self.height(), radius, radius)

            if not self._track_color:
                painter.setBrush(QColor(255, 255, 255, 60))
                painter.drawRoundedRect(0, 0, progress_width, max(2, self.height() // 2), radius, radius)

            # Percentage on fill (e.g. "25%")
            if self._show_percentage and self._max_value > 0:
                pct = round((self._value / self._max_value) * 100)
                painter.setPen(Qt.NoPen)
                painter.setBrush(Qt.NoBrush)
                font = painter.font()
                font.setPointSize(max(9, self.height() - 4))
                font.setWeight(QFont.Weight.DemiBold)
                painter.setFont(font)
                painter.setPen(QColor("#ffffff"))
                text = f"{pct}%"
                text_rect = painter.boundingRect(0, 0, progress_width, self.height(), Qt.AlignCenter, text)
                painter.drawText(text_rect, Qt.AlignCenter, text)


class ProgressCard(QFrame):
    """Progress block matching the glass UI: முன்னேற்றம் label, fraction, rounded bar with % on fill."""

    def __init__(self, parent: Optional[QWidget] = None, *, embedded: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("progressCard")
        if embedded:
            self.setStyleSheet(
                """
                QFrame#progressCard {
                    background: transparent;
                    border: none;
                    border-radius: 0;
                }
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QFrame#progressCard {{
                    background: {HomeColors.PROGRESS_CARD_BG};
                    border: 1px solid rgba(255,255,255,0.7);
                    border-radius: 16px;
                }}
                """
            )
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 60, 80, 28))
            self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self._title_label = QLabel("முன்னேற்றம்")
        self._title_label.setStyleSheet(
            f"color: {HomeColors.PROGRESS_LABEL_MUTED}; font-size: 13px; font-weight: 600;"
        )
        header.addWidget(self._title_label)
        header.addStretch(1)
        self._fraction_label = QLabel("0/0 (0%)")
        self._fraction_label.setStyleSheet(
            f"color: {HomeColors.PROGRESS_LABEL_MUTED}; font-size: 13px; font-weight: 600;"
        )
        header.addWidget(self._fraction_label)
        layout.addLayout(header)

        self._bar = HomeProgressBar(
            self,
            track_color=HomeColors.PROGRESS_TRACK,
            show_percentage=True,
            height=14,
        )
        self._bar.set_progress(0, 1, HomeColors.PROGRESS_FILL, HomeColors.PROGRESS_FILL)
        layout.addWidget(self._bar)
        self._bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_progress(self, current: int, total: int) -> None:
        total = max(1, total)
        self._bar.set_progress(current, total, HomeColors.PROGRESS_FILL, HomeColors.PROGRESS_FILL)
        pct = round((current / total) * 100)
        self._fraction_label.setText(f"{current}/{total} ({pct}%)")

    def setRange(self, min_val: int, max_val: int) -> None:
        self._bar._max_value = max(1, max_val)
        self.set_progress(min_val, self._bar._max_value)

    def setValue(self, value: int) -> None:
        self.set_progress(value, self._bar._max_value)


class GlassCard(QFrame):
    """Glassmorphism card (ported from `test.py`)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setStyleSheet(
            f"""
            QFrame#glassCard {{
                background: {HomeColors.CARD_BG};
                border: 1px solid {HomeColors.CARD_BORDER};
                border-radius: 20px;
            }}
            """
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 50, 70, 40))
        self.setGraphicsEffect(shadow)


class HomeStatCard(QFrame):
    def __init__(self, icon: str, label: str, value: str, bg_color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bg_color = bg_color
        self.setObjectName("homeStatCard")
        self.setStyleSheet(
            f"""
            QFrame#homeStatCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg_color}, stop:1 {QColor(bg_color).darker(112).name()});
                border-radius: 16px;
                border: none;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)
        label_widget = QLabel(f"{icon} {label}")
        label_widget.setStyleSheet("color: rgba(255,255,255,0.92); font-size: 12px; font-weight: 600;")
        layout.addWidget(label_widget)
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet("color: white; font-size: 28px; font-weight: 900;")
        layout.addWidget(self.value_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)

    def set_value(self, value: str) -> None:
        self.value_label.setText(str(value))


class HomeLevelRowCard(QFrame):
    """Clickable row card for one level (ported from `test.py` and wired to real levels)."""

    def __init__(
        self,
        *,
        level_key: str,
        level_id: int,
        title: str,
        icon: str,
        current: int,
        total: int,
        unlocked: bool,
        selected: bool,
        completed: bool,
        on_click: Callable[[str], None],
        on_restart: Optional[Callable[[str], None]] = None,
        on_view: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._level_key = level_key
        self._unlocked = bool(unlocked)
        self._selected = bool(selected)
        self._completed = bool(completed)
        self._on_click = on_click
        self._on_restart = on_restart
        self._on_view = on_view

        self.setCursor(Qt.PointingHandCursor if self._unlocked else Qt.ForbiddenCursor)
        self.setObjectName("homeLevelRowCard")
        self.setFixedHeight(96)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # Icon container
        icon_container = QFrame()
        icon_container.setFixedSize(56, 56)
        icon_container.setObjectName("levelIconBox")
        icon_color = self._progress_color(current, total)
        if self._unlocked:
            icon_container.setStyleSheet(
                f"""
                QFrame#levelIconBox {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {icon_color}, stop:1 {QColor(icon_color).darker(115).name()});
                    border-radius: 16px;
                }}
                """
            )
        else:
            icon_container.setStyleSheet(
                """
                QFrame#levelIconBox {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #cfd8dc, stop:1 #b0bec5);
                    border-radius: 16px;
                }
                """
            )

        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_text = icon if self._unlocked else "🔒"
        icon_label = QLabel(icon_text)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: white; font-size: 24px; font-weight: 900;")
        icon_layout.addWidget(icon_label)

        layout.addWidget(icon_container)

        # Info section
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_color = HomeColors.TEXT_PRIMARY if self._unlocked else HomeColors.TEXT_MUTED
        title_label = QLabel(f"நிலை {level_id} — {title}")
        title_label.setStyleSheet(f"color: {title_color}; font-size: 15px; font-weight: 800;")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        count_label = QLabel(f"{current}/{total}")
        count_label.setStyleSheet(f"color: {icon_color}; font-size: 13px; font-weight: 900;")
        title_row.addWidget(count_label)
        info_layout.addLayout(title_row)

        self._bar = HomeProgressBar()
        self._bar.set_progress(current, max(1, total), QColor(icon_color).lighter(120).name(), icon_color)
        info_layout.addWidget(self._bar)

        percent = self._progress_percent(current, total)
        percent_label = QLabel(f"{percent}% முடிந்தது")
        percent_label.setStyleSheet(f"color: {HomeColors.TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        info_layout.addWidget(percent_label)

        layout.addWidget(info_widget, 1)

        if self._unlocked:
            if self._completed and self._on_restart is not None:
                btn_row = QHBoxLayout()
                btn_row.setSpacing(8)
                icons_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
                icon_sz = 20
                view_icon_path = icons_dir / "icon_view.svg"
                restart_icon_path = icons_dir / "icon_restart.svg"
                view_btn = QPushButton()
                if view_icon_path.exists():
                    view_btn.setIcon(QIcon(str(view_icon_path)))
                view_btn.setIconSize(QSize(icon_sz, icon_sz))
                view_btn.setToolTip("பார்க்க")
                view_btn.setFixedSize(40, 40)
                view_btn.setCursor(Qt.PointingHandCursor)
                view_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {HomeColors.CARD_BG};
                        border: 1px solid {HomeColors.PRIMARY_LIGHT};
                        border-radius: 10px;
                        color: {HomeColors.PRIMARY};
                        padding: 0;
                    }}
                    QPushButton:hover {{ background: rgba(255,255,255,0.95); border-color: {HomeColors.PRIMARY}; }}
                    """
                )
                view_btn.clicked.connect(
                    lambda: (self._on_view(self._level_key) if self._on_view is not None else self._on_click(self._level_key))
                )
                restart_btn = QPushButton()
                if restart_icon_path.exists():
                    restart_btn.setIcon(QIcon(str(restart_icon_path)))
                restart_btn.setIconSize(QSize(icon_sz, icon_sz))
                restart_btn.setToolTip("மீண்டும் தொடங்கு")
                restart_btn.setFixedSize(40, 40)
                restart_btn.setCursor(Qt.PointingHandCursor)
                restart_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 {HomeColors.PRIMARY_LIGHT}, stop:1 {HomeColors.PRIMARY});
                        border: none;
                        border-radius: 10px;
                        color: white;
                        padding: 0;
                    }}
                    QPushButton:hover {{ background: {HomeColors.PRIMARY}; }}
                    """
                )
                restart_btn.clicked.connect(lambda: self._on_restart(self._level_key))
                btn_row.addWidget(view_btn)
                btn_row.addWidget(restart_btn)
                layout.addLayout(btn_row)
            else:
                arrow = QLabel("›")
                arrow.setStyleSheet(f"color: {HomeColors.PRIMARY_LIGHT}; font-size: 28px; font-weight: 900;")
                layout.addWidget(arrow)

        self._apply_style()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 60, 80, 35))
        self.setGraphicsEffect(shadow)

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                f"""
                QFrame#homeLevelRowCard {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255,255,255,0.98), stop:1 rgba(224,247,250,0.95));
                    border: 2px solid {HomeColors.PRIMARY};
                    border-radius: 18px;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QFrame#homeLevelRowCard {{
                    background: {HomeColors.CARD_BG};
                    border: 1px solid rgba(255,255,255,0.5);
                    border-radius: 18px;
                }}
                """
            )
        if not self._unlocked:
            self.setStyleSheet(self.styleSheet() + "QFrame#homeLevelRowCard { opacity: 0.65; }")

    @staticmethod
    def _progress_percent(current: int, total: int) -> int:
        if total <= 0:
            return 0
        return round((current / total) * 100)

    @staticmethod
    def _progress_color(current: int, total: int) -> str:
        if total <= 0:
            return HomeColors.TEXT_MUTED
        percent = (current / total) * 100
        if percent == 0:
            return "#90a4ae"
        if percent < 30:
            return HomeColors.CORAL
        if percent < 70:
            return HomeColors.AMBER
        return HomeColors.MINT

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_style()

    def enterEvent(self, event) -> None:
        if self._unlocked and not self._selected:
            self.setStyleSheet(
                f"""
                QFrame#homeLevelRowCard {{
                    background: {HomeColors.CARD_BG_HOVER};
                    border: 1px solid {HomeColors.PRIMARY_LIGHT};
                    border-radius: 18px;
                }}
                """
            )
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._unlocked and not self._completed:
            self._on_click(self._level_key)
        super().mousePressEvent(event)
