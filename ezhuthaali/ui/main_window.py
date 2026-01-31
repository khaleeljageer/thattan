from __future__ import annotations

from dataclasses import dataclass
import html
import re
import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QSize, QPropertyAnimation
from PySide6.QtGui import QFont, QShortcut, QKeyEvent, QPixmap, QGuiApplication, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ezhuthaali.core.levels import LevelRepository, Level
from ezhuthaali.core.progress import ProgressStore
from ezhuthaali.core.session import TypingSession, TaskResult
from ezhuthaali.core.keystroke_tracker import KeystrokeTracker, Tamil99KeyboardLayout


@dataclass
class LevelState:
    level: Level
    unlocked: bool
    completed: int


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


class MainWindow(QMainWindow):
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
        self._task_display_offset: int = 0
        self._unlock_all_levels = os.environ.get("EZUTHALI_UNLOCK_ALL") == "1"
        self._input_has_error = False
        
        # Gamification stats
        self._current_streak: int = 0
        self._best_streak: int = 0
        self._total_score: int = 0
        self._combo_multiplier: float = 1.0
        self._consecutive_correct: int = 0
        
        # Keystroke tracking
        self._keystroke_tracker = KeystrokeTracker()
        self._tamil99_layout = Tamil99KeyboardLayout()
        self._keycaps_map, self._char_to_key = self._load_tamil99_maps()
        self._keystroke_sequence: list[tuple[str, bool]] = []  # (key, needs_shift)
        self._keystroke_index: int = 0
        self._char_to_keystroke_map: dict[int, int] = {}  # char_index -> keystroke_index
        self._typed_keystrokes: list[str] = []  # Track actual keys pressed
        self._typed_tamil_text: str = ""  # Track typed Tamil text
        
        # Store references for adaptive layout
        self._keyboard_widget: Optional[QWidget] = None
        self._hands_image_label: Optional[QLabel] = None
        self._original_hands_pixmap: Optional[QPixmap] = None
        self._bottom_container: Optional[QWidget] = None
        self._keyboard_font_sizes: dict[str, int] = {}  # Store current font sizes
        self._finger_guidance_label: Optional[QLabel] = None
        self._key_base_style_by_label: dict[QLabel, str] = {}
        
        # Background SVG
        self._background_svg_path: Optional[Path] = None
        self._background_svg_renderer: Optional[QSvgRenderer] = None
        self._background_label: Optional[QLabel] = None
        self._background_update_timer: Optional[QTimer] = None
        self._background_last_render_key: Optional[tuple[int, int, float]] = None

        # Invalid input overlay (red flash)
        self._error_overlay: Optional[QWidget] = None
        self._error_overlay_effect: Optional[QGraphicsOpacityEffect] = None
        self._error_overlay_anim: Optional[QPropertyAnimation] = None
        
        # Finger mapping for QWERTY/Tamil99 layout
        self._key_to_finger = self._build_finger_mapping()

        self._build_ui()
        self._refresh_levels_list()
        QTimer.singleShot(0, self.showMaximized)

    
    def _build_finger_mapping(self) -> dict[str, tuple[str, str]]:
        """Build mapping from key to (hand, finger) tuple.
        
        Returns:
            dict mapping key name to (hand, finger) where:
            - hand: 'left' or 'right'
            - finger: 'thumb', 'index', 'middle', 'ring', 'pinky'
        """
        mapping = {}
        
        # Left hand - Pinky
        for key in ['`', '1', 'Q', 'A', 'Z', 'TAB', 'CAPS']:
            mapping[key.upper()] = ('left', 'pinky')
        mapping['SHIFT'] = ('left', 'pinky')  # Left shift (default, can be overridden)
        
        # Left hand - Ring
        for key in ['2', 'W', 'S', 'X']:
            mapping[key.upper()] = ('left', 'ring')
        
        # Left hand - Middle
        for key in ['3', 'E', 'D', 'C']:
            mapping[key.upper()] = ('left', 'middle')
        
        # Left hand - Index
        for key in ['4', '5', 'R', 'T', 'F', 'G', 'V', 'B']:
            mapping[key.upper()] = ('left', 'index')
        
        # Left hand - Thumb (Space bar left side)
        mapping['SPACE'] = ('left', 'thumb')
        mapping[' '] = ('left', 'thumb')  # Space as character
        
        # Right hand - Index
        for key in ['6', '7', 'Y', 'U', 'H', 'J', 'N', 'M']:
            mapping[key.upper()] = ('right', 'index')
        
        # Right hand - Middle
        for key in ['8', 'I', 'K', ',']:
            mapping[key.upper()] = ('right', 'middle')
        
        # Right hand - Ring
        for key in ['9', 'O', 'L', '.']:
            mapping[key.upper()] = ('right', 'ring')
        
        # Right hand - Pinky
        for key in ['0', '-', '=', 'P', '[', ']', '\\', ';', "'", '/', 'ENTER', 'BACKSPACE']:
            mapping[key.upper()] = ('right', 'pinky')
        
        # Special keys - Right shift (typically used more often)
        mapping['SHIFT'] = ('right', 'pinky')  # Right shift is more common
        
        # Special keys
        mapping['CTRL'] = ('left', 'pinky')  # Left Ctrl
        mapping['ALT'] = ('left', 'thumb')  # Left Alt
        
        # Handle numeric row and symbols
        # These follow the same pattern as letters above them
        
        return mapping
    
    def _get_finger_name(self, key_label: str, needs_shift: bool = False) -> tuple[str, str]:
        """Get finger name for a key in both English and Tamil.
        
        Args:
            key_label: The key label (e.g., 'A', 'Space', 'Shift')
            needs_shift: Whether Shift is required
            
        Returns:
            tuple of (english_name, tamil_name)
        """
        # Handle Shift key separately
        if key_label.upper() == 'SHIFT':
            # If it's the Shift key itself, determine which shift based on context
            # For now, default to right shift (pinky)
            hand, finger = self._key_to_finger.get('SHIFT', ('right', 'pinky'))
        elif needs_shift:
            # Shift rule:
            # - If the actual key is typed with LEFT hand -> use RIGHT shift
            # - If the actual key is typed with RIGHT hand -> use LEFT shift
            key_hand, _key_finger = self._key_to_finger.get(key_label.upper(), ('right', 'index'))
            shift_hand = 'right' if key_hand == 'left' else 'left'
            hand, finger = (shift_hand, 'pinky')
        else:
            # Regular key - get finger mapping
            hand, finger = self._key_to_finger.get(key_label.upper(), ('right', 'index'))
        
        # Tamil finger names
        finger_names_tamil = {
            'thumb': 'கட்டைவிரல்',
            'index': 'சுட்டுவிரல்',
            'middle': 'நடுவிரல்',
            'ring': 'மோதிரவிரல்',
            'pinky': 'சிறுவிரல்'
        }
        
        # Tamil hand names
        hand_names_tamil = {
            'left': 'இடது',
            'right': 'வலது'
        }
        
        english_name = f"{hand.capitalize()} {finger.capitalize()}"
        tamil_name = f"{hand_names_tamil.get(hand, hand)} {finger_names_tamil.get(finger, finger)}"
        
        return (english_name, tamil_name)

    def _shift_side_for_key(self, key_label: str) -> str:
        """Return which Shift side to use for a given key label ('left' or 'right')."""
        key_hand, _ = self._key_to_finger.get(key_label.upper(), ('right', 'index'))
        return 'right' if key_hand == 'left' else 'left'

    def _get_theme_colors(self) -> dict:
        """Get light theme color palette"""
        return {
            # Background: neutral light grey with soft teal tint
            'bg_main': '#EEF6F6',
            'bg_container': 'rgba(255, 255, 255, 0.34)',
            'bg_card': 'rgba(255, 255, 255, 0.24)',
            'bg_input': 'rgba(255, 255, 255, 0.38)',
            'bg_hover': 'rgba(255, 255, 255, 0.46)',

            # Typing text: dark neutral
            'text_primary': '#1F2933',
            'text_secondary': '#334155',
            'text_muted': '#64748B',

            'border': 'rgba(15, 23, 42, 0.14)',
            'border_light': 'rgba(15, 23, 42, 0.10)',

            # Active character: accent (teal)
            'highlight': '#0F766E',
            'highlight_bg': 'rgba(15, 118, 110, 0.18)',

            'error': '#D64545',
            'error_bg': 'rgba(214, 69, 69, 0.18)',
            'success': '#2F855A',
            'success_bg': 'rgba(47, 133, 90, 0.18)',
            'progress': '#0F766E',

            # Kept for compatibility with older styles
            'key_bg': 'rgba(255, 255, 255, 0.22)',
            'key_highlight': '#0F766E',
            'key_highlight_bg': 'rgba(15, 118, 110, 0.18)',
            'key_shift': '#0F766E',
            'key_shift_bg': 'rgba(15, 118, 110, 0.18)',
        }

    def _get_finger_colors(self) -> dict[tuple[str, str], str]:
        """Finger color palette (hand, finger) -> hex color."""
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
        """Darken a hex color by multiplying RGB by factor (0..1)."""
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
        """Blend two #RRGGBB colors. t=0 -> a, t=1 -> b."""
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
        """Return background color for a given key label."""
        hand, finger = self._key_to_finger.get(key_label.upper(), ('right', 'index'))
        return self._get_finger_colors().get((hand, finger), '#5C96EB')

    def _muted_key_fill_color_for_key(self, key_label: str) -> str:
        """Muted/pastel version of the finger color for this key."""
        colors = self._get_theme_colors()
        base = self._finger_color_for_key(key_label)
        # Blend towards window background to mute the color
        return self._blend_hex_colors(base, colors['bg_main'], 0.62)

    def _highlight_border_color_for_key(self, key_label: str) -> str:
        """Border color for highlight that matches the finger palette (darker shade)."""
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

    def _calculate_keyboard_dimensions(self) -> tuple[float, int, int]:
        """Calculate keyboard aspect ratio and optimal size based on screen size.
        
        Uses optimal dimensions from 1920x1200 screen (1402x424) as reference
        and scales proportionally for other screen sizes.
        
        Returns:
            tuple: (aspect_ratio, min_width, min_height)
        """
        screen = QGuiApplication.primaryScreen()
        
        # Reference dimensions from 1920x1200 screen that looked good
        reference_screen_width = 1920
        reference_keyboard_width = 1402
        reference_keyboard_height = 424
        reference_ratio = reference_keyboard_width / reference_keyboard_height  # ≈ 3.31
        
        if screen is None:
            # Fallback to default dimensions if screen is not available
            return (reference_ratio, 980, int(980 / reference_ratio))
        
        screen_width = screen.availableGeometry().width()
        
        # Calculate scale factor based on screen width
        # Use screen width as primary dimension for scaling
        scale_factor = screen_width / reference_screen_width
        
        # Calculate keyboard dimensions for current screen
        # Ensure minimum size but scale up for larger screens
        min_width = max(980, int(reference_keyboard_width * scale_factor))
        min_height = int(min_width / reference_ratio)
        
        return (reference_ratio, min_width, min_height)

    def _build_ui(self) -> None:
        self.setWindowTitle("தட்டான் - தமிழ்99 பயிற்சி")
        self.setMinimumSize(1200, 800)
        
        colors = self._get_theme_colors()
        
        # Set fallback background color
        self.setStyleSheet(f"""
            QMainWindow {{ 
                background: {colors['bg_main']};
            }}
        """)
        
        # Setup background SVG
        background_svg_path = Path(__file__).parent.parent / "assets" / "background.svg"
        if background_svg_path.exists():
            self._background_svg_path = background_svg_path
            self._background_svg_renderer = QSvgRenderer(str(background_svg_path))
        
        root = QWidget()
        
        # Create background label for SVG (as child of main window to cover entire window)
        if self._background_svg_renderer:
            self._background_label = QLabel(self)
            self._background_label.setAlignment(Qt.AlignCenter)
            self._background_label.lower()  # Put it behind everything
            self._background_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)  # Allow clicks to pass through
            # During interactive resize, allow cheap scaling of last pixmap;
            # a debounced re-render will refresh it crisply.
            self._background_label.setScaledContents(True)

            # Debounce expensive SVG->pixmap renders on resize
            self._background_update_timer = QTimer(self)
            self._background_update_timer.setSingleShot(True)
            self._background_update_timer.timeout.connect(self._update_background)

        # Create invalid input overlay (as child of main window to cover entire window)
        self._error_overlay = QWidget(self)
        self._error_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._error_overlay.setStyleSheet("background-color: #EF6060;")
        self._error_overlay_effect = QGraphicsOpacityEffect(self._error_overlay)
        self._error_overlay_effect.setOpacity(0.0)
        self._error_overlay.setGraphicsEffect(self._error_overlay_effect)
        self._error_overlay.hide()
        # Create the animation ONCE and reuse it (prevents accumulating children)
        self._error_overlay_anim = QPropertyAnimation(self._error_overlay_effect, b"opacity", self)
        self._error_overlay_anim.setDuration(200)
        self._error_overlay_anim.setKeyValueAt(0.0, 0.0)
        self._error_overlay_anim.setKeyValueAt(0.2, 0.28)
        self._error_overlay_anim.setKeyValueAt(1.0, 0.0)
        self._error_overlay_anim.finished.connect(self._error_overlay.hide)
        
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)
        
        stats_header = QLabel("📊 முன்னேற்றம்")
        stats_header.setStyleSheet(f"""
            font-size: 15px; 
            font-weight: 600; 
            color: {colors['text_secondary']}; 
            padding: 8px 0px;
        """)
        left_panel.addWidget(stats_header)
        
        stats_container = QWidget()
        stats_container.setStyleSheet(f"""
            QWidget {{
                background: {colors['bg_container']};
                border-radius: 12px;
                padding: 16px;
                border: none;
            }}
        """)
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setSpacing(12)
        
        self.score_label = QLabel("புள்ளிகள்: 0")
        self.score_label.setStyleSheet(f"""
            background: {colors['bg_card']};
            color: {colors['text_primary']};
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            border-left: 3px solid {colors['text_muted']};
        """)
        stats_layout.addWidget(self.score_label)
        
        self.streak_label = QLabel("தொடர்ச்சி: 0")
        self.streak_label.setStyleSheet(f"""
            background: {colors['bg_card']};
            color: {colors['text_primary']};
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            border-left: 3px solid {colors['success']};
        """)
        stats_layout.addWidget(self.streak_label)
        
        self.best_streak_label = QLabel("சிறந்த தொடர்ச்சி: 0")
        self.best_streak_label.setStyleSheet(f"""
            background: {colors['bg_card']};
            color: {colors['text_primary']};
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            border-left: 3px solid {colors['highlight']};
        """)
        stats_layout.addWidget(self.best_streak_label)
        
        left_panel.addWidget(stats_container)
        
        level_header = QLabel("📚 நிலைகள்")
        level_header.setStyleSheet(f"""
            font-size: 16px; 
            font-weight: 600; 
            color: {colors['text_secondary']}; 
            padding: 12px 0px;
        """)
        left_panel.addWidget(level_header)
        
        self.levels_list = QListWidget()
        self.levels_list.setStyleSheet(f"""
            QListWidget {{
                background: {colors['bg_container']};
                border: none;
                border-radius: 12px;
                padding: 8px;
                color: {colors['text_primary']};
            }}
            QListWidget::item {{
                padding: 12px 14px;
                margin: 4px 0;
                border-radius: 8px;
                background: {colors['bg_card']};
                color: {colors['text_secondary']};
                border: 1px solid transparent;
                font-size: 14px;
                font-weight: 500;
            }}
            QListWidget::item:hover {{
                background: {colors['bg_hover']};
                border: 1px solid {colors['border_light']};
            }}
            QListWidget::item:selected {{
                background: {colors['highlight_bg']};
                color: {colors['text_primary']};
                font-weight: 600;
                border: 1px solid {colors['highlight']};
            }}
        """)
        self.levels_list.itemSelectionChanged.connect(self._on_level_selected)
        left_panel.addWidget(self.levels_list)

        self.level_status = QLabel("தொடங்க ஒரு நிலையைத் தேர்வு செய்யவும்.")
        self.level_status.setWordWrap(True)
        self.level_status.setStyleSheet(f"""
            background: {colors['bg_card']};
            color: {colors['text_muted']};
            padding: 12px 14px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 500;
            border: none;
        """)
        left_panel.addWidget(self.level_status)

        self.reset_button = QPushButton("↻ மீட்டமை")
        self.reset_button.setStyleSheet(f"""
            QPushButton {{
                background: {colors['bg_container']};
                color: {colors['text_muted']};
                padding: 10px 16px;
                border: none;
                border-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {colors['bg_hover']};
                color: {colors['text_secondary']};
            }}
            QPushButton:pressed {{
                background: {colors['bg_card']};
            }}
        """)
        self.reset_button.clicked.connect(self._reset_progress)
        left_panel.addWidget(self.reset_button)
        left_panel.addStretch(1)

        right_panel = QVBoxLayout()
        
        task_container = QWidget()
        task_container.setStyleSheet(f"""
            QWidget {{
                background: {colors['bg_container']};
                border-radius: 16px;
                padding: 24px;
                border: none;
            }}
        """)
        task_container_layout = QVBoxLayout(task_container)
        task_container_layout.setContentsMargins(0, 0, 0, 0)
        task_container_layout.setSpacing(12)
        
        self.combo_label = QLabel("")
        self.combo_label.setVisible(False)

        self.task_display = QLabel()
        self.task_display.setTextFormat(Qt.RichText)
        self.task_display.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.task_display.setStyleSheet(f"""
            background: {colors['bg_input']};
            color: {colors['text_primary']};
            border: none;
            border-radius: 12px;
            padding: 24px 28px;
            font-size: 26px;
            font-weight: 400;
            font-family: '{QApplication.font().family()}', sans-serif;
            min-height: 100px;
        """)
        self.task_display.setMinimumHeight(100)
        task_container_layout.addWidget(self.task_display)
        right_panel.addWidget(task_container)

        input_container = QWidget()
        input_container.setStyleSheet(f"""
            QWidget {{
                background: {colors['bg_container']};
                border-radius: 16px;
                padding: 24px;
                border: none;
            }}
        """)
        input_container_layout = QVBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        input_container_layout.setSpacing(12)
        
        self.input_box = QLineEdit()
        self.input_box.setMinimumHeight(100)
        self.input_box.setStyleSheet(f"""
            QLineEdit {{
                background: {colors['bg_input']};
                color: {colors['text_primary']};
                border: none;
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
        self.input_box.installEventFilter(self)
        self.input_box.setReadOnly(True)  # Prevent text input, we'll handle keys manually
        input_container_layout.addWidget(self.input_box)
        right_panel.addWidget(input_container)

        progress_container = QWidget()
        progress_container.setStyleSheet(f"""
            QWidget {{
                background: {colors['bg_container']};
                border-radius: 12px;
                padding: 16px;
                border: none;
            }}
        """)
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setSpacing(10)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 8px;
                text-align: center;
                background: {colors['bg_card']};
                height: 24px;
                font-weight: 500;
                font-size: 12px;
                color: {colors['text_muted']};
            }}
            QProgressBar::chunk {{
                background: {colors['progress']};
                border-radius: 7px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        right_panel.addWidget(progress_container)
        right_panel.addStretch(1)

        top_row = QHBoxLayout()
        top_row.setSpacing(20)
        top_row.addLayout(left_panel, 1)
        top_row.addLayout(right_panel, 3)
        layout.addLayout(top_row)

        # Single parent container for Finger UI and Keyboard
        self._bottom_container = QWidget()
        self._bottom_container.setStyleSheet(f"""
            background: transparent;
            border-radius: 16px;
            padding: 20px;
        """)
        bottom_row = QHBoxLayout(self._bottom_container)
        bottom_row.setSpacing(15)  # Small spacing between finger UI and keyboard
        bottom_row.setContentsMargins(0, 0, 0, 0)
        
        # Finger UI container on the left
        finger_ui_container = QWidget()
        finger_ui_layout = QVBoxLayout(finger_ui_container)
        finger_ui_layout.setSpacing(10)
        finger_ui_layout.setContentsMargins(0, 0, 0, 0)
        finger_ui_layout.setAlignment(Qt.AlignCenter)  # Center all contents
        
        # Finger guidance label
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
        self._finger_guidance_label.setVisible(False)  # Hidden until session starts
        finger_ui_layout.addWidget(self._finger_guidance_label, 0, Qt.AlignCenter)
        
        # Hands image - centered to match text layout
        hands_image_path = Path(__file__).parent.parent / "assets" / "hands.png"
        if hands_image_path.exists():
            self._hands_image_label = QLabel()
            self._original_hands_pixmap = QPixmap(str(hands_image_path))
            
            # Initial scale - will be adjusted on resize
            initial_max_width = 600
            pixmap = self._original_hands_pixmap
            if pixmap.width() > initial_max_width:
                pixmap = pixmap.scaledToWidth(initial_max_width, Qt.SmoothTransformation)
            
            self._hands_image_label.setPixmap(pixmap)
            self._hands_image_label.setAlignment(Qt.AlignCenter)
            # Remove background - parent container provides it
            self._hands_image_label.setStyleSheet("background: transparent; padding: 0px;")
            # Use flexible size policy to allow shrinking
            self._hands_image_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            self._hands_image_label.setMinimumWidth(200)  # Minimum to prevent too small
            self._hands_image_label.setMinimumHeight(100)  # Minimum height
            # Center the hands image to align with the text layout above
            finger_ui_layout.addWidget(self._hands_image_label, 0, Qt.AlignCenter)
        
        bottom_row.addWidget(finger_ui_container, 1)  # Stretch factor 1
        
        # Keyboard on the right
        self._keyboard_widget = self._build_keyboard()
        
        # Remove background - parent container provides it
        self._keyboard_widget.setStyleSheet("background: transparent; border: none; padding: 0px;")
        
        # Use flexible size policy - allow shrinking below minimum if needed
        self._keyboard_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Set a very small minimum to allow maximum flexibility
        self._keyboard_widget.setMinimumSize(400, 150)
        bottom_row.addWidget(self._keyboard_widget, 2)  # Stretch factor 2 (keyboard gets more space)
        
        layout.addWidget(self._bottom_container)
        
        # Connect resize event to adjust layout dynamically
        self._bottom_container.installEventFilter(self)
        
        self.setCentralWidget(root)
        
        # Update background after window is set up
        self._update_background()
        self._update_error_overlay_geometry()

        self.start_shortcut = QShortcut(Qt.CTRL | Qt.Key_Return, self)
        self.start_shortcut.activated.connect(self._submit_task)

        self._apply_responsive_fonts()

    def _refresh_levels_list(self) -> None:
        self.levels_list.clear()
        level_states = self._build_level_states()
        for state in level_states:
            task_count = len(state.level.tasks)
            text = f"{state.level.name}"
            if not state.unlocked:
                text += " (பூட்டப்பட்டது)"
            elif state.completed >= task_count:
                text += " (முடிந்தது)"
            else:
                text += f" ({state.completed}/{task_count})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, state.level.key)
            if not state.unlocked:
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                item.setForeground(Qt.gray)
                item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            self.levels_list.addItem(item)

        if level_states:
            self.levels_list.setCurrentRow(0)

    def _build_level_states(self) -> list[LevelState]:
        levels = self._levels_repo.all()
        states: list[LevelState] = []
        previous_completed = True
        for level in levels:
            progress = self._progress_store.get_level_progress(level.key)
            task_count = len(level.tasks)
            unlocked = True
            states.append(LevelState(level=level, unlocked=unlocked, completed=progress.completed))
            previous_completed = progress.completed >= task_count
        return states

    def _on_level_selected(self) -> None:
        items = self.levels_list.selectedItems()
        if not items:
            return
        level_key = items[0].data(Qt.UserRole)
        level = self._levels_repo.get(level_key)
        progress = self._progress_store.get_level_progress(level_key)
        task_count = len(level.tasks)
        self._current_level = level
        self._session = None
        self.progress_bar.setRange(0, task_count)
        self.progress_bar.setValue(progress.completed)
        self.task_display.setText("")
        self.input_box.setText("")
        self.level_status.setText(
            f"{level.name} பயிற்சி வரிகள்: {task_count}. "
            f"முடிந்தது: {progress.completed}/{task_count}."
        )
        if progress.completed >= task_count:
            pass
        self._start_session(level, progress.completed)

    def _start_session(self, level: Level, start_index: int) -> None:
        task_count = len(level.tasks)
        if start_index >= task_count:
            start_index = 0
        self._session = TypingSession(level.tasks, start_index=start_index)
        # Set progress bar range to match task count
        self.progress_bar.setRange(0, task_count)
        # Reset keystroke tracker for new session
        self._keystroke_tracker.reset_session()
        self._update_gamification_stats()
        self._load_current_task()

    def _load_current_task(self) -> None:
        if not self._session:
            return
        if self._session.is_complete():
            self.task_display.setText("நிலை முடிந்தது!")
            return
        self._current_task_text = self._session.current_task()
        self._task_display_offset = 0
        # Build keystroke sequence using Tamil99 layout
        self._keystroke_sequence = self._tamil99_layout.get_keystroke_sequence(self._current_task_text)
        self._keystroke_index = 0
        self._typed_keystrokes = []
        self._typed_tamil_text = ""  # Track typed Tamil text
        self._keystroke_to_char_map: dict[int, int] = {}  # keystroke_idx -> char_idx
        self._build_keystroke_to_char_map()  # Build mapping from keystroke indices to character indices
        self._render_task_display("", self._current_task_text, is_error=False)
        self._set_input_text("")
        self.input_box.setFocus()
        self._update_keyboard_hint()
    
    def _build_keystroke_to_char_map(self) -> None:
        """Build mapping from keystroke indices to character indices"""
        self._keystroke_to_char_map = {}
        keystroke_idx = 0
        target = self._current_task_text
        i = 0
        
        # Process text the same way get_keystroke_sequence does
        # to correctly handle combined characters
        while i < len(target):
            char = target[i]
            
            if char == ' ':
                self._keystroke_to_char_map[keystroke_idx] = i
                keystroke_idx += 1
                i += 1
            # Check for combined characters first (same logic as get_keystroke_sequence)
            elif i + 1 < len(target):
                combined = char + target[i + 1]
                if combined in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                    # Found combined character (e.g., "து" = "ld")
                    key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[combined]
                    # Map all keystrokes for this combined character to the first character index
                    for _ in key_seq:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1
                    i += 2  # Skip both characters
                    continue
            # Single character
            if char in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[char]
                # Handle special prefixes
                if key_seq.startswith('^#'):
                    # Tamil numeral: ^#1
                    self._keystroke_to_char_map[keystroke_idx] = i
                    keystroke_idx += 1  # ^
                    self._keystroke_to_char_map[keystroke_idx] = i
                    keystroke_idx += 1  # #
                    if len(key_seq) > 2:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1  # number
                elif key_seq.startswith('^'):
                    # Vowel sign: ^q
                    self._keystroke_to_char_map[keystroke_idx] = i
                    keystroke_idx += 1  # ^
                    if len(key_seq) > 1:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1  # vowel key
                else:
                    # Regular sequence
                    for _ in key_seq:
                        self._keystroke_to_char_map[keystroke_idx] = i
                        keystroke_idx += 1
                i += 1
            else:
                # Fallback
                self._keystroke_to_char_map[keystroke_idx] = i
                keystroke_idx += 1
                i += 1

    def _set_input_text(self, text: str) -> None:
        self._auto_submit_block = True
        self.input_box.setText(text)
        self.input_box.setCursorPosition(len(text))
        self._auto_submit_block = False
        self._set_input_error_state(False)

    def eventFilter(self, obj, event) -> bool:
        """Filter key events to track individual keystrokes and resize events"""
        if obj == self.input_box and event.type() == event.Type.KeyPress:
            return self._on_key_press(event)
        elif obj == self._bottom_container and event.type() == event.Type.Resize:
            # Handle resize events for adaptive layout
            QTimer.singleShot(10, self._adjust_adaptive_layout)  # Delay to ensure size is updated
        return super().eventFilter(obj, event)
    
    def resizeEvent(self, event) -> None:
        """Handle window resize to adjust keyboard and finger UI"""
        super().resizeEvent(event)
        self._schedule_background_update()
        self._update_error_overlay_geometry()
        QTimer.singleShot(10, self._adjust_adaptive_layout)  # Delay to ensure size is updated
    
    def _adjust_adaptive_layout(self) -> None:
        """Adjust keyboard and finger UI sizes based on available space"""
        if not self._keyboard_widget or not self._bottom_container:
            return
        
        # Calculate available width (accounting for margins and spacing)
        available_width = self._bottom_container.width() - 40  # Padding
        if available_width <= 0:
            return
        
        # Calculate space allocation
        # Reserve minimum space for finger UI, rest for keyboard
        min_hands_width = 200
        max_hands_width = 600
        hands_ratio = 0.3  # Finger UI should take ~30% of space
        
        # Calculate ideal widths
        ideal_hands_width = min(max_hands_width, max(min_hands_width, int(available_width * hands_ratio)))
        keyboard_width = available_width - ideal_hands_width - 15  # 15px spacing
        
        # Ensure keyboard has reasonable minimum width
        min_keyboard_width = 400  # Reduced from 600 to allow more flexibility
        if keyboard_width < min_keyboard_width and available_width > min_keyboard_width + min_hands_width + 15:
            # Only enforce minimum if we have enough total space
            keyboard_width = min_keyboard_width
            ideal_hands_width = available_width - keyboard_width - 15
            ideal_hands_width = max(min_hands_width, ideal_hands_width)
        
        # Adjust hands image if needed
        if self._hands_image_label and self._original_hands_pixmap:
            current_width = self._hands_image_label.width()
            if abs(ideal_hands_width - current_width) > 10:  # Only update if significant change
                scaled_pixmap = self._original_hands_pixmap.scaledToWidth(
                    ideal_hands_width, Qt.SmoothTransformation
                )
                self._hands_image_label.setPixmap(scaled_pixmap)
                self._hands_image_label.setMinimumWidth(ideal_hands_width)
                self._hands_image_label.setMaximumWidth(ideal_hands_width)
        
        # Update keyboard font sizes based on actual width
        if keyboard_width > 0:
            self._update_keyboard_font_sizes(keyboard_width)
    
    def _update_keyboard_font_sizes(self, keyboard_width: int) -> None:
        """Update keyboard font sizes based on available width"""
        if not self._keyboard_widget:
            return
        
        # Reference: 1402px keyboard width = 18px base font
        # Scale font proportionally with keyboard width
        reference_keyboard_width = 1402
        font_scale = keyboard_width / reference_keyboard_width
        base_font_size = max(12, int(18 * font_scale))
        
        # Calculate derived font sizes
        tamil_base_font = base_font_size
        english_font = max(7, int(base_font_size * 0.75))
        tamil_shift_font = max(9, int(base_font_size * 0.75))
        special_font = max(9, int(base_font_size * 0.78))
        
        # Only update if font sizes changed significantly
        if (self._keyboard_font_sizes.get('base', 0) != base_font_size or
            abs(self._keyboard_font_sizes.get('base', 18) - base_font_size) > 1):
            
            # Store font sizes
            self._keyboard_font_sizes = {
                'base': base_font_size,
                'tamil_base': tamil_base_font,
                'english': english_font,
                'tamil_shift': tamil_shift_font,
                'special': special_font
            }
            
            # Rebuild keyboard HTML with new font sizes
            self._rebuild_keyboard_labels()
            
            # Update special key labels
            colors = self._get_theme_colors()
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
            
            # Update Space key
            if "Space" in self._key_labels:
                space_label = self._key_labels["Space"]
                style = self._build_key_style("Space", special_font, font_weight=500)
                space_label.setStyleSheet(style)
                self._key_base_style_by_label[space_label] = style
            
            # Update shift labels
            for shift_label in self._shift_labels:
                style = self._build_key_style("Shift", special_font, font_weight=500)
                shift_label.setStyleSheet(style)
                self._key_base_style_by_label[shift_label] = style
    
    def _on_key_press(self, event: QKeyEvent) -> bool:
        """Handle individual key press events"""
        if not self._session:
            return False
        
        key = event.key()
        text = event.text()
        
        if key == Qt.Key.Key_Space:
            if self._keystroke_index >= len(self._keystroke_sequence):
                self._submit_task_from_keystrokes()
                return True
            if self._keystroke_index >= len(self._keystroke_sequence):
                return False
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
            self._update_display_from_keystrokes()
            self._flash_invalid_input_overlay()
        
        self._update_keyboard_hint()
        self._update_stats_from_tracker()
        
        return True

    def _update_error_overlay_geometry(self) -> None:
        if not self._error_overlay:
            return
        s = self.size()
        self._error_overlay.setGeometry(0, 0, s.width(), s.height())

    def _flash_invalid_input_overlay(self, duration_ms: int = 200) -> None:
        """Flash a short red overlay on invalid input."""
        if not self._error_overlay or not self._error_overlay_effect or not self._error_overlay_anim:
            return
        
        # Stop any running animation (we reuse the same object)
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
        """Reconstruct Tamil text from typed keystrokes"""
        # Process the target text and match keystrokes to characters
        target = self._current_task_text
        typed_ks_count = len(self._typed_keystrokes)
        
        # Reconstruct by processing target text character by character
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
            
            # Check for combined characters first
            elif i + 1 < len(target):
                combined = char + target[i + 1]
                if combined in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                    key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[combined]
                    # Check if we have enough keystrokes for this combined character
                    if keystroke_idx + len(key_seq) <= typed_ks_count:
                        # Verify the keystrokes match
                        matches = True
                        for j, expected_key in enumerate(key_seq):
                            typed_key = self._typed_keystrokes[keystroke_idx + j].upper()
                            expected_key_upper = expected_key.upper()
                            if typed_key != expected_key_upper:
                                matches = False
                                break
                        if matches:
                            reconstructed += combined
                            keystroke_idx += len(key_seq)
                            i += 2
                            continue
            
            # Single character
            if char in self._tamil99_layout.CHAR_TO_KEYSTROKES:
                key_seq = self._tamil99_layout.CHAR_TO_KEYSTROKES[char]
                # Handle special prefixes
                if key_seq.startswith('^#'):
                    # Tamil numeral: ^#1
                    required_keys = 3 if len(key_seq) > 2 else 2
                    if keystroke_idx + required_keys <= typed_ks_count:
                        # Verify keystrokes match
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
                    # Vowel sign: ^q
                    required_keys = 2 if len(key_seq) > 1 else 1
                    if keystroke_idx + required_keys <= typed_ks_count:
                        # Verify keystrokes match
                        if self._typed_keystrokes[keystroke_idx].upper() == '^':
                            if len(key_seq) > 1:
                                if (keystroke_idx + 1 < typed_ks_count and
                                    self._typed_keystrokes[keystroke_idx + 1].upper() == key_seq[1].upper()):
                                    reconstructed += char
                                    keystroke_idx += required_keys
                                    i += 1
                                    continue
                else:
                    # Regular sequence
                    if keystroke_idx + len(key_seq) <= typed_ks_count:
                        # Verify keystrokes match
                        matches = True
                        for j, expected_key in enumerate(key_seq):
                            typed_key = self._typed_keystrokes[keystroke_idx + j].upper()
                            expected_key_upper = expected_key.upper()
                            if typed_key != expected_key_upper:
                                matches = False
                                break
                        if matches:
                            reconstructed += char
                            keystroke_idx += len(key_seq)
                            i += 1
                            continue
            else:
                # Fallback for punctuation and other characters not in CHAR_TO_KEYSTROKES
                # Check if the next keystroke matches this character
                if keystroke_idx < typed_ks_count:
                    typed_key = self._typed_keystrokes[keystroke_idx]
                    # Get the expected key for this character using _map_char_to_key
                    key_label, needs_shift = self._map_char_to_key(char)
                    
                    # Check if typed key matches the expected key
                    # Normalize for comparison (handle both direct match and key label match)
                    if (typed_key == char or 
                        typed_key.upper() == char.upper() or
                        typed_key.upper() == key_label.upper()):
                        reconstructed += char
                        keystroke_idx += 1
                        i += 1
                        continue
            
            # If we can't match, break
            break
        
        self._typed_tamil_text = reconstructed
    
    def _update_display_from_keystrokes(self) -> None:
        """Update the display based on typed keystrokes"""
        target = self._current_task_text
        
        # Use the tracked Tamil text
        typed_text = self._typed_tamil_text
        
        is_error = self._input_has_error
        self._update_task_display_for_typed(typed_text, target, is_error)
        
        # Update input box to show the typed Tamil text
        self._set_input_text(typed_text)
    
    def _submit_task_from_keystrokes(self) -> None:
        """Submit task when all keystrokes are completed"""
        if not self._session:
            return
        
        typed = self._typed_tamil_text if self._typed_tamil_text else self._current_task_text
        self._submit_task(typed)
        
        self._typed_keystrokes = []
        self._typed_tamil_text = ""
        self._keystroke_index = 0
        self._input_has_error = False
    
    def _update_stats_from_tracker(self) -> None:
        """Update UI stats from keystroke tracker"""
        summary = self._keystroke_tracker.get_session_summary()
        self._update_gamification_stats()
    
    def _on_input_changed(self, text: str) -> None:
        """Legacy method - no longer used but kept for compatibility"""
        pass

    def _submit_task(self, typed: Optional[str] = None) -> None:
        if not self._session or not self._current_level:
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
        
        self._update_gamification_stats()
    
    def _update_gamification_stats(self) -> None:
        """Update gamification UI elements - peaceful style"""
        self.score_label.setText(f"புள்ளிகள்: {self._total_score:,}")
        self.streak_label.setText(f"தொடர்ச்சி: {self._current_streak}")
        self.best_streak_label.setText(f"சிறந்த தொடர்ச்சி: {self._best_streak}")
        
        self.combo_label.setVisible(False)

    def _level_completed(self) -> None:
        self.task_display.setText("நிலை முடிந்தது! அடுத்த நிலையைத் தேர்வு செய்யவும்.")
        self._set_input_text("")
        QMessageBox.information(self, "நிலை முடிந்தது", "இந்த நிலையை நீங்கள் முடித்துவிட்டீர்கள்!")
        self._refresh_levels_list()
        self._clear_keyboard_highlight()

    def _reset_progress(self) -> None:
        confirm = QMessageBox.question(
            self,
            "முன்னேற்றத்தை மீட்டமை",
            "அனைத்து முன்னேற்றத்தையும் மீட்டமைக்க வேண்டுமா?",
        )
        if confirm == QMessageBox.Yes:
            self._progress_store.reset()
            self._refresh_levels_list()

    def _build_keyboard(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)
        # Set padding to match outer container padding for proper spacing
        container.setStyleSheet("background: transparent; border-radius: 12px; padding: 0px;")

        colors = self._get_theme_colors()
        
        # Calculate base font size - will be updated dynamically based on actual width
        # Use initial estimate based on screen size
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            screen_width = screen.availableGeometry().width()
            # Reference: 1920px screen = 18px base font
            # Scale font proportionally with screen width
            font_scale = screen_width / 1920.0
            base_font_size = max(14, int(18 * font_scale))
        else:
            base_font_size = 18
        
        # Store initial font sizes
        self._keyboard_font_sizes = {
            'base': base_font_size,
            'tamil_base': base_font_size,
            'english': max(8, int(base_font_size * 0.75)),
            'tamil_shift': max(10, int(base_font_size * 0.75)),
            'special': max(10, int(base_font_size * 0.78))
        }
        
        size_map = {
            "Backspace": 2.0,
            "Tab": 1.75,
            "Caps": 2.0,
            "Enter": 2.0,
            "Shift": 2.5,
            "Space": 7.5,
            "Ctrl": 1.75,
            "Alt": 1.0,
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

        # Calculate font sizes based on the base font size (which scales with screen)
        # These ratios maintain good readability at different sizes
        tamil_base_font = self._keyboard_font_sizes['tamil_base']
        english_font = self._keyboard_font_sizes['english']
        tamil_shift_font = self._keyboard_font_sizes['tamil_shift']
        special_font = self._keyboard_font_sizes['special']

        # Use percentage-based spacing for consistent appearance across all key sizes
        # The middle column will take 15% of the table width, ensuring uniform spacing
        label_spacing_percent = 100

        logging.info(f"Base font size: {base_font_size}")
        logging.info(f"English font: {english_font}")
        logging.info(f"Tamil base font: {tamil_base_font}")
        logging.info(f"Tamil shift font: {tamil_shift_font}")
        logging.info(f"Special font: {special_font}")

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
                
                # Calculate key dimensions - use flexible sizing
                # Base width will scale with grid columns
                key_width = int(unit_pixels * size * unit_scale)
                key_height = base_key_height
                
                # Log each key size
                logging.info(f"Key: {key}, Size: {size}, Width: {key_width}px, Height: {key_height}px")

                label.setMinimumHeight(key_height)
                # Don't set fixed minimum width - let grid handle it with stretch factors
                # This allows keys to scale down when space is limited
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
                    # Identify left vs right shift by position (row 3 has two Shift keys)
                    if row_index == 3 and start_col == 0:
                        self._left_shift_label = label
                    elif row_index == 3:
                        self._right_shift_label = label

        max_columns = max(sum(int(size * unit_scale) for _, size in row) for row in rows)
        for column in range(max_columns):
            # Set a very small minimum width to allow scaling down
            grid.setColumnMinimumWidth(column, 2)
            # Use stretch factors to allow columns to scale proportionally
            grid.setColumnStretch(column, 1)
        
        # Ensure the grid layout has proper margins to prevent cropping
        grid.setContentsMargins(0, 0, 0, 0)
        
        # Store keyboard container reference for font updates
        container._key_labels_ref = self._key_labels
        container._shift_labels_ref = self._shift_labels

        return container
    
    def _rebuild_keyboard_labels(self) -> None:
        """Rebuild keyboard label HTML with updated font sizes"""
        if not self._keyboard_widget or not self._keyboard_font_sizes:
            return
        
        colors = self._get_theme_colors()
        tamil_base_font = self._keyboard_font_sizes.get('tamil_base', 18)
        english_font = self._keyboard_font_sizes.get('english', 14)
        tamil_shift_font = self._keyboard_font_sizes.get('tamil_shift', 14)
        
        # Special keys that shouldn't be updated (handled separately)
        special_keys = {"Space", "Tab", "Caps", "Enter", "Backspace", "Ctrl", "Alt", "Shift"}
        
        # Update all regular key labels (non-special keys)
        for key_name, label in self._key_labels.items():
            if key_name in special_keys:
                continue  # Special keys are handled separately
            
            # Get the key display mapping
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
        for label in self._highlighted_keys:
            base_style = self._key_base_style_by_label.get(label)
            if base_style:
                label.setStyleSheet(base_style)
        self._highlighted_keys = []

    def _highlight_key(self, label: QLabel, key_label: str = "", is_shift: bool = False) -> None:
        font_px = self._keyboard_font_sizes.get('special', 18) if (is_shift or key_label in {"Shift", "Space", "Backspace", "Tab", "Caps", "Enter", "Ctrl", "Alt"}) else self._keyboard_font_sizes.get('base', 18)
        highlight_key = key_label or "Shift"
        border_color = self._highlight_border_color_for_key(highlight_key)
        style = self._build_key_style(highlight_key, font_px, border_px=4, border_color=border_color, font_weight=500)
        label.setStyleSheet(style)
        self._highlighted_keys.append(label)

    def _update_keyboard_hint(self) -> None:
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
                # Highlight the correct Shift key based on hand rule
                side = self._shift_side_for_key(key_label)
                shift_label = self._right_shift_label if side == 'right' else self._left_shift_label
                if shift_label is not None:
                    self._highlight_key(shift_label, key_label="Shift", is_shift=True)
                else:
                    # Fallback if we couldn't identify sides
                    for s in self._shift_labels:
                        self._highlight_key(s, key_label="Shift", is_shift=True)
            
            # Update finger guidance label
            if self._finger_guidance_label:
                english_finger, tamil_finger = self._get_finger_name(key_label, needs_shift)
                # Format: "Use Left Thumb / இடது கட்டைவிரல்"
                if needs_shift:
                    shift_side = self._shift_side_for_key(key_label)
                    guidance_text = f"<div style='text-align: center;'>Hold {shift_side.capitalize()} Shift<br/>{english_finger}<br/>{tamil_finger}</div>"
                else:
                    guidance_text = f"<div style='text-align: center;'>Use {english_finger}<br/>{tamil_finger}</div>"
                self._finger_guidance_label.setText(guidance_text)
                self._finger_guidance_label.setVisible(True)
        else:
            # Task is complete - highlight space bar to indicate user should press space for next task
            self._clear_keyboard_highlight()
            if "Space" in self._key_labels:
                space_label = self._key_labels["Space"]
                colors = self._get_theme_colors()
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
            
            # Update finger guidance for space bar
            if self._finger_guidance_label:
                english_finger, tamil_finger = self._get_finger_name("Space", False)
                guidance_text = f"Press Space to continue<br/>Use {english_finger}<br/>{tamil_finger}"
                self._finger_guidance_label.setText(guidance_text)
                self._finger_guidance_label.setVisible(True)
    
    def _build_keystroke_sequence(self, text: str) -> list[tuple[str, bool]]:
        """Build the keystroke sequence for Tamil99 text."""
        sequence = []
        self._char_to_keystroke_map = {}
        keystroke_idx = 0
        
        for char_idx, char in enumerate(text):
            # Get keystroke sequence from char_to_keystrokes mapping
            if self._char_to_key and char in self._char_to_key:
                key_seq = self._char_to_key[char]  # e.g., "oa" or "q" or "^d"
                # Handle special sequences like "^d" or "^q"
                # In Tamil99, "^" prefix means use the key after it (^d = press d, ^q = press q)
                if key_seq.startswith("^"):
                    # Extract the actual key after ^
                    if len(key_seq) > 1:
                        k = key_seq[1]
                        is_upper = k.isupper()
                        sequence.append((k.upper(), is_upper))
                        self._char_to_keystroke_map[char_idx] = keystroke_idx
                        keystroke_idx += 1
                    else:
                        # Just "^" - shouldn't happen, but handle it
                        sequence.append(("^", False))
                        self._char_to_keystroke_map[char_idx] = keystroke_idx
                        keystroke_idx += 1
                else:
                    # Multi-character sequence like "oa" means press o then a
                    # All keystrokes for this character map to the same char_idx
                    for k in key_seq:
                        is_upper = k.isupper()
                        sequence.append((k.upper(), is_upper))
                        keystroke_idx += 1
                    # Map the character to the first keystroke of its sequence
                    self._char_to_keystroke_map[char_idx] = keystroke_idx - len(key_seq)
            else:
                # Fallback for unmapped characters (spaces, punctuation)
                if char == " ":
                    sequence.append(("Space", False))
                else:
                    key_label, needs_shift = self._map_char_to_key(char)
                    sequence.append((key_label, needs_shift))
                self._char_to_keystroke_map[char_idx] = keystroke_idx
                keystroke_idx += 1
        
        return sequence

    def _map_char_to_key(self, char: str) -> tuple[str, bool]:
        # This is a fallback for non-Tamil characters (spaces, punctuation, etc.)
        # Tamil characters should be handled in _build_keystroke_sequence using _char_to_key
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
        mapping_path = Path(__file__).parent.parent / "data" / "m17n" / "ta-tamil99.mim"
        if not mapping_path.exists():
            return {}, {}

        text = mapping_path.read_text(encoding="utf-8", errors="ignore")
        pattern = re.compile(r'\("([^"]+)"\s+(\?[^)]+|"[^"]*")\)')

        keycaps: dict[str, tuple[str, Optional[str]]] = {}
        char_to_keystrokes: dict[str, str] = {}  # Tamil char -> keystroke sequence (e.g., "oa")

        for match in pattern.finditer(text):
            key_seq = match.group(1)  # Can be single or multi-character like "oa"
            out = match.group(2)

            if out.startswith("?"):
                out_value = out[1:].replace('\\"', '"').replace("\\\\", "\\")
            else:
                out_value = out.strip('"').replace('\\"', '"').replace("\\\\", "\\")

            if not out_value:
                continue

            # Build keycaps for single-character keys only
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

            # Build reverse mapping: Tamil character -> keystroke sequence
            # Only store mappings where output is EXACTLY that character (not a compound)
            if len(out_value) == 1:
                char_code = ord(out_value)
                # Tamil Unicode range: 0B80-0BFF (includes all Tamil chars, combining marks, etc.)
                if 0x0B80 <= char_code <= 0x0BFF:
                    # Prefer shorter sequences, but prioritize single-character keys
                    should_store = False
                    if out_value not in char_to_keystrokes:
                        should_store = True
                    else:
                        current_seq = char_to_keystrokes[out_value]
                        # Prefer single-character sequences
                        if len(key_seq) == 1 and len(current_seq) > 1:
                            should_store = True
                        # For pulli (்), prefer sequences ending with 'f'
                        elif out_value == '்' and key_seq.endswith('f') and not current_seq.endswith('f'):
                            should_store = True
                        # For vowel signs, prefer sequences starting with '^'
                        elif 0x0BBE <= char_code <= 0x0BFF and key_seq.startswith('^') and not current_seq.startswith('^'):
                            should_store = True
                        # Otherwise prefer shorter sequences
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
        if not target:
            return
        self._task_display_offset = 0
        self._render_task_display(typed, target, is_error)

    def _render_task_display(self, typed: str, target: str, is_error: bool) -> None:
        if not target:
            self.task_display.setText("")
            return

        colors = self._get_theme_colors()
        
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
    
    def _update_background(self) -> None:
        """Update the background SVG to fit the window size"""
        if not self._background_label or not self._background_svg_renderer:
            return
        
        # Get window size
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return

        dpr = float(self.devicePixelRatioF())
        render_key = (size.width(), size.height(), dpr)
        if self._background_last_render_key == render_key:
            # Avoid redundant renders while resizing
            return
        
        # Create pixmap at window size (device pixels for crisp rendering)
        pixmap = QPixmap(int(size.width() * dpr), int(size.height() * dpr))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.transparent)
        
        # Render SVG scaled to match window size exactly
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Scale SVG to match window dimensions exactly
        svg_size = self._background_svg_renderer.defaultSize()
        if svg_size.width() > 0 and svg_size.height() > 0:
            scale_x = size.width() / svg_size.width()
            scale_y = size.height() / svg_size.height()
            
            # Scale to match window size exactly (stretches if aspect ratios differ)
            painter.scale(scale_x, scale_y)
            self._background_svg_renderer.render(painter)
        
        painter.end()
        
        # Set pixmap to background label
        self._background_label.setPixmap(pixmap)
        self._background_label.setGeometry(0, 0, size.width(), size.height())
        self._background_last_render_key = render_key

    def _schedule_background_update(self, debounce_ms: int = 50) -> None:
        """Debounce background renders during interactive resize."""
        if not self._background_label or not self._background_svg_renderer:
            return
        if self._background_update_timer is None:
            self._update_background()
            return
        # Restart timer (cancels previous pending update)
        self._background_update_timer.stop()
        self._background_update_timer.start(max(0, int(debounce_ms)))
