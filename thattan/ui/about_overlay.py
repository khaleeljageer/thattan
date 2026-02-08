"""In-window About overlay widget."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize, QEvent, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon
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

# Palette used by the overlay (avoids circular import from main_window)
_PRIMARY = "#00838f"
_PRIMARY_LIGHT = "#4fb3bf"


class AboutOverlay(QWidget):
    """In-window overlay for About — stays inside the main window and is clipped to it."""

    closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setRowStretch(0, 1)
        main_layout.setColumnStretch(0, 1)

        overlay_bg = QWidget(self)
        overlay_bg.setStyleSheet("background: rgba(0, 0, 0, 0.2);")
        overlay_bg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        overlay_bg.setCursor(Qt.CursorShape.ArrowCursor)
        overlay_bg.setMinimumSize(1, 1)

        def on_overlay_click(_e) -> None:
            self.hide()
            self.closed.emit()

        overlay_bg.mousePressEvent = on_overlay_click
        main_layout.addWidget(overlay_bg, 0, 0)

        radius = 24
        container = QFrame(self)
        container.setObjectName("aboutContainer")
        container.setMinimumWidth(680)
        container.setMaximumWidth(920)
        container.setStyleSheet(
            f"""
            QFrame#aboutContainer {{
                background: #ffffff;
                border-radius: {radius}px;
            }}
            """
        )
        container_shadow = QGraphicsDropShadowEffect(container)
        container_shadow.setBlurRadius(24)
        container_shadow.setOffset(0, 8)
        container_shadow.setColor(QColor(0, 80, 100, 25))
        container.setGraphicsEffect(container_shadow)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # ---- Left panel: branding (teal gradient) ----
        left_panel = QFrame()
        left_panel.setObjectName("aboutLeftPanel")
        left_panel.setFixedWidth(240)
        left_panel.setStyleSheet(
            f"""
            QFrame#aboutLeftPanel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {_PRIMARY_LIGHT}, stop:1 {_PRIMARY});
                border-top-left-radius: {radius}px;
                border-bottom-left-radius: {radius}px;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
            }}
            """
        )
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(32, 40, 32, 40)
        left_layout.setSpacing(16)

        icon_box = QFrame()
        icon_box.setFixedSize(80, 80)
        icon_box.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: none;
                border-radius: 24px;
            }
            """
        )
        icon_layout = QVBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        _assets_dir = Path(__file__).resolve().parent.parent / "assets"
        logo_path = _assets_dir / "logo" / "logo.svg"
        if not logo_path.exists():
            logo_path = _assets_dir / "logo" / "logo_256.png"
        icon_label = QLabel()
        if logo_path.exists():
            icon_label.setPixmap(QIcon(str(logo_path)).pixmap(QSize(80, 80)))
        else:
            icon_label.setText("த")
            icon_label.setStyleSheet(f"color: {_PRIMARY}; font-size: 40px; font-weight: 900;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        left_layout.addWidget(icon_box, 0, Qt.AlignCenter)

        title_ta = QLabel("தட்டான்")
        title_ta.setStyleSheet("color: white; font-size: 28px; font-weight: 800;")
        title_ta.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_ta, 0, Qt.AlignCenter)

        title_en = QLabel("THATTAN")
        title_en.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 11px; font-weight: 500; letter-spacing: 3px;")
        title_en.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_en, 0, Qt.AlignCenter)

        version_pill = QLabel("V1.0.0")
        version_pill.setStyleSheet(
            "color: white; font-size: 12px; font-weight: 700;"
        )
        version_pill.setAlignment(Qt.AlignCenter)
        version_pill.setFixedHeight(28)
        left_layout.addWidget(version_pill, 0, Qt.AlignCenter)

        tagline = QLabel("செம்மொழித் தமிழ் கற்போம்")
        tagline.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 12px; font-weight: 500;")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setWordWrap(True)
        left_layout.addWidget(tagline, 0, Qt.AlignCenter)

        left_layout.addStretch(1)
        container_layout.addWidget(left_panel)

        # ---- Right panel: content (white background) ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(28, 28, 28, 28)
        right_layout.setSpacing(12)

        # Single info card: Author, Organization, Email (no internal dividers)
        info_section = QFrame()
        info_section.setObjectName("aboutInfoCard")
        info_section.setStyleSheet(
            """
            QFrame#aboutInfoCard {
                background: #ffffff;
                border: 1px solid rgba(0, 131, 143, 0.12);
                border-radius: 16px;
            }
            """
        )
        info_inner = QVBoxLayout(info_section)
        info_inner.setContentsMargins(20, 18, 20, 18)
        info_inner.setSpacing(20)

        def _info_row(icon_char: str, label: str, value: str, is_link: bool = False, url: str = "") -> QWidget:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(14)
            icon_frame = QFrame()
            icon_frame.setFixedSize(40, 40)
            icon_frame.setStyleSheet(
                """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #e0f7fa, stop:1 #b2ebf2);
                    border-radius: 12px;
                }
                """
            )
            icon_lo = QVBoxLayout(icon_frame)
            icon_lo.setContentsMargins(0, 0, 0, 0)
            ic = QLabel(icon_char)
            ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet(f"color: {_PRIMARY}; font-size: 18px;")
            icon_lo.addWidget(ic)
            row_layout.addWidget(icon_frame, 0)
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #90a4ae; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
            col.addWidget(lbl)
            if is_link and url:
                val = QLabel(f'<a href="{url}">{value}</a>')
                val.setOpenExternalLinks(True)
                val.setTextFormat(Qt.TextFormat.RichText)
                val.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {_PRIMARY};")
            else:
                val = QLabel(value)
                val.setStyleSheet("color: #1a3a3a; font-size: 14px; font-weight: 600;")
            col.addWidget(val)
            row_layout.addLayout(col, 1)
            return row

        def _separator() -> QWidget:
            wrap = QWidget()
            wrap_layout = QHBoxLayout(wrap)
            wrap_layout.setContentsMargins(0, 0, 0, 0)
            wrap_layout.setSpacing(0)
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet("background: rgba(0, 131, 143, 0.25); border: none;")
            line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            wrap_layout.addWidget(line)
            return wrap

        info_inner.addWidget(_info_row("👤", "AUTHOR", "Khaleel Jageer"))
        info_inner.addWidget(_separator())
        info_inner.addWidget(_info_row("🏢", "ORGANIZATION", "Kaniyam Foundation", True, "https://www.kaniyam.com"))
        info_inner.addWidget(_separator())
        info_inner.addWidget(_info_row("📧", "EMAIL", "jskcse4@gmail.com"))
        right_layout.addWidget(info_section)

        # GitHub & Website: light buttons with light grey border
        link_row = QHBoxLayout()
        link_row.setSpacing(10)
        for text, url, symbol in [
            ("GitHub", "https://github.com/khaleeljageer/thattan", "💻"),
            ("Website", "https://www.kaniyam.com", "🌐"),
        ]:
            card = QPushButton(f"  {symbol}  {text}")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet(
                """
                QPushButton {
                    background: #fafafa;
                    color: #1a3a3a;
                    padding: 12px 16px;
                    border: 1px solid #e0e0e0;
                    border-radius: 14px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #f0f0f0;
                    border-color: #00838f;
                    color: #00838f;
                }
                """
            )
            card.setMinimumHeight(48)
            card.clicked.connect(lambda checked=False, _u=url: QDesktopServices.openUrl(QUrl(_u)))
            link_row.addWidget(card, 1)
        right_layout.addLayout(link_row)

        # License and Built with (centered, light grey text)
        license_section = QWidget()
        footer_line = QHBoxLayout(license_section)
        footer_line.setContentsMargins(0, 8, 0, 8)
        footer_line.setSpacing(24)
        license_lbl = QLabel('<b>📜 License:</b> <a href="https://www.gnu.org/licenses/gpl-3.0.en.html">GPL v3</a>')
        license_lbl.setOpenExternalLinks(True)
        license_lbl.setTextFormat(Qt.TextFormat.RichText)
        license_lbl.setStyleSheet("color: #78909c; font-size: 12px;")
        footer_line.addWidget(license_lbl, 0)
        footer_line.addStretch(1)
        built_lbl = QLabel("<b>🛠️ Built with:</b> Python + PySide6")
        built_lbl.setStyleSheet("color: #78909c; font-size: 12px;")
        footer_line.addWidget(built_lbl, 0)
        right_layout.addWidget(license_section)

        # Buttons: Report Issue (left), Close (right)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        report_issue_url = "https://github.com/khaleeljageer/thattan/issues/new"
        bug_icon_path = _assets_dir / "icons" / "icon_bug.svg"
        report_btn = QPushButton("Report Issue")
        if bug_icon_path.exists():
            report_btn.setIcon(QIcon(str(bug_icon_path)))
        report_btn.setIconSize(QSize(18, 18))
        report_btn.setStyleSheet(
            """
            QPushButton {
                background: #fafafa;
                color: #1a3a3a;
                padding: 12px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 14px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-color: #00838f;
                color: #00838f;
            }
            """
        )
        report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        report_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        report_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(report_issue_url)))
        btn_row.addWidget(report_btn, 1)

        close_btn = QPushButton("மூடு")
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {_PRIMARY_LIGHT}, stop:1 {_PRIMARY});
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 14px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {_PRIMARY}; }}
            """
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        close_btn.clicked.connect(lambda: (self.hide(), self.closed.emit()))
        btn_row.addWidget(close_btn, 1)

        right_layout.addLayout(btn_row)
        container_layout.addWidget(right_panel, 1)
        main_layout.addWidget(container, 0, 0, 1, 1, Qt.AlignCenter)

    def _update_geometry(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

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
