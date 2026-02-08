"""Custom in-window overlays (reset confirm, level completed)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QSize, QEvent, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_PRIMARY = "#00838f"
_PRIMARY_LIGHT = "#4fb3bf"


def _themed_card_container(radius: int = 20, object_name: str = "overlayContainer") -> QFrame:
    container = QFrame()
    container.setObjectName(object_name)
    container.setMinimumWidth(400)
    container.setMaximumWidth(480)
    container.setStyleSheet(
        f"""
        QFrame#{object_name} {{
            background: #ffffff;
            border: 1px solid rgba(0, 131, 143, 0.12);
            border-radius: {radius}px;
        }}
        """
    )
    shadow = QGraphicsDropShadowEffect(container)
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(0, 80, 100, 25))
    container.setGraphicsEffect(shadow)
    return container


def _overlay_background(parent: QWidget, on_click: Callable[[], None]) -> QWidget:
    overlay_bg = QWidget(parent)
    overlay_bg.setStyleSheet("background: rgba(0, 0, 0, 0.2);")
    overlay_bg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    overlay_bg.setCursor(Qt.CursorShape.ArrowCursor)
    overlay_bg.setMinimumSize(1, 1)
    overlay_bg.mousePressEvent = lambda e: on_click()
    return overlay_bg


def _secondary_button_style() -> str:
    return """
        QPushButton {
            background: #fafafa;
            color: #1a3a3a;
            padding: 10px 16px;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            font-weight: 600;
            font-size: 13px;
        }
        QPushButton:hover {
            background: #f0f0f0;
            border-color: #00838f;
            color: #00838f;
        }
    """


def _primary_button_style() -> str:
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {_PRIMARY_LIGHT}, stop:1 {_PRIMARY});
            color: white;
            padding: 10px 16px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton:hover {{ background: {_PRIMARY}; }}
    """


class ResetConfirmOverlay(QWidget):
    """In-window overlay to confirm reset progress."""

    closed = Signal(bool)  # True if user confirmed reset

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setRowStretch(0, 1)
        main_layout.setColumnStretch(0, 1)

        overlay_bg = _overlay_background(self, lambda: (self.hide(), self.closed.emit(False)))
        main_layout.addWidget(overlay_bg, 0, 0)

        container = _themed_card_container(object_name="resetContainer")
        content = QVBoxLayout(container)
        content.setContentsMargins(28, 24, 28, 24)
        content.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(12)
        _assets_dir = Path(__file__).resolve().parent.parent / "assets"
        icon_box = QFrame()
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e0f7fa, stop:1 #b2ebf2);
                border-radius: 12px;
            }
            """
        )
        icon_layout = QVBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        restart_icon_path = _assets_dir / "icons" / "icon_restart.svg"
        icon_label = QLabel()
        if restart_icon_path.exists():
            icon_label.setPixmap(QIcon(str(restart_icon_path)).pixmap(QSize(28, 28)))
        else:
            icon_label.setText("↻")
            icon_label.setStyleSheet(f"color: {_PRIMARY}; font-size: 22px; font-weight: 900;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        header.addWidget(icon_box, 0)

        title = QLabel("மீட்டமை")
        title.setStyleSheet(f"color: {_PRIMARY}; font-size: 18px; font-weight: 800;")
        header.addWidget(title, 0)
        header.addStretch(1)
        content.addLayout(header)

        msg = QLabel("அனைத்து முன்னேற்றத்தையும் மீட்டமைக்க வேண்டுமா?")
        msg.setStyleSheet("color: #1a3a3a; font-size: 14px; font-weight: 500;")
        msg.setWordWrap(True)
        content.addWidget(msg, 0)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("மூடு")
        cancel_btn.setStyleSheet(_secondary_button_style())
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cancel_btn.clicked.connect(lambda: (self.hide(), self.closed.emit(False)))
        btn_row.addWidget(cancel_btn, 1)

        confirm_btn = QPushButton("மீட்டமை")
        confirm_btn.setStyleSheet(_primary_button_style())
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        confirm_btn.clicked.connect(lambda: (self.hide(), self.closed.emit(True)))
        btn_row.addWidget(confirm_btn, 1)

        content.addLayout(btn_row)
        main_layout.addWidget(container, 0, 0, 1, 1, Qt.AlignCenter)
        self._add_overlay_geometry_behavior()

    def _add_overlay_geometry_behavior(self) -> None:
        def _update_geometry() -> None:
            parent = self.parentWidget()
            if parent is not None:
                self.setGeometry(parent.rect())

        self._update_geometry = _update_geometry

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_geometry()

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._update_geometry()
        return super().eventFilter(obj, event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_geometry()
        parent = self.parentWidget()
        if parent is not None:
            parent.installEventFilter(self)

    def hideEvent(self, event) -> None:
        parent = self.parentWidget()
        if parent is not None:
            parent.removeEventFilter(self)
        super().hideEvent(event)


class LevelCompletedOverlay(QWidget):
    """In-window overlay shown when user completes a level."""

    closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setRowStretch(0, 1)
        main_layout.setColumnStretch(0, 1)

        overlay_bg = _overlay_background(self, lambda: (self.hide(), self.closed.emit()))
        main_layout.addWidget(overlay_bg, 0, 0)

        container = _themed_card_container(object_name="levelCompletedContainer")
        content = QVBoxLayout(container)
        content.setContentsMargins(28, 24, 28, 24)
        content.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(12)
        icon_box = QFrame()
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e0f7fa, stop:1 #b2ebf2);
                border-radius: 12px;
            }
            """
        )
        icon_layout = QVBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel("✓")
        icon_label.setStyleSheet(f"color: {_PRIMARY}; font-size: 24px; font-weight: 900;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        header.addWidget(icon_box, 0)

        title = QLabel("நிலை முடிந்தது")
        title.setStyleSheet(f"color: {_PRIMARY}; font-size: 18px; font-weight: 800;")
        header.addWidget(title, 0)
        header.addStretch(1)
        content.addLayout(header)

        msg = QLabel("இந்த நிலையை நீங்கள் முடித்துவிட்டீர்கள்!")
        msg.setStyleSheet("color: #1a3a3a; font-size: 14px; font-weight: 500;")
        msg.setWordWrap(True)
        content.addWidget(msg, 0)

        ok_btn = QPushButton("சரி")
        ok_btn.setStyleSheet(_primary_button_style())
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ok_btn.clicked.connect(lambda: (self.hide(), self.closed.emit()))
        content.addWidget(ok_btn, 0)

        main_layout.addWidget(container, 0, 0, 1, 1, Qt.AlignCenter)
        self._add_overlay_geometry_behavior()

    def _add_overlay_geometry_behavior(self) -> None:
        def _update_geometry() -> None:
            parent = self.parentWidget()
            if parent is not None:
                self.setGeometry(parent.rect())

        self._update_geometry = _update_geometry

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_geometry()

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._update_geometry()
        return super().eventFilter(obj, event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_geometry()
        parent = self.parentWidget()
        if parent is not None:
            parent.installEventFilter(self)

    def hideEvent(self, event) -> None:
        parent = self.parentWidget()
        if parent is not None:
            parent.removeEventFilter(self)
        super().hideEvent(event)
