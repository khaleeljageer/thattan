from __future__ import annotations

import html
import re
import os
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEventLoop
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QKeyEvent,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
    QMainWindow,
    QPushButton,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from thattan.core.levels import LevelRepository, Level
from thattan.core.progress import ProgressStore
from thattan.core.session import TypingSession, TaskResult
from thattan.core.keystroke_tracker import KeystrokeTracker, Tamil99KeyboardLayout
from thattan.ui.about_overlay import AboutOverlay
from thattan.ui.colors import HomeColors
from thattan.ui.custom_overlay import ResetConfirmOverlay, LevelCompletedOverlay
from thattan.ui.home_widgets import (
    CoolBackground,
    GlassCard,
    HomeLevelRowCard,
    HomeProgressBar,
    HomeStatCard,
    ProgressCard,
)
from thattan.ui.models import LevelState
from thattan.ui.typing_widgets import HeroLetterLabel, LetterSequenceWidget


class MainWindow(QMainWindow):
    """Main application window managing home screen, typing practice, and keyboard UI.

    Provides a two-screen layout: a home screen with level selection and progress
    stats, and a typing screen with real-time keystroke tracking against the
    Tamil99 keyboard layout.
    """

    def __init__(self, levels: LevelRepository, progress_store: ProgressStore) -> None:
        super().__init__()
        self._levels_repo = levels
        self._progress_store = progress_store
        self._session: Optional[TypingSession] = None
        self._current_level: Optional[Level] = None
        self._auto_submit_block = False
        self._highlighted_keys: list[QLabel] = []
        self._key_labels: dict[str, QLabel] = {}
        self._shift_labels: list[QLabel] = []
        self._left_shift_label: Optional[QLabel] = None
        self._right_shift_label: Optional[QLabel] = None
        self._current_task_text: str = ""
        self._unlock_all_levels = os.environ.get("THATTAN_UNLOCK_ALL") == "1"
        self._input_has_error = False

        ts, cs, bs = self._progress_store.get_gamification()
        self._total_score: int = ts
        self._current_streak: int = cs
        self._best_streak: int = bs
        self._combo_multiplier: float = 1.0
        self._consecutive_correct: int = 0
        self._view_only_session: bool = False

        self._keystroke_tracker = KeystrokeTracker()
        self._tamil99_layout = Tamil99KeyboardLayout()
        self._keycaps_map, _ = self._load_tamil99_maps()
        self._keystroke_sequence: list[tuple[str, bool]] = []
        self._keystroke_index: int = 0
        self._typed_keystrokes: list[str] = []
        self._typed_tamil_text: str = ""

        self._keyboard_widget: Optional[QWidget] = None
        self._hands_image_label: Optional[QLabel] = None
        self._original_hands_pixmap: Optional[QPixmap] = None
        self._bottom_container: Optional[QWidget] = None
        self._keyboard_font_sizes: dict[str, int] = {}
        self._finger_guidance_label: Optional[QLabel] = None
        self._key_base_style_by_label: dict[QLabel, str] = {}

        self._stack: Optional[QStackedWidget] = None
        self._home_screen: Optional[QWidget] = None
        self._typing_screen: Optional[QWidget] = None
        self._back_button: Optional[QPushButton] = None
        self._typing_title_label: Optional[QLabel] = None

        self._letter_sequence_widget: Optional[LetterSequenceWidget] = None
        self._hero_letter_label: Optional[HeroLetterLabel] = None
        self._typing_time_label: Optional[QLabel] = None
        self._typing_wpm_label: Optional[QLabel] = None
        self._typing_cpm_label: Optional[QLabel] = None
        self._typing_accuracy_bar: Optional[HomeProgressBar] = None
        self._typing_accuracy_value: Optional[QLabel] = None
        self._typing_streak_label: Optional[QLabel] = None
        self._typing_best_streak_label: Optional[QLabel] = None
        self._typing_correct_label: Optional[QLabel] = None
        self._typing_wrong_label: Optional[QLabel] = None
        self._typing_stats_timer: Optional[QTimer] = None
        self._typing_stats_panel: Optional[GlassCard] = None
        self._typing_practice_card: Optional[GlassCard] = None
        self._typing_header: Optional[QWidget] = None
        self._typing_feedback_label: Optional[QLabel] = None
        self._level_pill: Optional[QFrame] = None
        self._stat_time_header: Optional[QLabel] = None
        self._stat_wpm_header: Optional[QLabel] = None
        self._stat_wpm_sub: Optional[QLabel] = None
        self._stat_cpm_header: Optional[QLabel] = None
        self._stat_cpm_sub: Optional[QLabel] = None
        self._stat_acc_header: Optional[QLabel] = None
        self._stat_streak_header: Optional[QLabel] = None
        self._stat_correct_sub: Optional[QLabel] = None
        self._stat_wrong_sub: Optional[QLabel] = None

        self._points_card: Optional[HomeStatCard] = None
        self._streak_card: Optional[HomeStatCard] = None
        self._best_streak_card: Optional[HomeStatCard] = None
        self._accuracy_bar: Optional[HomeProgressBar] = None
        self._accuracy_value_label: Optional[QLabel] = None
        self._levels_summary_label: Optional[QLabel] = None
        self._levels_scroll: Optional[QScrollArea] = None
        self._levels_list_container: Optional[QWidget] = None
        self._home_levels_layout: Optional[QVBoxLayout] = None

        self._error_overlay: Optional[QWidget] = None
        self._error_overlay_effect: Optional[QGraphicsOpacityEffect] = None
        self._error_overlay_anim: Optional[QPropertyAnimation] = None

        self._key_to_finger = self._build_finger_mapping()

        self._build_ui()
        self._refresh_levels_list()
        QTimer.singleShot(0, self.showMaximized)

    
    def _build_finger_mapping(self) -> dict[str, tuple[str, str]]:
        """Build mapping from QWERTY key name to ``(hand, finger)`` tuple.

        The mapping follows standard touch-typing finger assignments.
        """
        mapping: dict[str, tuple[str, str]] = {}

        for key in ['`', '1', 'Q', 'A', 'Z', 'TAB', 'CAPS']:
            mapping[key.upper()] = ('left', 'pinky')
        mapping['SHIFT'] = ('left', 'pinky')

        for key in ['2', 'W', 'S', 'X']:
            mapping[key.upper()] = ('left', 'ring')
        for key in ['3', 'E', 'D', 'C']:
            mapping[key.upper()] = ('left', 'middle')
        for key in ['4', '5', 'R', 'T', 'F', 'G', 'V', 'B']:
            mapping[key.upper()] = ('left', 'index')

        mapping['SPACE'] = ('left', 'thumb')
        mapping[' '] = ('left', 'thumb')

        for key in ['6', '7', 'Y', 'U', 'H', 'J', 'N', 'M']:
            mapping[key.upper()] = ('right', 'index')
        for key in ['8', 'I', 'K', ',']:
            mapping[key.upper()] = ('right', 'middle')
        for key in ['9', 'O', 'L', '.']:
            mapping[key.upper()] = ('right', 'ring')
        for key in ['0', '-', '=', 'P', '[', ']', '\\', ';', "'", '/', 'ENTER', 'BACKSPACE']:
            mapping[key.upper()] = ('right', 'pinky')

        # Override SHIFT to right pinky (default when side is unknown)
        mapping['SHIFT'] = ('right', 'pinky')
        mapping['CTRL'] = ('left', 'pinky')
        mapping['ALT'] = ('left', 'thumb')

        return mapping
    
    def _get_finger_name(self, key_label: str, needs_shift: bool = False) -> tuple[str, str]:
        """Return ``(english_name, tamil_name)`` describing which finger to use.

        When *needs_shift* is True the opposite-hand Shift pinky is returned
        (standard touch-typing rule: left-hand key → right Shift and vice-versa).
        """
        if key_label.upper() == 'SHIFT':
            hand, finger = self._key_to_finger.get('SHIFT', ('right', 'pinky'))
        elif needs_shift:
            key_hand, _key_finger = self._key_to_finger.get(key_label.upper(), ('right', 'index'))
            shift_hand = 'right' if key_hand == 'left' else 'left'
            hand, finger = (shift_hand, 'pinky')
        else:
            hand, finger = self._key_to_finger.get(key_label.upper(), ('right', 'index'))

        finger_names_tamil = {
            'thumb': 'கட்டைவிரல்',
            'index': 'சுட்டுவிரல்',
            'middle': 'நடுவிரல்',
            'ring': 'மோதிரவிரல்',
            'pinky': 'சிறுவிரல்'
        }
        
        hand_names_tamil = {
            'left': 'இடது',
            'right': 'வலது'
        }
        
        english_name = f"{hand.capitalize()} {finger.capitalize()}"
        tamil_name = f"{hand_names_tamil.get(hand, hand)} {finger_names_tamil.get(finger, finger)}"
        
        return (english_name, tamil_name)

    def _shift_side_for_key(self, key_label: str) -> str:
        """Return ``'left'`` or ``'right'`` indicating which Shift to press for *key_label*."""
        key_hand, _ = self._key_to_finger.get(key_label.upper(), ('right', 'index'))
        return 'right' if key_hand == 'left' else 'left'

    def _get_theme_colors(self) -> dict:
        """Return the light-theme color palette used across all UI elements."""
        return {
            'bg_main': '#EEF6F6',
            'bg_container': 'rgba(255, 255, 255, 0.34)',
            'bg_card': 'rgba(255, 255, 255, 0.24)',
            'bg_input': 'rgba(255, 255, 255, 0.38)',
            'bg_hover': 'rgba(255, 255, 255, 0.46)',
            'text_primary': '#1F2933',
            'text_secondary': '#334155',
            'text_muted': '#64748B',
            'border': 'rgba(15, 23, 42, 0.14)',
            'border_light': 'rgba(15, 23, 42, 0.10)',
            'highlight': '#0F766E',
            'highlight_bg': 'rgba(15, 118, 110, 0.18)',
            'error': '#D64545',
            'error_bg': 'rgba(214, 69, 69, 0.18)',
            'success': '#2F855A',
            'success_bg': 'rgba(47, 133, 90, 0.18)',
            'progress': '#0F766E',
            'key_bg': 'rgba(255, 255, 255, 0.22)',
            'key_highlight': '#0F766E',
            'key_highlight_bg': 'rgba(15, 118, 110, 0.18)',
            'key_shift': '#0F766E',
            'key_shift_bg': 'rgba(15, 118, 110, 0.18)',
        }

    def _get_finger_colors(self) -> dict[tuple[str, str], str]:
        """Return mapping of ``(hand, finger)`` to hex colour for keyboard tinting."""
        return {
            ('left', 'pinky'): '#5C96EB',
            ('left', 'ring'): '#EF6060',
            ('left', 'middle'): '#2ECC71',
            ('left', 'index'): '#7A5CEB',
            ('left', 'thumb'): '#EB78D2',
            ('right', 'pinky'): '#5C96EB',
            ('right', 'ring'): '#EF6060',
            ('right', 'middle'): '#2ECC71',
            ('right', 'index'): '#FF953D',
            ('right', 'thumb'): '#EB78D2',
        }

    def _darken_hex_color(self, hex_color: str, factor: float) -> str:
        """Darken a ``#RRGGBB`` colour by multiplying each channel by *factor* (0–1)."""
        try:
            c = hex_color.strip()
            if not c.startswith("#"):
                return hex_color
            if len(c) != 7:
                return hex_color
            factor = max(0.0, min(1.0, factor))
            r = int(c[1:3], 16)
            g = int(c[3:5], 16)
            b = int(c[5:7], 16)
            r = max(0, min(255, int(r * factor)))
            g = max(0, min(255, int(g * factor)))
            b = max(0, min(255, int(b * factor)))
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    def _blend_hex_colors(self, a: str, b: str, t: float) -> str:
        """Linearly interpolate two ``#RRGGBB`` colours; *t* = 0 yields *a*, *t* = 1 yields *b*."""
        try:
            a = a.strip()
            b = b.strip()
            if not (a.startswith("#") and b.startswith("#") and len(a) == 7 and len(b) == 7):
                return a
            t = max(0.0, min(1.0, float(t)))
            ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
            br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
            r = int(ar + (br - ar) * t)
            g = int(ag + (bg - ag) * t)
            bl = int(ab + (bb - ab) * t)
            return f"#{r:02X}{g:02X}{bl:02X}"
        except Exception:
            return a

    def _finger_color_for_key(self, key_label: str) -> str:
        """Return the finger-zone background colour for *key_label*."""
        hand, finger = self._key_to_finger.get(key_label.upper(), ('right', 'index'))
        return self._get_finger_colors().get((hand, finger), '#5C96EB')

    def _muted_key_fill_color_for_key(self, key_label: str) -> str:
        """Return a pastel version of the finger colour blended towards the background."""
        colors = self._get_theme_colors()
        base = self._finger_color_for_key(key_label)
        return self._blend_hex_colors(base, colors['bg_main'], 0.62)

    def _highlight_border_color_for_key(self, key_label: str) -> str:
        """Return a darkened finger-zone colour used as the highlight border."""
        base = self._finger_color_for_key(key_label)
        return self._darken_hex_color(base, 0.45)

    def _build_key_style(
        self,
        key_label: str,
        font_px: int,
        *,
        border_px: int = 4,
        border_color: str = "transparent",
        font_weight: int = 500,
    ) -> str:
        """Generate a ``QLabel`` stylesheet for a single keyboard key."""
        colors = self._get_theme_colors()
        bg = self._muted_key_fill_color_for_key(key_label)
        border = f"{border_px}px solid {border_color}" if border_px > 0 else "none"
        return f"""
            QLabel {{
                background: {bg};
                color: {colors['text_primary']};
                border: {border};
                border-radius: 6px;
                padding: 12px 8px;
                font-family: '{QApplication.font().family()}', sans-serif;
                font-size: {font_px}px;
                font-weight: {font_weight};
            }}
        """

    def _build_ui(self) -> None:
        """Construct the entire widget tree: home screen, typing screen, and overlays."""
        self.setWindowTitle("தட்டான் - தமிழ்99 பயிற்சி")
        self.setMinimumSize(1200, 800)

        colors = self._get_theme_colors()

        self.setStyleSheet(f"""
            QMainWindow {{ 
                background: {colors['bg_main']};
            }}
        """)

        self._error_overlay = QWidget(self)
        self._error_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._error_overlay.setStyleSheet("background-color: #EF6060;")
        self._error_overlay_effect = QGraphicsOpacityEffect(self._error_overlay)
        self._error_overlay_effect.setOpacity(0.0)
        self._error_overlay.setGraphicsEffect(self._error_overlay_effect)
        self._error_overlay.hide()
        self._error_overlay_anim = QPropertyAnimation(self._error_overlay_effect, b"opacity", self)
        self._error_overlay_anim.setDuration(200)
        self._error_overlay_anim.setKeyValueAt(0.0, 0.0)
        self._error_overlay_anim.setKeyValueAt(0.2, 0.28)
        self._error_overlay_anim.setKeyValueAt(1.0, 0.0)
        self._error_overlay_anim.finished.connect(self._error_overlay.hide)

        self._stack = QStackedWidget()
        self._home_screen = CoolBackground()
        self._typing_screen = CoolBackground()
        self._stack.addWidget(self._home_screen)
        self._stack.addWidget(self._typing_screen)
        self.setCentralWidget(self._stack)

        self._about_overlay = AboutOverlay(self._stack)
        self._about_overlay.hide()
        self._reset_overlay = ResetConfirmOverlay(self._stack)
        self._reset_overlay.hide()
        self._level_completed_overlay = LevelCompletedOverlay(self._stack)
        self._level_completed_overlay.hide()

        home_layout = QVBoxLayout(self._home_screen)
        home_layout.setContentsMargins(16, 16, 16, 16)
        home_layout.setSpacing(20)

        header = GlassCard()
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(16, 16, 16, 16)
        header_row.setSpacing(18)

        logo = QFrame()
        logo.setFixedSize(60, 60)
        logo.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: none;
                border-radius: 15px;
            }
            """
        )
        logo_shadow = QGraphicsDropShadowEffect(logo)
        logo_shadow.setBlurRadius(20)
        logo_shadow.setOffset(0, 5)
        logo_shadow.setColor(QColor(HomeColors.PRIMARY_DARK))
        logo.setGraphicsEffect(logo_shadow)
        logo_layout = QVBoxLayout(logo)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo" / "logo.svg"
        if not logo_path.exists():
            logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo" / "logo_256.png"
        logo_label = QLabel()
        if logo_path.exists():
            logo_label.setPixmap(QIcon(str(logo_path)).pixmap(QSize(60, 60)))
        else:
            logo_label.setText("த")
            logo_label.setStyleSheet("color: white; font-size: 32px; font-weight: 900;")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(logo_label)
        header_row.addWidget(logo, 0)

        title_widget = QWidget()
        title_col = QVBoxLayout(title_widget)
        title_col.setContentsMargins(8, 0, 0, 0)
        title_col.setSpacing(2)
        title = QLabel("தமிழ் தட்டச்சு பயிற்சி")
        title.setStyleSheet(f"color: {HomeColors.PRIMARY}; font-size: 28px; font-weight: 900;")
        subtitle = QLabel("TAMIL TYPING TUTOR")
        subtitle.setStyleSheet(f"color: {HomeColors.TEXT_SECONDARY}; font-size: 12px; letter-spacing: 4px; font-weight: 600;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_row.addWidget(title_widget, 1)
        header_row.addStretch(1)
        deco = QLabel("⌨️")
        deco.setStyleSheet("font-size: 34px;")
        header_row.addWidget(deco, 0, Qt.AlignRight)
        home_layout.addWidget(header, 0)

        content_row = QHBoxLayout()
        content_row.setSpacing(28)

        stats_panel = GlassCard()
        stats_panel.setFixedWidth(320)
        stats_layout = QVBoxLayout(stats_panel)
        stats_layout.setContentsMargins(22, 22, 22, 22)
        stats_layout.setSpacing(16)

        stats_title = QLabel("📊 முன்னேற்றம்")
        stats_title.setStyleSheet(f"color: {HomeColors.TEXT_PRIMARY}; font-size: 16px; font-weight: 900;")
        stats_layout.addWidget(stats_title, 0)

        self._points_card = HomeStatCard("🏆", "புள்ளிகள்", "0", HomeColors.PRIMARY_LIGHT)
        stats_layout.addWidget(self._points_card)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._streak_card = HomeStatCard("🔥", "தொடர்ச்சி", "0", HomeColors.CORAL)
        self._best_streak_card = HomeStatCard("⭐", "சிறந்தது", "0", HomeColors.LAVENDER)
        self._streak_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._best_streak_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stats_row.addWidget(self._streak_card)
        stats_row.addWidget(self._best_streak_card)
        stats_layout.addLayout(stats_row)

        accuracy_box = GlassCard()
        accuracy_layout = QVBoxLayout(accuracy_box)
        accuracy_layout.setContentsMargins(14, 12, 14, 12)
        accuracy_layout.setSpacing(8)
        accuracy_row = QHBoxLayout()
        accuracy_row.setContentsMargins(0, 0, 0, 0)
        accuracy_label = QLabel("துல்லியம்")
        accuracy_label.setStyleSheet(f"color: {HomeColors.TEXT_SECONDARY}; font-size: 12px; font-weight: 800;")
        self._accuracy_value_label = QLabel("0%")
        self._accuracy_value_label.setStyleSheet(f"color: {HomeColors.TEXT_PRIMARY}; font-size: 12px; font-weight: 900;")
        accuracy_row.addWidget(accuracy_label)
        accuracy_row.addStretch(1)
        accuracy_row.addWidget(self._accuracy_value_label)
        accuracy_layout.addLayout(accuracy_row)
        self._accuracy_bar = HomeProgressBar()
        self._accuracy_bar.set_progress(0, 100, QColor(HomeColors.MINT).lighter(120).name(), HomeColors.PRIMARY)
        accuracy_layout.addWidget(self._accuracy_bar)
        stats_layout.addWidget(accuracy_box)

        self.reset_button = QPushButton("மீட்டமை")
        restart_icon_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "icon_restart.svg"
        if restart_icon_path.exists():
            self.reset_button.setIcon(QIcon(str(restart_icon_path)))
        self.reset_button.setIconSize(QSize(18, 18))
        self.reset_button.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {HomeColors.PRIMARY_LIGHT}, stop:1 {HomeColors.PRIMARY});
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 16px;
                font-weight: 900;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {HomeColors.PRIMARY}; }}
            QPushButton:pressed {{ background: {HomeColors.PRIMARY_DARK}; }}
            """
        )
        self.reset_button.clicked.connect(self._reset_progress)
        stats_layout.addWidget(self.reset_button, 0)

        stats_layout.addStretch(1)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.addStretch(1)
        about_btn = QPushButton()
        about_btn.setToolTip("எங்களை பற்றி")
        about_icon_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "icon_about.svg"
        if about_icon_path.exists():
            about_btn.setIcon(QIcon(str(about_icon_path)))
        about_btn.setIconSize(QSize(22, 22))
        about_btn.setFixedSize(44, 44)
        about_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {HomeColors.PRIMARY_LIGHT}, stop:1 {HomeColors.PRIMARY});
                color: white;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{ background: {HomeColors.PRIMARY}; }}
            QPushButton:pressed {{ background: {HomeColors.PRIMARY_DARK}; }}
            """
        )
        about_btn.setCursor(Qt.PointingHandCursor)
        about_btn.clicked.connect(self._show_about)
        bottom_row.addWidget(about_btn, 0)
        stats_layout.addLayout(bottom_row)

        content_row.addWidget(stats_panel, 0)

        levels_panel = GlassCard()
        levels_layout = QVBoxLayout(levels_panel)
        levels_layout.setContentsMargins(22, 22, 22, 22)
        levels_layout.setSpacing(14)

        levels_header = QHBoxLayout()
        levels_header.setContentsMargins(0, 0, 0, 0)
        levels_title = QLabel("🎯 நிலைகள்")
        levels_title.setStyleSheet(f"color: {HomeColors.TEXT_PRIMARY}; font-size: 16px; font-weight: 900;")
        self._levels_summary_label = QLabel("")
        self._levels_summary_label.setStyleSheet(f"color: {HomeColors.TEXT_SECONDARY}; font-size: 12px; font-weight: 800;")
        levels_header.addWidget(levels_title)
        levels_header.addStretch(1)
        levels_header.addWidget(self._levels_summary_label)
        levels_layout.addLayout(levels_header)

        self._levels_scroll = QScrollArea()
        self._levels_scroll.setWidgetResizable(True)
        self._levels_scroll.setFrameShape(QFrame.NoFrame)
        self._levels_scroll.setStyleSheet("background: transparent;")
        self._levels_list_container = QWidget()
        self._levels_list_container.setStyleSheet("background: transparent;")
        self._home_levels_layout = QVBoxLayout(self._levels_list_container)
        self._home_levels_layout.setContentsMargins(0, 0, 0, 0)
        self._home_levels_layout.setSpacing(14)
        self._levels_scroll.setWidget(self._levels_list_container)
        levels_layout.addWidget(self._levels_scroll, 1)

        content_row.addWidget(levels_panel, 1)

        home_layout.addLayout(content_row, 1)

        footer_tagline = QLabel("செம்மொழித் தமிழ் கற்போம்")
        footer_tagline.setAlignment(Qt.AlignCenter)
        footer_tagline.setStyleSheet(
            f"""
            color: rgba(26, 58, 58, 0.45);
            font-size: 11px;
            font-weight: 700;
            """
        )
        home_layout.addWidget(footer_tagline, 0)

        typing_layout = QVBoxLayout(self._typing_screen)
        typing_layout.setContentsMargins(16, 16, 16, 16)
        typing_layout.setSpacing(20)

        typing_header = QWidget()
        self._typing_header = typing_header
        typing_header.setFixedHeight(48)
        typing_header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        header_row = QHBoxLayout(typing_header)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        self._back_button = QPushButton("← நிலைகள்")
        self._back_button.setCursor(Qt.PointingHandCursor)
        self._back_button.setFixedHeight(48)
        self._back_button.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid rgba(0,131,143,0.2);
                border-radius: 12px;
                color: {HomeColors.PRIMARY};
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
            }}
            QPushButton:hover {{ background: white; border-color: {HomeColors.PRIMARY}; }}
        """)
        self._back_button.clicked.connect(self._show_home_screen)
        header_row.addWidget(self._back_button, 0)
        header_row.addStretch(1)
        level_pill = QFrame()
        self._level_pill = level_pill
        level_pill.setFixedHeight(48)
        level_pill.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {HomeColors.PRIMARY_LIGHT}, stop:1 {HomeColors.PRIMARY});
                border-radius: 12px;
                border: none;
            }}
            """
        )
        pill_layout = QHBoxLayout(level_pill)
        pill_layout.setContentsMargins(20, 0, 20, 0)
        pill_layout.setSpacing(10)
        self._typing_title_label = QLabel("")
        self._typing_title_label.setStyleSheet("color: white; font-size: 15px; font-weight: 800;")
        pill_layout.addWidget(self._typing_title_label)
        header_row.addWidget(level_pill, 0)
        header_row.addStretch(1)
        typing_layout.addWidget(typing_header, 0)

        typing_content = QHBoxLayout()
        typing_content.setSpacing(24)

        stats_panel = GlassCard()
        self._typing_stats_panel = stats_panel
        stats_panel.setFixedWidth(280)
        stats_layout = QVBoxLayout(stats_panel)
        stats_layout.setContentsMargins(16, 16, 16, 16)
        stats_layout.setSpacing(0)

        def _add_divider():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet(f"background: {HomeColors.PROGRESS_TRACK}; border: none; max-height: 1px;")
            line.setFixedHeight(1)
            stats_layout.addSpacing(14)
            stats_layout.addWidget(line)
            stats_layout.addSpacing(14)

        def _muted_label(text, size=12, align=None):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {HomeColors.TEXT_MUTED}; font-size: {size}px;")
            if align: lbl.setAlignment(align)
            return lbl

        def _big_value(text, color=HomeColors.PRIMARY, size=32, align=None):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: 900;")
            if align: lbl.setAlignment(align)
            return lbl

        def _stat_column(header_text, value_text, sub_text, value_color=HomeColors.PRIMARY, value_size=32):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignCenter)
            col.addWidget(_muted_label(header_text, 12, Qt.AlignCenter))
            val = _big_value(value_text, value_color, value_size, Qt.AlignCenter)
            col.addWidget(val)
            col.addWidget(_muted_label(sub_text, 10 if sub_text.endswith("/min") else 11, Qt.AlignCenter))
            return col, val

        def _vertical_divider(min_h=44):
            d = QWidget()
            d.setFixedWidth(1)
            d.setMinimumHeight(min_h)
            d.setStyleSheet(f"background-color: {HomeColors.PROGRESS_TRACK};")
            return d

        def _side_by_side(left, right, divider_h=44):
            row = QHBoxLayout()
            row.setSpacing(0)
            row.addLayout(left, 1)
            row.addWidget(_vertical_divider(divider_h))
            row.addLayout(right, 1)
            return row

        self._stat_time_header = _muted_label("⏱️ நேரம்")
        stats_layout.addWidget(self._stat_time_header)
        self._typing_time_label = QLabel("0:00")
        self._typing_time_label.setStyleSheet(f"color: {HomeColors.PRIMARY}; font-size: 36px; font-weight: 900; font-family: monospace;")
        stats_layout.addWidget(self._typing_time_label)

        _add_divider()

        wpm_col, self._typing_wpm_label = _stat_column("⚡ WPM", "0", "words/min")
        cpm_col, self._typing_cpm_label = _stat_column("⌨️ CPM", "0", "chars/min")
        self._stat_wpm_header = wpm_col.itemAt(0).widget()
        self._stat_wpm_sub = wpm_col.itemAt(2).widget()
        self._stat_cpm_header = cpm_col.itemAt(0).widget()
        self._stat_cpm_sub = cpm_col.itemAt(2).widget()
        stats_layout.addLayout(_side_by_side(wpm_col, cpm_col))

        _add_divider()

        acc_header = QHBoxLayout()
        self._stat_acc_header = _muted_label("🎯 துல்லியம்")
        acc_header.addWidget(self._stat_acc_header)
        acc_header.addStretch(1)
        self._typing_accuracy_value = _big_value("0%", size=18)
        acc_header.addWidget(self._typing_accuracy_value)
        stats_layout.addLayout(acc_header)
        stats_layout.addSpacing(6)
        self._typing_accuracy_bar = HomeProgressBar()
        self._typing_accuracy_bar.set_progress(0, 100, HomeColors.PRIMARY_LIGHT, HomeColors.PRIMARY)
        stats_layout.addWidget(self._typing_accuracy_bar)

        _add_divider()

        self._stat_streak_header = _muted_label("🔥 தொடர்ச்சி")
        stats_layout.addWidget(self._stat_streak_header)
        streak_row = QHBoxLayout()
        self._typing_streak_label = _big_value("0", HomeColors.TEXT_PRIMARY)
        streak_row.addWidget(self._typing_streak_label)
        self._typing_best_streak_label = _muted_label("/ சிறந்தது 0", 13)
        streak_row.addWidget(self._typing_best_streak_label)
        streak_row.addStretch(1)
        stats_layout.addLayout(streak_row)

        _add_divider()

        correct_col, self._typing_correct_label = _stat_column("", "0", "சரி ✓", "#2e7d32", 26)
        wrong_col, self._typing_wrong_label = _stat_column("", "0", "தவறு ✗", "#c62828", 26)
        correct_col.takeAt(0).widget().deleteLater()
        wrong_col.takeAt(0).widget().deleteLater()
        self._stat_correct_sub = correct_col.itemAt(1).widget()
        self._stat_wrong_sub = wrong_col.itemAt(1).widget()
        stats_layout.addLayout(_side_by_side(correct_col, wrong_col, 36))

        stats_layout.addStretch(1)
        stats_panel.setMinimumHeight(280)
        stats_panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        typing_content.addWidget(stats_panel, 0)

        practice_card = GlassCard()
        self._typing_practice_card = practice_card
        practice_card.setMinimumHeight(280)
        practice_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        practice_layout = QVBoxLayout(practice_card)
        practice_layout.setContentsMargins(32, 24, 32, 24)
        practice_layout.setSpacing(20)

        self._letter_sequence_widget = LetterSequenceWidget()
        practice_layout.addWidget(self._letter_sequence_widget, 0, Qt.AlignCenter)

        self._hero_letter_label = HeroLetterLabel()
        practice_layout.addWidget(self._hero_letter_label, 0, Qt.AlignCenter)

        self._typing_feedback_label = QLabel("இந்த எழுத்தை தட்டச்சு செய்க")
        self._typing_feedback_label.setStyleSheet(f"color: {HomeColors.TEXT_SECONDARY}; font-size: 16px; font-weight: 600;")
        self._typing_feedback_label.setAlignment(Qt.AlignCenter)
        practice_layout.addWidget(self._typing_feedback_label)

        self.progress_bar = ProgressCard(embedded=True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        practice_layout.addWidget(self.progress_bar)

        hidden_container = QWidget()
        hidden_container.setFixedHeight(0)
        hidden_container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        hidden_layout = QVBoxLayout(hidden_container)
        hidden_layout.setContentsMargins(0, 0, 0, 0)
        hidden_layout.setSpacing(0)
        self.combo_label = QLabel("")
        self.combo_label.setVisible(False)
        self.task_display = QLabel()
        self.task_display.setTextFormat(Qt.RichText)
        self.task_display.setVisible(False)
        self.input_box = QLineEdit()
        self.input_box.setFixedHeight(0)
        self.input_box.setStyleSheet("background: transparent; border: none; color: transparent;")
        self.input_box.installEventFilter(self)
        self.input_box.setReadOnly(True)
        hidden_layout.addWidget(self.task_display)
        hidden_layout.addWidget(self.input_box)
        practice_layout.addWidget(hidden_container)

        practice_layout.addStretch(1)
        typing_content.addWidget(practice_card, 1)
        typing_layout.addLayout(typing_content, 1)

        self._bottom_container = QWidget()
        self._bottom_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._bottom_container.setStyleSheet("""
            background: transparent;
            border-radius: 16px;
            padding: 16px;
        """)
        bottom_row = QHBoxLayout(self._bottom_container)
        bottom_row.setSpacing(15)
        bottom_row.setContentsMargins(0, 0, 0, 0)

        finger_ui_container = QWidget()
        finger_ui_layout = QVBoxLayout(finger_ui_container)
        finger_ui_layout.setSpacing(10)
        finger_ui_layout.setContentsMargins(0, 0, 0, 0)
        finger_ui_layout.setAlignment(Qt.AlignCenter)

        self._finger_guidance_label = QLabel("")
        self._finger_guidance_label.setAlignment(Qt.AlignCenter)
        self._finger_guidance_label.setWordWrap(True)
        self._finger_guidance_label.setTextFormat(Qt.RichText)
        self._finger_guidance_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {colors['text_primary']};
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 16px;
                font-weight: 600;
                font-family: '{QApplication.font().family()}', sans-serif;
                min-height: 50px;
            }}
        """)
        self._finger_guidance_label.setVisible(False)
        finger_ui_layout.addWidget(self._finger_guidance_label, 0, Qt.AlignCenter)

        hands_image_path = Path(__file__).parent.parent / "assets" / "hands.png"
        if hands_image_path.exists():
            self._hands_image_label = QLabel()
            self._original_hands_pixmap = QPixmap(str(hands_image_path))

            initial_max_width = 600
            pixmap = self._original_hands_pixmap
            if pixmap.width() > initial_max_width:
                pixmap = pixmap.scaledToWidth(initial_max_width, Qt.SmoothTransformation)

            self._hands_image_label.setPixmap(pixmap)
            self._hands_image_label.setAlignment(Qt.AlignCenter)
            self._hands_image_label.setStyleSheet("background: transparent; padding: 0px;")
            self._hands_image_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            self._hands_image_label.setMinimumWidth(200)
            self._hands_image_label.setMinimumHeight(100)
            finger_ui_layout.addWidget(self._hands_image_label, 0, Qt.AlignCenter)

        bottom_row.addWidget(finger_ui_container, 1)

        self._keyboard_widget = self._build_keyboard()
        self._keyboard_widget.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self._keyboard_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._keyboard_widget.setMinimumSize(400, 150)
        bottom_row.addWidget(self._keyboard_widget, 2)

        typing_layout.addWidget(self._bottom_container, 0)
        self._bottom_container.installEventFilter(self)

        self._stack.setCurrentWidget(self._home_screen)

        self._update_error_overlay_geometry()

        self.start_shortcut = QShortcut(Qt.CTRL | Qt.Key_Return, self)
        self.start_shortcut.activated.connect(self._submit_task)

        self._apply_responsive_fonts()
        QTimer.singleShot(50, self._rescale_typing_screen)

        self._typing_stats_timer = QTimer(self)
        self._typing_stats_timer.timeout.connect(self._update_typing_stats_panel)

    def _aggregate_best_accuracy(self) -> float:
        """Return the highest recorded accuracy (0–100) across all levels."""
        best = 0.0
        for lvl in self._levels_repo.all():
            p = self._progress_store.get_level_progress(lvl.key)
            best = max(best, float(p.best_accuracy))
        return max(0.0, min(100.0, best))

    def _set_home_accuracy(self, accuracy: float) -> None:
        """Update the home-screen accuracy bar and percentage label."""
        if self._accuracy_bar is None or self._accuracy_value_label is None:
            return
        a = max(0.0, min(100.0, float(accuracy)))
        self._accuracy_value_label.setText(f"{a:.0f}%")
        self._accuracy_bar.set_progress(int(round(a)), 100, QColor(HomeColors.MINT).lighter(120).name(), HomeColors.PRIMARY)

    def _refresh_levels_list(self) -> None:
        """Rebuild the home-screen level list and sync gamification stats."""
        level_states = self._build_level_states()

        if self._home_levels_layout is not None:
            while self._home_levels_layout.count():
                item = self._home_levels_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()

            icon_map = {0: "அ", 1: "ஆ", 2: "க்", 3: "கா", 4: "📝"}
            name_map = {
                0: "அடிப்படை எழுத்துகள்",
                1: "எளிய சொற்கள்",
                2: "எளிய வாக்கியங்கள்",
                3: "நடுத்தர வாக்கியங்கள்",
                4: "நீளமான வாக்கியங்கள்",
            }

            completed_levels = 0
            for state in level_states:
                task_count = len(state.level.tasks)
                if state.completed >= task_count and task_count > 0:
                    completed_levels += 1

            if self._levels_summary_label is not None:
                self._levels_summary_label.setText(f"{completed_levels}/{len(level_states)} நிறைவேற்றப்பட்டது")

            for idx, state in enumerate(level_states):
                level_id = idx
                try:
                    m = re.match(r"^level(\d+)$", state.level.key)
                    if m:
                        level_id = int(m.group(1))
                except Exception:
                    level_id = idx

                task_count = len(state.level.tasks)
                title = name_map.get(level_id, state.level.name)
                icon = icon_map.get(level_id, title[:1] if title else "•")
                completed = state.completed >= task_count and task_count > 0
                card = HomeLevelRowCard(
                    level_key=state.level.key,
                    level_id=level_id,
                    title=title,
                    icon=icon,
                    current=int(state.completed),
                    total=int(task_count),
                    unlocked=bool(state.unlocked),
                    selected=bool(state.is_current),
                    completed=completed,
                    on_click=self._start_level,
                    on_restart=self._restart_level,
                    on_view=self._view_level,
                )
                self._home_levels_layout.addWidget(card)

            self._home_levels_layout.addStretch(1)

        self._update_gamification_stats()

    def _build_level_states(self) -> list[LevelState]:
        """Compute unlock/completion state for every level and mark the current target."""
        levels = self._levels_repo.all()
        states: list[LevelState] = []
        previous_completed = True
        for level in levels:
            progress = self._progress_store.get_level_progress(level.key)
            task_count = len(level.tasks)
            unlocked = bool(self._unlock_all_levels or previous_completed)
            states.append(LevelState(level=level, unlocked=unlocked, completed=progress.completed, is_current=False))
            previous_completed = progress.completed >= task_count

        if not self._unlock_all_levels:
            for st in states:
                if st.unlocked and st.completed < len(st.level.tasks):
                    st.is_current = True
                    break
        return states

    def _restart_level(self, level_key: str) -> None:
        """Clear progress for the level and start it from the beginning."""
        self._progress_store.reset_level(level_key)
        self._start_level(level_key, view_only=False)

    def _view_level(self, level_key: str) -> None:
        """Open a completed level in view-only mode (no timer, no typing)."""
        self._start_level(level_key, view_only=True)

    def _start_level(self, level_key: str, view_only: bool = False) -> None:
        """Load a level, create its session, and switch to the typing screen."""
        self._view_only_session = view_only
        level = self._levels_repo.get(level_key)
        progress = self._progress_store.get_level_progress(level_key)
        task_count = len(level.tasks)
        self._current_level = level
        self._session = None
        self.progress_bar.setRange(0, task_count)
        self.progress_bar.setValue(progress.completed)
        self.task_display.setText("")
        self.input_box.setText("")
        self._start_session(level, progress.completed)
        if self._typing_title_label is not None:
            level_id = re.sub(r"^level", "", level.key)
            self._typing_title_label.setText(f"நிலை {level_id}: {level.name}")
        if self._typing_feedback_label is not None:
            if view_only:
                self._typing_feedback_label.setText("பார்வை மட்டும் — தட்டச்சு செய்ய முடியாது")
            else:
                self._typing_feedback_label.setText("இந்த எழுத்தை தட்டச்சு செய்க")
        self._show_typing_screen()

    def _show_home_screen(self) -> None:
        """Navigate back to the home screen and stop the stats timer."""
        if self._stack is None or self._home_screen is None:
            return
        self._stack.setCurrentWidget(self._home_screen)
        if self._typing_stats_timer is not None:
            self._typing_stats_timer.stop()
        if self._finger_guidance_label is not None:
            self._finger_guidance_label.setVisible(False)
        self._clear_keyboard_highlight()
        if self._levels_scroll is not None:
            self._levels_scroll.setFocus()

    def _show_typing_screen(self) -> None:
        """Switch to the typing screen and start the stats refresh timer."""
        if self._stack is None or self._typing_screen is None:
            return
        self._stack.setCurrentWidget(self._typing_screen)
        self._typing_screen.updateGeometry()
        if self.input_box is not None:
            self.input_box.setFocus()
        self._update_typing_stats_panel()
        if not self._view_only_session and self._typing_stats_timer is not None:
            self._typing_stats_timer.start(1000)

    def _start_session(self, level: Level, start_index: int) -> None:
        """Create a new typing session for *level*, starting at *start_index*."""
        task_count = len(level.tasks)
        if start_index >= task_count:
            start_index = 0
        self._session = TypingSession(level.tasks, start_index=start_index)
        self.progress_bar.setRange(0, task_count)
        self._keystroke_tracker.reset_session()
        self._update_gamification_stats()
        self._load_current_task()

    def _load_current_task(self) -> None:
        """Prepare the UI for the next task in the current session."""
        if not self._session:
            return
        if self._session.is_complete():
            self.task_display.setText("நிலை முடிந்தது!")
            return
        self._current_task_text = self._session.current_task()
        self._task_display_offset = 0
        self._keystroke_sequence = self._tamil99_layout.get_keystroke_sequence(self._current_task_text)
        self._keystroke_index = 0
        self._typed_keystrokes = []
        self._typed_tamil_text = ""
        self._keystroke_to_char_map: dict[int, int] = {}
        self._build_keystroke_to_char_map()
        self._render_task_display("", self._current_task_text, is_error=False)
        self._set_input_text("")
        self.input_box.setFocus()
        self._update_keyboard_hint()
    
    def _build_keystroke_to_char_map(self) -> None:
        """Map each keystroke index to the character index it contributes to.

        Mirrors the character-decomposition logic of ``get_keystroke_sequence``
        so that combined Tamil characters (e.g. "து" → two keystrokes) all
        point back to the first Unicode code-unit.
        """
        self._keystroke_to_char_map = {}
        keystroke_idx = 0
        target = self._current_task_text
        i = 0

        while i < len(target):
            char = target[i]

            if char == ' ':
                self._keystroke_to_char_map[keystroke_idx] = i
                keystroke_idx += 1
                i += 1
            elif i + 1 < len(target):
                combined = char + target[i + 1]
                if combined in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                    key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[combined]
                    for _ in key_seq:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1
                    i += 2
                    continue
            if char in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[char]
                if key_seq.startswith('^#'):
                    self._keystroke_to_char_map[keystroke_idx] = i
                    keystroke_idx += 1
                    self._keystroke_to_char_map[keystroke_idx] = i
                    keystroke_idx += 1
                    if len(key_seq) > 2:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1
                elif key_seq.startswith('^'):
                    self._keystroke_to_char_map[keystroke_idx] = i
                    keystroke_idx += 1
                    if len(key_seq) > 1:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1
                else:
                    for _ in key_seq:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1
                i += 1
            else:
                self._keystroke_to_char_map[keystroke_idx] = i
                keystroke_idx += 1
                i += 1

    def _set_input_text(self, text: str) -> None:
        """Set the hidden input box text without triggering auto-submit."""
        self._auto_submit_block = True
        self.input_box.setText(text)
        self.input_box.setCursorPosition(len(text))
        self._auto_submit_block = False
        self._set_input_error_state(False)

    def eventFilter(self, obj, event) -> bool:
        """Intercept key-press events on the hidden input and resize events on the bottom bar."""
        if obj == self.input_box and event.type() == event.Type.KeyPress:
            return self._on_key_press(event)
        elif obj == self._bottom_container and event.type() == event.Type.Resize:
            QTimer.singleShot(10, self._adjust_adaptive_layout)
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        """Re-layout adaptive UI elements when the window is resized."""
        super().resizeEvent(event)
        self._update_error_overlay_geometry()
        QTimer.singleShot(10, self._adjust_adaptive_layout)
        QTimer.singleShot(10, self._rescale_typing_screen)
    
    def _adjust_adaptive_layout(self) -> None:
        """Redistribute space between the finger-guide image and the keyboard widget."""
        if not self._keyboard_widget or not self._bottom_container:
            return

        available_width = self._bottom_container.width() - 40
        if available_width <= 0:
            return

        min_hands_width = 200
        max_hands_width = 600
        hands_ratio = 0.3
        min_keyboard_width = 400

        ideal_hands_width = min(max_hands_width, max(min_hands_width, int(available_width * hands_ratio)))
        keyboard_width = available_width - ideal_hands_width - 15

        if keyboard_width < min_keyboard_width and available_width > min_keyboard_width + min_hands_width + 15:
            keyboard_width = min_keyboard_width
            ideal_hands_width = max(min_hands_width, available_width - keyboard_width - 15)

        if self._hands_image_label and self._original_hands_pixmap:
            current_width = self._hands_image_label.width()
            if abs(ideal_hands_width - current_width) > 10:
                scaled_pixmap = self._original_hands_pixmap.scaledToWidth(
                    ideal_hands_width, Qt.SmoothTransformation
                )
                self._hands_image_label.setPixmap(scaled_pixmap)
                self._hands_image_label.setMinimumWidth(ideal_hands_width)
                self._hands_image_label.setMaximumWidth(ideal_hands_width)

        if keyboard_width > 0:
            self._update_keyboard_font_sizes(keyboard_width)
    
    def _rescale_typing_screen(self) -> None:
        """Scale typing screen fonts and dimensions proportionally to window size.

        Reference design: 1920x1080.  Every pixel dimension and font-size is
        expressed as a fraction of window width (w) or height (h) so nothing
        clips when the window shrinks or grows.
        """
        w = self.width()
        h = self.height()
        if w < 100 or h < 100:
            return

        REF_W, REF_H = 1920, 1080
        sw = w / REF_W
        sh = h / REF_H
        s = min(sw, sh)

        def _set_font(lbl: Optional[QLabel], ref_px: int) -> None:
            """Replace ``font-size`` in *lbl*'s stylesheet with a scaled value."""
            if lbl is None:
                return
            sz = max(9, int(ref_px * s))
            cur = lbl.styleSheet()
            new_ss = re.sub(r"font-size:\s*\d+px", f"font-size: {sz}px", cur)
            if new_ss == cur and "font-size:" not in cur:
                new_ss += f" font-size: {sz}px;"
            if new_ss != cur:
                lbl.setStyleSheet(new_ss)

        if self._typing_screen is not None:
            outer_lay = self._typing_screen.layout()
            if outer_lay is not None:
                om = max(8, int(16 * s))
                outer_lay.setContentsMargins(om, om, om, om)
                outer_lay.setSpacing(max(8, int(20 * s)))

        stats_w = max(180, int(280 * sw))
        if self._typing_stats_panel is not None:
            self._typing_stats_panel.setFixedWidth(stats_w)
            m = max(10, int(16 * s))
            self._typing_stats_panel.layout().setContentsMargins(m, m, m, m)

        hdr_h = max(32, int(48 * sh))
        if self._typing_header is not None:
            self._typing_header.setFixedHeight(hdr_h)

        if self._back_button is not None:
            self._back_button.setFixedHeight(hdr_h)
            btn_fs = max(10, int(14 * s))
            btn_r = max(8, int(12 * s))
            btn_px = max(10, int(24 * sw))
            self._back_button.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid rgba(0,131,143,0.2);
                    border-radius: {btn_r}px;
                    color: {HomeColors.PRIMARY};
                    font-size: {btn_fs}px;
                    font-weight: 600;
                    padding: 0 {btn_px}px;
                }}
                QPushButton:hover {{ background: white; border-color: {HomeColors.PRIMARY}; }}
            """)

        if self._level_pill is not None:
            pill_r = max(8, int(12 * s))
            self._level_pill.setFixedHeight(hdr_h)
            self._level_pill.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {HomeColors.PRIMARY_LIGHT}, stop:1 {HomeColors.PRIMARY});
                    border-radius: {pill_r}px;
                    border: none;
                }}
            """)

        if self._typing_title_label is not None:
            title_fs = max(10, int(15 * s))
            self._typing_title_label.setStyleSheet(
                f"color: white; font-size: {title_fs}px; font-weight: 800;"
            )

        _set_font(self._typing_time_label, 36)
        _set_font(self._typing_wpm_label, 32)
        _set_font(self._typing_cpm_label, 32)
        _set_font(self._typing_accuracy_value, 18)
        _set_font(self._typing_streak_label, 32)
        _set_font(self._typing_best_streak_label, 13)
        _set_font(self._typing_correct_label, 26)
        _set_font(self._typing_wrong_label, 26)
        _set_font(self._stat_time_header, 12)
        _set_font(self._stat_wpm_header, 12)
        _set_font(self._stat_wpm_sub, 10)
        _set_font(self._stat_cpm_header, 12)
        _set_font(self._stat_cpm_sub, 10)
        _set_font(self._stat_acc_header, 12)
        _set_font(self._stat_streak_header, 12)
        _set_font(self._stat_correct_sub, 11)
        _set_font(self._stat_wrong_sub, 11)

        if self._typing_feedback_label is not None:
            fb_sz = max(10, int(16 * s))
            self._typing_feedback_label.setStyleSheet(
                f"color: {HomeColors.TEXT_SECONDARY}; font-size: {fb_sz}px; font-weight: 600;"
            )

        if self._typing_practice_card is not None:
            pm = max(12, int(32 * s))
            pv = max(10, int(24 * s))
            lay = self._typing_practice_card.layout()
            if lay is not None:
                lay.setContentsMargins(pm, pv, pm, pv)
                lay.setSpacing(max(8, int(20 * s)))

        if self._hero_letter_label is not None:
            hero_dim = max(64, int(120 * s))
            hero_font = max(24, int(48 * s))
            hero_radius = hero_dim // 2
            self._hero_letter_label.setMinimumSize(hero_dim, hero_dim)
            self._hero_letter_label.setMaximumSize(hero_dim, hero_dim)
            self._hero_letter_label.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {HomeColors.PRIMARY_LIGHT}, stop:1 {HomeColors.PRIMARY});
                    color: white;
                    border-radius: {hero_radius}px;
                    font-size: {hero_font}px;
                    font-weight: 900;
                }}
            """)

        if self._letter_sequence_widget is not None:
            seq_h = max(32, int(60 * sh))
            self._letter_sequence_widget.setFixedHeight(seq_h)
            self._letter_sequence_widget._scale = s

        if self._finger_guidance_label is not None:
            fg_fs = max(10, int(16 * s))
            fg_pad_v = max(6, int(12 * s))
            fg_pad_h = max(8, int(16 * s))
            fg_min_h = max(30, int(50 * s))
            cur_ss = self._finger_guidance_label.styleSheet()
            new_ss = re.sub(r"font-size:\s*\d+px", f"font-size: {fg_fs}px", cur_ss)
            new_ss = re.sub(r"padding:\s*\d+px\s+\d+px", f"padding: {fg_pad_v}px {fg_pad_h}px", new_ss)
            new_ss = re.sub(r"min-height:\s*\d+px", f"min-height: {fg_min_h}px", new_ss)
            if new_ss != cur_ss:
                self._finger_guidance_label.setStyleSheet(new_ss)

    def _update_keyboard_font_sizes(self, keyboard_width: int) -> None:
        """Scale keyboard key fonts proportionally to *keyboard_width* (reference: 1402 px → 18 px)."""
        if not self._keyboard_widget:
            return

        font_scale = keyboard_width / 1402
        base_font_size = max(12, int(18 * font_scale))
        tamil_base_font = base_font_size
        english_font = max(7, int(base_font_size * 0.75))
        tamil_shift_font = max(9, int(base_font_size * 0.75))
        special_font = max(9, int(base_font_size * 0.78))

        if (self._keyboard_font_sizes.get('base', 0) != base_font_size or
            abs(self._keyboard_font_sizes.get('base', 18) - base_font_size) > 1):

            self._keyboard_font_sizes = {
                'base': base_font_size,
                'tamil_base': tamil_base_font,
                'english': english_font,
                'tamil_shift': tamil_shift_font,
                'special': special_font
            }

            self._rebuild_keyboard_labels()

            if "Space" in self._key_labels:
                space_label = self._key_labels["Space"]
                style = self._build_key_style("Space", special_font, font_weight=500)
                space_label.setStyleSheet(style)
                self._key_base_style_by_label[space_label] = style

            for shift_label in self._shift_labels:
                style = self._build_key_style("Shift", special_font, font_weight=500)
                shift_label.setStyleSheet(style)
                self._key_base_style_by_label[shift_label] = style
    
    def _on_key_press(self, event: QKeyEvent) -> bool:
        """Process a single physical keypress against the expected keystroke sequence."""
        if not self._session:
            return False
        if self._view_only_session:
            return True

        key = event.key()
        text = event.text()
        
        if key == Qt.Key.Key_Space:
            if self._keystroke_index >= len(self._keystroke_sequence):
                self._submit_task_from_keystrokes()
                return True
            pressed_key = "Space"
        elif key == Qt.Key.Key_Backspace:
            if self._typed_keystrokes and self._keystroke_index > 0:
                self._typed_keystrokes.pop()
                self._keystroke_index -= 1
                self._update_typed_tamil_text_from_keystrokes()
                self._input_has_error = False
                self._set_input_error_state(False)
                self._update_display_from_keystrokes()
                self._update_keyboard_hint()
            return True
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._keystroke_index >= len(self._keystroke_sequence):
                self._submit_task_from_keystrokes()
            return True
        elif text and text.isprintable():
            if self._keystroke_index >= len(self._keystroke_sequence):
                return False
            pressed_key = text.upper() if text.isalpha() else text
        else:
            return False
        
        expected_key, needs_shift = self._keystroke_sequence[self._keystroke_index]
        
        if expected_key == ' ':
            expected_key = "Space"
        if pressed_key == ' ':
            pressed_key = "Space"
        
        result = self._keystroke_tracker.record_stroke(pressed_key, expected_key)
        
        if result['is_correct']:
            self._typed_keystrokes.append(pressed_key)
            self._keystroke_index += 1
            
            self._update_typed_tamil_text_from_keystrokes()
            
            self._input_has_error = False
            self._set_input_error_state(False)
            
            self._update_display_from_keystrokes()
        else:
            self._input_has_error = True
            self._set_input_error_state(True)
            if self.task_display is not None:
                self.task_display.setText("")
            self._flash_invalid_input_overlay()
        
        self._update_keyboard_hint()
        self._update_stats_from_tracker()
        
        return True

    def _update_error_overlay_geometry(self) -> None:
        """Resize the error-flash overlay to cover the full window."""
        if not self._error_overlay:
            return
        s = self.size()
        self._error_overlay.setGeometry(0, 0, s.width(), s.height())

    def _flash_invalid_input_overlay(self, duration_ms: int = 200) -> None:
        """Flash a short red overlay on invalid input."""
        if not self._error_overlay or not self._error_overlay_effect or not self._error_overlay_anim:
            return
        
        try:
            self._error_overlay_anim.stop()
        except Exception:
            pass

        self._update_error_overlay_geometry()
        self._error_overlay.show()
        self._error_overlay.raise_()

        self._error_overlay_effect.setOpacity(0.0)
        self._error_overlay_anim.setDuration(max(50, int(duration_ms)))
        self._error_overlay_anim.start()
    
    def _update_typed_tamil_text_from_keystrokes(self) -> None:
        """Reconstruct Tamil text by matching typed keystrokes against the target.

        Walks the target string character-by-character (handling combined
        Tamil characters, special prefix sequences like ``^#`` for numerals and
        ``^`` for vowel signs) and verifies that the recorded keystrokes match.
        Stops at the first mismatch.
        """
        target = self._current_task_text
        typed_ks_count = len(self._typed_keystrokes)

        reconstructed = ""
        keystroke_idx = 0
        i = 0

        while i < len(target) and keystroke_idx < typed_ks_count:
            char = target[i]

            if char == ' ':
                if keystroke_idx < typed_ks_count and self._typed_keystrokes[keystroke_idx] == "Space":
                    reconstructed += " "
                    keystroke_idx += 1
                i += 1
                continue

            elif i + 1 < len(target):
                combined = char + target[i + 1]
                if combined in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                    key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[combined]
                    if keystroke_idx + len(key_seq) <= typed_ks_count:
                        matches = True
                        for j, expected_key in enumerate(key_seq):
                            if self._typed_keystrokes[keystroke_idx + j].upper() != expected_key.upper():
                                matches = False
                                break
                        if matches:
                            reconstructed += combined
                            keystroke_idx += len(key_seq)
                            i += 2
                            continue

            if char in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[char]
                if key_seq.startswith('^#'):
                    required_keys = 3 if len(key_seq) > 2 else 2
                    if keystroke_idx + required_keys <= typed_ks_count:
                        if (self._typed_keystrokes[keystroke_idx].upper() == '^' and
                            keystroke_idx + 1 < typed_ks_count and
                            self._typed_keystrokes[keystroke_idx + 1].upper() == '#'):
                            if len(key_seq) > 2:
                                if (keystroke_idx + 2 < typed_ks_count and
                                    self._typed_keystrokes[keystroke_idx + 2].upper() == key_seq[2].upper()):
                                    reconstructed += char
                                    keystroke_idx += required_keys
                                    i += 1
                                    continue
                elif key_seq.startswith('^'):
                    required_keys = 2 if len(key_seq) > 1 else 1
                    if keystroke_idx + required_keys <= typed_ks_count:
                        if self._typed_keystrokes[keystroke_idx].upper() == '^':
                            if len(key_seq) > 1:
                                if (keystroke_idx + 1 < typed_ks_count and
                                    self._typed_keystrokes[keystroke_idx + 1].upper() == key_seq[1].upper()):
                                    reconstructed += char
                                    keystroke_idx += required_keys
                                    i += 1
                                    continue
                else:
                    if keystroke_idx + len(key_seq) <= typed_ks_count:
                        matches = True
                        for j, expected_key in enumerate(key_seq):
                            if self._typed_keystrokes[keystroke_idx + j].upper() != expected_key.upper():
                                matches = False
                                break
                        if matches:
                            reconstructed += char
                            keystroke_idx += len(key_seq)
                            i += 1
                            continue
            else:
                # Fallback for non-Tamil characters (punctuation, etc.)
                if keystroke_idx < typed_ks_count:
                    typed_key = self._typed_keystrokes[keystroke_idx]
                    key_label, needs_shift = self._map_char_to_key(char)
                    if (typed_key == char or
                        typed_key.upper() == char.upper() or
                        typed_key.upper() == key_label.upper()):
                        reconstructed += char
                        keystroke_idx += 1
                        i += 1
                        continue

            break

        self._typed_tamil_text = reconstructed
    
    def _update_display_from_keystrokes(self) -> None:
        """Refresh the task display and input box from the reconstructed Tamil text."""
        target = self._current_task_text
        typed_text = self._typed_tamil_text
        is_error = self._input_has_error
        self._update_task_display_for_typed(typed_text, target, is_error)
        self._set_input_text(typed_text)
    
    def _submit_task_from_keystrokes(self) -> None:
        """Submit the current task once all expected keystrokes have been entered."""
        if not self._session or self._session.is_complete():
            return

        typed = self._typed_tamil_text if self._typed_tamil_text else self._current_task_text
        self._submit_task(typed)
        
        self._typed_keystrokes = []
        self._typed_tamil_text = ""
        self._keystroke_index = 0
        self._input_has_error = False
    
    def _update_stats_from_tracker(self) -> None:
        """Propagate keystroke-tracker changes to the gamification UI."""
        self._update_gamification_stats()

    def _submit_task(self, typed: Optional[str] = None) -> None:
        """Score the typed text, persist progress, and advance to the next task."""
        if not self._session or not self._current_level:
            return
        if self._session.is_complete():
            return
        if typed is None:
            typed = self.input_box.text()
        if not typed:
            return
        result = self._session.submit(typed)
        self._update_stats(result)
        self.progress_bar.setValue(self._session.index)
        self._progress_store.update_level_progress(
            self._current_level.key,
            self._session.index,
            self._session.aggregate_wpm(),
            self._session.aggregate_accuracy(),
        )

        if self._session.is_complete():
            self._level_completed()
            return
        self._load_current_task()
        self._update_keyboard_hint()

    def _update_stats(self, result: TaskResult) -> None:
        """Update score, streak, and combo multiplier from a single task result."""
        if result.accuracy == 100.0:
            self._current_streak += 1
            if self._current_streak > self._best_streak:
                self._best_streak = self._current_streak
            base_points = 10
            streak_bonus = self._current_streak * 2
            self._total_score += int((base_points + streak_bonus) * self._combo_multiplier)
            self._consecutive_correct += 1
        else:
            self._current_streak = 0
            self._consecutive_correct = 0
        
        if self._consecutive_correct >= 10:
            self._combo_multiplier = 2.0
        elif self._consecutive_correct >= 5:
            self._combo_multiplier = 1.5
        else:
            self._combo_multiplier = 1.0

        self._progress_store.update_gamification(
            self._total_score,
            self._current_streak,
            self._best_streak,
        )
        self._update_gamification_stats()
    
    def _update_gamification_stats(self) -> None:
        """Update home UI stats (and hide combo label)."""
        if self._points_card is not None:
            self._points_card.set_value(f"{self._total_score:,}")
        if self._streak_card is not None:
            self._streak_card.set_value(f"{self._current_streak}")
        if self._best_streak_card is not None:
            self._best_streak_card.set_value(f"{self._best_streak}")

        if self._session is not None:
            self._set_home_accuracy(self._session.aggregate_accuracy())
        else:
            self._set_home_accuracy(self._aggregate_best_accuracy())

        self._update_typing_stats_panel()
        if self.combo_label is not None:
            self.combo_label.setVisible(False)

    def _update_typing_stats_panel(self) -> None:
        """Update typing screen left panel: time, WPM, accuracy, streak, correct/wrong, progress text."""
        if self._session is None:
            return
        elapsed = int(time.time() - self._session.start_time)
        m, s = divmod(elapsed, 60)
        time_str = f"{m}:{s:02d}"
        if self._typing_time_label is not None:
            self._typing_time_label.setText(time_str)
        wpm = self._session.aggregate_wpm()
        if self._typing_wpm_label is not None:
            self._typing_wpm_label.setText(f"{int(wpm)}")
        cpm = self._session.aggregate_cpm()
        if self._typing_cpm_label is not None:
            self._typing_cpm_label.setText(f"{int(cpm)}")
        acc = self._session.aggregate_accuracy()
        if self._typing_accuracy_value is not None:
            self._typing_accuracy_value.setText(f"{int(round(acc))}%")
        if self._typing_accuracy_bar is not None:
            self._typing_accuracy_bar.set_progress(int(round(acc)), 100, HomeColors.PRIMARY_LIGHT, HomeColors.PRIMARY)
        if self._typing_streak_label is not None:
            self._typing_streak_label.setText(f"{self._current_streak}")
        if self._typing_best_streak_label is not None:
            self._typing_best_streak_label.setText(f"/ சிறந்தது {self._best_streak}")
        if self._typing_correct_label is not None:
            self._typing_correct_label.setText(f"{self._session.total_correct}")
        if self._typing_wrong_label is not None:
            self._typing_wrong_label.setText(f"{self._session.aggregate_errors()}")
        task_count = self._session.total_tasks
        idx = self._session.index
        pct = round((idx / task_count) * 100) if task_count else 0
        self.progress_bar.setValue(idx)

    def _level_completed(self) -> None:
        """Show the level-completed overlay and return to the home screen."""
        if self._typing_stats_timer is not None:
            self._typing_stats_timer.stop()
        self.task_display.setText("நிலை முடிந்தது! அடுத்த நிலையைத் தேர்வு செய்யவும்.")
        self._set_input_text("")
        overlay = self._level_completed_overlay
        overlay.setGeometry(self._stack.rect())
        overlay.raise_()
        overlay.show()
        loop = QEventLoop()
        overlay.closed.connect(loop.quit)
        loop.exec()
        overlay.closed.disconnect(loop.quit)
        self._refresh_levels_list()
        self._clear_keyboard_highlight()

    def _reset_progress(self) -> None:
        """Show the confirmation overlay and, if confirmed, wipe all progress."""
        overlay = self._reset_overlay
        overlay.setGeometry(self._stack.rect())
        overlay.raise_()
        overlay.show()
        confirmed = [False]

        def on_closed(ok: bool) -> None:
            confirmed[0] = ok
            loop.quit()

        loop = QEventLoop()
        overlay.closed.connect(on_closed)
        loop.exec()
        overlay.closed.disconnect(on_closed)

        if confirmed[0]:
            self._progress_store.reset()
            self._total_score = 0
            self._current_streak = 0
            self._best_streak = 0
            self._update_gamification_stats()
            self._refresh_levels_list()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Persist progress when closing the app."""
        if self._progress_store is not None:
            self._progress_store.save()
        super().closeEvent(event)

    def _show_about(self) -> None:
        """Display the About overlay as a modal dialog."""
        overlay = self._about_overlay
        overlay.setGeometry(self._stack.rect())
        overlay.raise_()
        overlay.show()
        loop = QEventLoop()
        overlay.closed.connect(loop.quit)
        loop.exec()
        overlay.closed.disconnect(loop.quit)

    def _build_keyboard(self) -> QWidget:
        """Create a virtual Tamil99 keyboard widget laid out on a ``QGridLayout``."""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)
        container.setStyleSheet("background: transparent; border-radius: 12px; padding: 0px;")

        colors = self._get_theme_colors()
        
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            font_scale = screen.availableGeometry().width() / 1920.0
            base_font_size = max(14, int(18 * font_scale))
        else:
            base_font_size = 18

        self._keyboard_font_sizes = {
            'base': base_font_size,
            'tamil_base': base_font_size,
            'english': max(8, int(base_font_size * 0.75)),
            'tamil_shift': max(10, int(base_font_size * 0.75)),
            'special': max(10, int(base_font_size * 0.78))
        }
        
        rows = [
            [("`", 1.0), ("1", 1.0), ("2", 1.0), ("3", 1.0), ("4", 1.0), ("5", 1.0), ("6", 1.0), ("7", 1.0), ("8", 1.0), ("9", 1.0), ("0", 1.0), ("-", 1.0), ("=", 1.0), ("Backspace", 2.0)],
            [("Tab", 1.75), ("Q", 1.0), ("W", 1.0), ("E", 1.0), ("R", 1.0), ("T", 1.0), ("Y", 1.0), ("U", 1.0), ("I", 1.0), ("O", 1.0), ("P", 1.0), ("[", 1.0), ("]", 1.0), ("\\", 1.25)],
            [("Caps", 2.0), ("A", 1.0), ("S", 1.0), ("D", 1.0), ("F", 1.0), ("G", 1.0), ("H", 1.0), ("J", 1.0), ("K", 1.0), ("L", 1.0), (";", 1.0), ("'", 1.0), ("Enter", 2.0)],
            [("Shift", 2.5), ("Z", 1.0), ("X", 1.0), ("C", 1.0), ("V", 1.0), ("B", 1.0), ("N", 1.0), ("M", 1.0), (",", 1.0), (".", 1.0), ("/", 1.0), ("Shift", 2.5)],
            [("Ctrl", 1.75), (" ", 1.0), ("Alt", 1.0), ("Space", 7.5), ("Alt", 1.0), (" ", 1.0), ("Ctrl", 1.75)],
        ]

        unit_pixels = 12
        unit_scale = 4
        base_key_height = 44
        special_labels = {
            "Backspace": "←",
            "Tab": "Tab",
            "Caps": "Caps Lock",
            "Enter": "Enter",
            "Shift": "Shift",
            "Ctrl": "Ctrl",
            "Alt": "Alt",
            "Space": "Space",
        }

        tamil_base_font = self._keyboard_font_sizes['tamil_base']
        english_font = self._keyboard_font_sizes['english']
        tamil_shift_font = self._keyboard_font_sizes['tamil_shift']
        special_font = self._keyboard_font_sizes['special']

        for row_index, row in enumerate(rows):
            col = 0
            for key, size in row:
                start_col = col
                span = int(size * unit_scale)
                if key is None:
                    col += span
                    continue
                display = self._keycaps_map.get(key, (key, None))
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setTextFormat(Qt.RichText)
                
                key_width = int(unit_pixels * size * unit_scale)
                key_height = base_key_height

                label.setMinimumHeight(key_height)
                label.setMinimumWidth(0)

                if key in special_labels:
                    label.setText(html.escape(special_labels[key]))
                    style = self._build_key_style(key, special_font, font_weight=500)
                    label.setStyleSheet(style)
                    self._key_base_style_by_label[label] = style
                else:
                    english = html.escape(key)
                    tamil_base = html.escape(display[0]) if display[0] else ""
                    tamil_shift = html.escape(display[1]) if display[1] else ""
                    style = self._build_key_style(key, base_font_size, font_weight=500)
                    label.setStyleSheet(style)
                    self._key_base_style_by_label[label] = style
                    label.setText(
                        '<table width="100%" height="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">'
                            '<tr>'
                                f'<td style="padding-right:3px; vertical-align:top; text-align:left; '
                                f'font-family:\'{QApplication.font().family()}\', sans-serif; '
                                f'font-size:{english_font}px; color:{colors["text_primary"]}; ">{english}</td>'

                                '<td style="width:5px;"></td>'

                                f'<td style="padding-left:3px; vertical-align:top; text-align:right; '
                                f'font-family:\'{QApplication.font().family()}\', sans-serif; '
                                f'font-size:{tamil_shift_font}px; color:{colors["text_primary"]}; ">{tamil_shift}</td>'
                            '</tr>'

                            '<tr>'
                                f'<td colspan="3" style="vertical-align:bottom; text-align:left; '
                                f'font-family:\'{QApplication.font().family()}\', sans-serif; '
                                f'font-size:{tamil_base_font}px; font-weight:600; color:{colors["text_primary"]}; ">{tamil_base}</td>'
                            '</tr>'
                        '</table>'
                    )

                grid.addWidget(label, row_index, col, 1, span)
                col += span

                if key == "Space":
                    self._key_labels["Space"] = label
                elif key not in {"Tab", "Caps", "Enter", "Backspace", "Ctrl", "Win", "Alt", "AltGr", "PrtSc"}:
                    self._key_labels[key.upper()] = label
                if key == "Shift":
                    self._shift_labels.append(label)
                    if row_index == 3 and start_col == 0:
                        self._left_shift_label = label
                    elif row_index == 3:
                        self._right_shift_label = label

        max_columns = max(sum(int(size * unit_scale) for _, size in row) for row in rows)
        for column in range(max_columns):
            grid.setColumnMinimumWidth(column, 2)
            grid.setColumnStretch(column, 1)

        grid.setContentsMargins(0, 0, 0, 0)
        return container
    
    def _rebuild_keyboard_labels(self) -> None:
        """Re-render the HTML content of all regular keyboard key labels with current font sizes."""
        if not self._keyboard_widget or not self._keyboard_font_sizes:
            return

        colors = self._get_theme_colors()
        tamil_base_font = self._keyboard_font_sizes.get('tamil_base', 18)
        english_font = self._keyboard_font_sizes.get('english', 14)
        tamil_shift_font = self._keyboard_font_sizes.get('tamil_shift', 14)

        special_keys = {"Space", "Tab", "Caps", "Enter", "Backspace", "Ctrl", "Alt", "Shift"}

        for key_name, label in self._key_labels.items():
            if key_name in special_keys:
                continue

            display = self._keycaps_map.get(key_name, (key_name, None))
            english = html.escape(key_name)
            tamil_base = html.escape(display[0]) if display[0] else ""
            tamil_shift = html.escape(display[1]) if display[1] else ""
            
            label.setText(
                '<table width="100%" height="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">'
                    '<tr>'
                        f'<td style="padding-right:3px; vertical-align:top; text-align:left; '
                        f'font-family:\'{QApplication.font().family()}\', sans-serif; '
                        f'font-size:{english_font}px; color:{colors["text_primary"]}; ">{english}</td>'
                        '<td style="width:5px;"></td>'
                        f'<td style="padding-left:3px; vertical-align:top; text-align:right; '
                        f'font-family:\'{QApplication.font().family()}\', sans-serif; '
                        f'font-size:{tamil_shift_font}px; color:{colors["text_primary"]}; ">{tamil_shift}</td>'
                    '</tr>'
                    '<tr>'
                        f'<td colspan="3" style="vertical-align:bottom; text-align:left; '
                        f'font-family:\'{QApplication.font().family()}\', sans-serif; '
                        f'font-size:{tamil_base_font}px; font-weight:600; color:{colors["text_primary"]}; ">{tamil_base}</td>'
                    '</tr>'
                '</table>'
            )

    def _clear_keyboard_highlight(self) -> None:
        """Restore all highlighted keys to their default style."""
        for label in self._highlighted_keys:
            base_style = self._key_base_style_by_label.get(label)
            if base_style:
                label.setStyleSheet(base_style)
        self._highlighted_keys = []

    def _highlight_key(self, label: QLabel, key_label: str = "", is_shift: bool = False) -> None:
        """Apply a coloured border highlight to a single keyboard key label."""
        font_px = self._keyboard_font_sizes.get('special', 18) if (is_shift or key_label in {"Shift", "Space", "Backspace", "Tab", "Caps", "Enter", "Ctrl", "Alt"}) else self._keyboard_font_sizes.get('base', 18)
        highlight_key = key_label or "Shift"
        border_color = self._highlight_border_color_for_key(highlight_key)
        style = self._build_key_style(highlight_key, font_px, border_px=4, border_color=border_color, font_weight=500)
        label.setStyleSheet(style)
        self._highlighted_keys.append(label)

    def _update_keyboard_hint(self) -> None:
        """Highlight the next expected key and update the finger-guidance label."""
        if not self._session:
            self._clear_keyboard_highlight()
            if self._finger_guidance_label:
                self._finger_guidance_label.setText("")
                self._finger_guidance_label.setVisible(False)
            return

        if self._keystroke_index < len(self._keystroke_sequence):
            key_label, needs_shift = self._keystroke_sequence[self._keystroke_index]
            self._clear_keyboard_highlight()
            
            if key_label == ' ' or key_label == 'Space':
                key_label = "Space"
            
            if key_label in self._key_labels:
                self._highlight_key(self._key_labels[key_label], key_label=key_label)
            if needs_shift:
                side = self._shift_side_for_key(key_label)
                shift_label = self._right_shift_label if side == 'right' else self._left_shift_label
                if shift_label is not None:
                    self._highlight_key(shift_label, key_label="Shift", is_shift=True)
                else:
                    for s in self._shift_labels:
                        self._highlight_key(s, key_label="Shift", is_shift=True)
            
            if self._finger_guidance_label:
                english_finger, tamil_finger = self._get_finger_name(key_label, needs_shift)
                if needs_shift:
                    shift_side = self._shift_side_for_key(key_label)
                    guidance_text = f"<div style='text-align: center;'>Hold {shift_side.capitalize()} Shift<br/>{english_finger}<br/>{tamil_finger}</div>"
                else:
                    guidance_text = f"<div style='text-align: center;'>Use {english_finger}<br/>{tamil_finger}</div>"
                self._finger_guidance_label.setText(guidance_text)
                self._finger_guidance_label.setVisible(True)
        else:
            colors = self._get_theme_colors()
            self._clear_keyboard_highlight()
            if "Space" in self._key_labels:
                space_label = self._key_labels["Space"]
                font_px = self._keyboard_font_sizes.get('special', 18)
                border_color = self._highlight_border_color_for_key("Space")
                space_label.setStyleSheet(f"""
                    QLabel {{
                        background: {colors['success_bg']};
                        color: #ffffff;
                        border: 4px solid {border_color};
                        border-radius: 6px;
                        padding: 12px 8px;
                        font-family: '{QApplication.font().family()}', sans-serif;
                        font-size: {font_px}px;
                        font-weight: 500;
                    }}
                """)
                self._highlighted_keys.append(space_label)
            
            if self._finger_guidance_label:
                english_finger, tamil_finger = self._get_finger_name("Space", False)
                guidance_text = f"Press Space to continue<br/>Use {english_finger}<br/>{tamil_finger}"
                self._finger_guidance_label.setText(guidance_text)
                self._finger_guidance_label.setVisible(True)
    
    def _map_char_to_key(self, char: str) -> tuple[str, bool]:
        """Return ``(key_label, needs_shift)`` for a non-Tamil character."""
        if char == " ":
            return "Space", False

        if char.isalpha():
            return char.upper(), char.isupper()

        shift_map = {
            "!": ("1", True),
            "@": ("2", True),
            "#": ("3", True),
            "$": ("4", True),
            "%": ("5", True),
            "^": ("6", True),
            "&": ("7", True),
            "*": ("8", True),
            "(": ("9", True),
            ")": ("0", True),
            "_": ("-", True),
            "+": ("=", True),
            "{": ("[", True),
            "}": ("]", True),
            "|": ("\\", True),
            ":": (";", True),
            "\"": ("'", True),
            "<": (",", True),
            ">": (".", True),
            "?": ("/", True),
            "~": ("`", True),
        }
        if char in shift_map:
            return shift_map[char]

        if char in {"`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/"}:
            return char.upper(), False

        return char.upper(), False

    def _load_tamil99_maps(self) -> tuple[dict[str, tuple[str, Optional[str]]], dict[str, str]]:
        """Parse the m17n Tamil99 mapping file into keycap labels and char→keystroke maps."""
        mapping_path = Path(__file__).parent.parent / "data" / "m17n" / "ta-tamil99.mim"
        if not mapping_path.exists():
            return {}, {}

        text = mapping_path.read_text(encoding="utf-8", errors="ignore")
        pattern = re.compile(r'\("([^"]+)"\s+(\?[^)]+|"[^"]*")\)')

        keycaps: dict[str, tuple[str, Optional[str]]] = {}
        char_to_keystrokes: dict[str, str] = {}

        for match in pattern.finditer(text):
            key_seq = match.group(1)
            out = match.group(2)

            if out.startswith("?"):
                out_value = out[1:].replace('\\"', '"').replace("\\\\", "\\")
            else:
                out_value = out.strip('"').replace('\\"', '"').replace("\\\\", "\\")

            if not out_value:
                continue

            if len(key_seq) == 1:
                key_label = key_seq.upper() if key_seq.isalpha() else key_seq
                if key_seq.isalpha():
                    if key_seq == key_seq.lower():
                        base, shift = keycaps.get(key_label, (None, None))
                        if not base:
                            base = out_value
                        keycaps[key_label] = (base, shift)
                    else:
                        base, shift = keycaps.get(key_label, (None, None))
                        if not shift:
                            shift = out_value
                        keycaps[key_label] = (base, shift)
                else:
                    base, shift = keycaps.get(key_label, (None, None))
                    if not base:
                        base = out_value
                    keycaps[key_label] = (base, shift)

            # Reverse mapping: single Tamil character → shortest keystroke sequence.
            # Priority: single-key > pulli ending in 'f' > vowel-sign prefix '^' > shorter.
            if len(out_value) == 1:
                char_code = ord(out_value)
                if 0x0B80 <= char_code <= 0x0BFF:
                    should_store = False
                    if out_value not in char_to_keystrokes:
                        should_store = True
                    else:
                        current_seq = char_to_keystrokes[out_value]
                        if len(key_seq) == 1 and len(current_seq) > 1:
                            should_store = True
                        elif out_value == '்' and key_seq.endswith('f') and not current_seq.endswith('f'):
                            should_store = True
                        elif 0x0BBE <= char_code <= 0x0BFF and key_seq.startswith('^') and not current_seq.startswith('^'):
                            should_store = True
                        elif len(key_seq) < len(current_seq):
                            should_store = True
                    
                    if should_store:
                        char_to_keystrokes[out_value] = key_seq

        tamil_digits = {
            "1": "௧",
            "2": "௨",
            "3": "௩",
            "4": "௪",
            "5": "௫",
            "6": "௬",
            "7": "௭",
            "8": "௮",
            "9": "௯",
            "0": "௦",
        }
        for digit, tamil_digit in tamil_digits.items():
            base, shift = keycaps.get(digit, (None, None))
            if not base:
                base = tamil_digit
            keycaps[digit] = (base, shift)
            char_to_keystrokes.setdefault(tamil_digit, digit)

        return keycaps, char_to_keystrokes

    def _update_task_display_for_typed(self, typed: str, target: str, is_error: bool) -> None:
        """Convenience wrapper that resets the display offset and re-renders."""
        if not target:
            return
        self._task_display_offset = 0
        self._render_task_display(typed, target, is_error)

    def _render_task_display(self, typed: str, target: str, is_error: bool) -> None:
        """Update the letter-sequence widget, hero label, and rich-text task display."""
        if not target:
            self.task_display.setText("")
            if self._letter_sequence_widget is not None:
                self._letter_sequence_widget.set_letters([])
                self._letter_sequence_widget.set_current(0)
            if self._hero_letter_label is not None:
                self._hero_letter_label.setText("")
            return

        colors = self._get_theme_colors()

        letters = list(target)
        match_len = 0
        for i in range(min(len(typed or ""), len(target))):
            if i < len(typed) and i < len(target) and typed[i] == target[i]:
                match_len = i + 1
            else:
                break
        if self._letter_sequence_widget is not None:
            self._letter_sequence_widget.set_letters(letters)
            self._letter_sequence_widget.set_current(match_len)
        if self._hero_letter_label is not None:
            current_char = target[match_len] if match_len < len(target) else ""
            self._hero_letter_label.setText(current_char)
        
        if typed and typed == target:
            completed = html.escape(target)
            html_text = f'<span style="color:{colors["success"]};">{completed}</span>'
            self.task_display.setText(html_text)
            return
        
        typed_len = len(typed) if typed else 0
        target_len = len(target)
        
        if typed_len >= target_len:
            completed = html.escape(target)
            html_text = f'<span style="color:{colors["success"]};">{completed}</span>'
            self.task_display.setText(html_text)
            return
        
        match_len = 0
        for i in range(min(typed_len, target_len)):
            if i < len(typed) and i < len(target) and typed[i] == target[i]:
                match_len = i + 1
            else:
                break
        
        completed_text = target[:match_len] if match_len > 0 else ""
        remaining_text = target[match_len:] if match_len < target_len else ""
        
        if remaining_text:
            space_pos = remaining_text.find(' ')
            if space_pos > 0:
                current_char = remaining_text[:space_pos]
                remaining = remaining_text[space_pos:]
            elif space_pos == 0:
                current_char = ' '
                remaining = remaining_text[1:]
            else:
                current_char = remaining_text
                remaining = ""
        else:
            current_char = ""
            remaining = ""
        
        completed_escaped = html.escape(completed_text)
        current_char_escaped = html.escape(current_char)
        remaining_escaped = html.escape(remaining)
        
        if not current_char and not remaining:
            html_text = f'<span style="color:{colors["success"]};">{completed_escaped}</span>'
        else:
            current_style = f"background:{colors['highlight_bg']}; color:{colors['highlight']}; font-weight:600; padding:2px 4px; border-radius:4px;"
            if is_error:
                current_style = f"background:{colors['error_bg']}; color:{colors['error']}; font-weight:600; padding:2px 4px; border-radius:4px;"
            
            html_text = (
                f'<span style="color:{colors["success"]};">{completed_escaped}</span>'
                f'<span style="{current_style}">{current_char_escaped}</span>'
                f'<span style="color:{colors["text_muted"]};">{remaining_escaped}</span>'
            )

        self.task_display.setText(html_text)

    def _set_input_error_state(self, is_error: bool) -> None:
        """Toggle the hidden input box border between normal and error styles."""
        if self._input_has_error == is_error:
            return
        self._input_has_error = is_error
        colors = self._get_theme_colors()
        if is_error:
            self.input_box.setStyleSheet(f"""
                QLineEdit {{
                    background: {colors['bg_input']};
                    color: {colors['text_primary']};
                    border: 2px solid {colors['error']};
                    border-radius: 12px;
                    padding: 24px 28px;
                    font-size: 26px;
                    font-weight: 400;
                    font-family: '{QApplication.font().family()}', sans-serif;
                }}
            """)
        else:
            self.input_box.setStyleSheet(f"""
                QLineEdit {{
                    background: {colors['bg_input']};
                    color: {colors['text_primary']};
                    border: 1px solid {colors['border_light']};
                    border-radius: 12px;
                    padding: 24px 28px;
                    font-size: 26px;
                    font-weight: 400;
                    font-family: '{QApplication.font().family()}', sans-serif;
                }}
                QLineEdit:focus {{
                    border: 2px solid {colors['highlight']};
                    background: {colors['bg_container']};
                }}
            """)

    def _apply_responsive_fonts(self) -> None:
        """Set initial font sizes for the task display and input box based on screen height."""
        screen = self.screen()
        if screen is None:
            return
        height = screen.availableGeometry().height()
        task_size = max(16.0, height * 0.035)
        input_size = max(15.0, height * 0.03)

        task_font = QFont(QApplication.font().family())
        task_font.setPointSizeF(task_size)
        self.task_display.setFont(task_font)

        input_font = QFont(QApplication.font().family())
        input_font.setPointSizeF(input_size)
        self.input_box.setFont(input_font)

        self.task_display.setMinimumHeight(int(task_size * 2.2))
        self.input_box.setMinimumHeight(int(input_size * 2.2))
