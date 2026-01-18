from __future__ import annotations

from dataclasses import dataclass
import html
import re
import os
import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QShortcut, QKeyEvent
from PySide6.QtCore import QObject
from PySide6.QtWidgets import (
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
    QStyle,
    QVBoxLayout,
    QWidget,
)

from thattachu.core.levels import LevelRepository, Level
from thattachu.core.progress import ProgressStore
from thattachu.core.session import TypingSession, TaskResult
from thattachu.core.keystroke_tracker import KeystrokeTracker, Tamil99KeyboardLayout


@dataclass
class LevelState:
    level: Level
    unlocked: bool
    completed: int


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
        self._current_task_text: str = ""
        self._task_display_offset: int = 0
        self._unlock_all_levels = os.environ.get("THATTACHU_UNLOCK_ALL") == "1"
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

        self._build_ui()
        self._refresh_levels_list()
        QTimer.singleShot(0, self.showMaximized)

    def _get_theme_colors(self) -> dict:
        """Get dark theme color palette"""
        return {
            'bg_main': '#1a202c',
            'bg_container': '#2d3748',
            'bg_card': '#4a5568',
            'bg_input': '#4a5568',
            'bg_hover': '#5a6578',
            'text_primary': '#e2e8f0',
            'text_secondary': '#cbd5e0',
            'text_muted': '#a0aec0',
            'border': '#4a5568',
            'border_light': '#5a6578',
            'highlight': '#81e6d9',
            'highlight_bg': '#234e52',
            'error': '#fc8181',
            'error_bg': '#742a2a',
            'success': '#68d391',
            'success_bg': '#22543d',
            'progress': '#81e6d9',
            'key_bg': '#4a5568',
            'key_highlight': '#81e6d9',
            'key_highlight_bg': '#234e52',
            'key_shift': '#f6ad55',
            'key_shift_bg': '#7c2d12',
        }

    def _build_ui(self) -> None:
        self.setWindowTitle("தட்டச்சு - தமிழ்99 பயிற்சி")
        self.setMinimumSize(1200, 800)
        
        colors = self._get_theme_colors()
        
        self.setStyleSheet(f"""
            QMainWindow {{ 
                background: {colors['bg_main']};
            }}
        """)

        root = QWidget()
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

        self.reset_button = QPushButton("🔄 முன்னேற்றத்தை மீட்டமை")
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
            font-family: 'Noto Sans Tamil', 'Latha', sans-serif;
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
                font-family: 'Noto Sans Tamil', 'Latha', sans-serif;
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

        keyboard_header = QLabel("⌨️ தமிழ்99 விசைப்பலகை")
        keyboard_header.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {colors['text_secondary']};
            padding: 12px 0px;
            background: transparent;
        """)
        layout.addWidget(keyboard_header, alignment=Qt.AlignHCenter)
        
        keyboard_container = self._build_keyboard()
        keyboard_container.setMinimumSize(980, 400)
        keyboard_container.setStyleSheet(f"""
            background: {colors['bg_container']};
            border: none;
            border-radius: 16px;
            padding: 20px;
        """)
        keyboard_wrapper = QWidget()
        keyboard_layout = QHBoxLayout(keyboard_wrapper)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard_layout.addStretch(1)
        keyboard_layout.addWidget(keyboard_container)
        keyboard_layout.addStretch(1)
        layout.addWidget(keyboard_wrapper)
        self.setCentralWidget(root)

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
        """Filter key events to track individual keystrokes"""
        if obj == self.input_box and event.type() == event.Type.KeyPress:
            return self._on_key_press(event)
        return super().eventFilter(obj, event)
    
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
        
        self._update_keyboard_hint()
        self._update_stats_from_tracker()
        
        return True
    
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
        container.setStyleSheet("background: #2d3748; border-radius: 12px; padding: 16px;")

        colors = self._get_theme_colors()
        key_style = f"""
            QLabel {{
                background: {colors['key_bg']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 12px 8px;
                font-family: 'Noto Sans Tamil', 'Latha', 'Sans Serif';
                font-size: 18px;
                font-weight: 400;
            }}
        """

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

        for row_index, row in enumerate(rows):
            col = 0
            for key, size in row:
                span = int(size * unit_scale)
                if key is None:
                    col += span
                    continue
                display = self._keycaps_map.get(key, (key, None))
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setTextFormat(Qt.RichText)
                label.setStyleSheet(key_style)
                label.setMinimumHeight(44)
                label.setMinimumWidth(int(unit_pixels * size * unit_scale))
                colors = self._get_theme_colors()
                if key in special_labels:
                    label.setText(html.escape(special_labels[key]))
                    label.setStyleSheet(key_style + f"QLabel {{ font-size: 14px; color: {colors['text_muted']}; }}")
                else:
                    english = html.escape(key)
                    tamil_base = html.escape(display[0]) if display[0] else ""
                    tamil_shift = html.escape(display[1]) if display[1] else ""
                    label.setText(
                        '<table style="width:100%; height:100%; border-collapse:collapse;">'
                        "<tr>"
                        f'<td style="font-size:10px; color:{colors["text_muted"]}; vertical-align:top; text-align:left;">{english}</td>'
                        '<td style="width:6px;"></td>'
                        f'<td style="font-size:12px; color:{colors["text_muted"]}; vertical-align:top; text-align:right;">{tamil_shift}</td>'
                        "</tr>"
                        "<tr>"
                        f'<td style="font-size:18px; font-weight:600; vertical-align:bottom; text-align:center;">{tamil_base}</td>'
                        "</tr>"
                        "</table>"
                    )

                grid.addWidget(label, row_index, col, 1, span)
                col += span

                if key == "Space":
                    self._key_labels["Space"] = label
                elif key not in {"Tab", "Caps", "Enter", "Backspace", "Ctrl", "Win", "Alt", "AltGr", "PrtSc"}:
                    self._key_labels[key.upper()] = label
                if key == "Shift":
                    self._shift_labels.append(label)

        max_columns = max(sum(int(size * unit_scale) for _, size in row) for row in rows)
        for column in range(max_columns):
            grid.setColumnMinimumWidth(column, unit_pixels)
            grid.setColumnStretch(column, 1)

        return container

    def _clear_keyboard_highlight(self) -> None:
        colors = self._get_theme_colors()
        for label in self._highlighted_keys:
            label.setStyleSheet(f"""
                QLabel {{
                    background: {colors['key_bg']};
                    color: {colors['text_primary']};
                    border: none;
                    border-radius: 6px;
                    padding: 12px 8px;
                    font-family: 'Noto Sans Tamil', 'Latha', 'Sans Serif';
                    font-size: 18px;
                    font-weight: 400;
                }}
            """)
        self._highlighted_keys = []

    def _highlight_key(self, label: QLabel, is_shift: bool = False) -> None:
        colors = self._get_theme_colors()
        if is_shift:
            style = f"""
                QLabel {{
                    background: {colors['key_shift_bg']};
                    color: {colors['text_primary']};
                    border: 2px solid {colors['key_shift']};
                    border-radius: 6px;
                    padding: 12px 8px;
                    font-family: 'Noto Sans Tamil', 'Latha', 'Sans Serif';
                    font-size: 18px;
                    font-weight: 500;
                }}
            """
        else:
            style = f"""
                QLabel {{
                    background: {colors['key_highlight_bg']};
                    color: {colors['text_primary']};
                    border: 2px solid {colors['key_highlight']};
                    border-radius: 6px;
                    padding: 12px 8px;
                    font-family: 'Noto Sans Tamil', 'Latha', 'Sans Serif';
                    font-size: 18px;
                    font-weight: 500;
                }}
            """
        label.setStyleSheet(style)
        self._highlighted_keys.append(label)

    def _update_keyboard_hint(self) -> None:
        if not self._session:
            self._clear_keyboard_highlight()
            return

        if self._keystroke_index < len(self._keystroke_sequence):
            key_label, needs_shift = self._keystroke_sequence[self._keystroke_index]
            self._clear_keyboard_highlight()
            
            if key_label == ' ' or key_label == 'Space':
                key_label = "Space"
            
            if key_label in self._key_labels:
                self._highlight_key(self._key_labels[key_label])
            if needs_shift:
                for shift_label in self._shift_labels:
                    self._highlight_key(shift_label, is_shift=True)
        else:
            # Task is complete - highlight space bar to indicate user should press space for next task
            self._clear_keyboard_highlight()
            if "Space" in self._key_labels:
                space_label = self._key_labels["Space"]
                colors = self._get_theme_colors()
                space_label.setStyleSheet(f"""
                    QLabel {{
                        background: {colors['success_bg']};
                        color: {colors['text_primary']};
                        border: 2px solid {colors['success']};
                        border-radius: 6px;
                        padding: 12px 8px;
                        font-family: 'Noto Sans Tamil', 'Latha', 'Sans Serif';
                        font-size: 18px;
                        font-weight: 500;
                    }}
                """)
                self._highlighted_keys.append(space_label)
    
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
        mapping_path = Path("/usr/share/m17n/ta-tamil99.mim")
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
            current_style = f"background:{colors['highlight_bg']}; color:{colors['text_primary']}; font-weight:500; padding:2px 4px; border-radius:4px;"
            if is_error:
                current_style = f"background:{colors['error_bg']}; color:{colors['text_primary']}; font-weight:500; padding:2px 4px; border-radius:4px;"
            
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
                    font-family: 'Noto Sans Tamil', 'Latha', sans-serif;
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
                    font-family: 'Noto Sans Tamil', 'Latha', sans-serif;
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

        task_font = QFont("Sans Serif")
        task_font.setPointSizeF(task_size)
        self.task_display.setFont(task_font)

        input_font = QFont("Sans Serif")
        input_font.setPointSizeF(input_size)
        self.input_box.setFont(input_font)

        self.task_display.setMinimumHeight(int(task_size * 2.2))
        self.input_box.setMinimumHeight(int(input_size * 2.2))
