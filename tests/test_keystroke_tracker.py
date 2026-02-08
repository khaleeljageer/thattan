"""Tests for thattan.core.keystroke_tracker – Tamil99 layout and tracker."""

from __future__ import annotations

from datetime import datetime

from thattan.core.keystroke_tracker import (
    KeystrokeTracker,
    StrokeData,
    Tamil99KeyboardLayout,
)


# ===========================================================================
# StrokeData dataclass
# ===========================================================================

class TestStrokeData:
    def test_creation(self):
        now = datetime.now()
        sd = StrokeData(
            key="a", expected_key="a",
            is_correct=True, response_time=120.5,
            timestamp=now,
        )
        assert sd.key == "a"
        assert sd.expected_key == "a"
        assert sd.is_correct is True
        assert sd.response_time == 120.5
        assert sd.timestamp == now

    def test_incorrect_stroke(self):
        sd = StrokeData(
            key="b", expected_key="a",
            is_correct=False, response_time=200.0,
            timestamp=datetime.now(),
        )
        assert sd.is_correct is False


# ===========================================================================
# Tamil99KeyboardLayout – _generate_consonant_vowel_combination
# ===========================================================================

class TestGenerateCombination:
    def test_valid_combination(self):
        # க + ா => 'h' + 'q' => 'hq'
        result = Tamil99KeyboardLayout._generate_consonant_vowel_combination("க", "ா")
        assert result == "hq"

    def test_valid_combination_pa_i(self):
        # ப + ி => 'j' + 's' => 'js'
        result = Tamil99KeyboardLayout._generate_consonant_vowel_combination("ப", "ி")
        assert result == "js"

    def test_invalid_consonant(self):
        result = Tamil99KeyboardLayout._generate_consonant_vowel_combination("X", "ா")
        assert result is None

    def test_invalid_vowel_sign(self):
        result = Tamil99KeyboardLayout._generate_consonant_vowel_combination("க", "X")
        assert result is None

    def test_both_invalid(self):
        result = Tamil99KeyboardLayout._generate_consonant_vowel_combination("X", "Y")
        assert result is None


# ===========================================================================
# Tamil99KeyboardLayout – get_keystroke_sequence
# ===========================================================================

class TestGetKeystrokeSequence:
    # --- Space handling ---
    def test_space(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence(" ")
        assert seq == [("Space", False)]

    def test_multiple_spaces(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("   ")
        assert seq == [("Space", False), ("Space", False), ("Space", False)]

    # --- Standalone vowels ---
    def test_vowel_a(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("அ")
        assert seq == [("A", False)]

    def test_vowel_aa(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("ஆ")
        assert seq == [("Q", False)]

    # --- Standalone consonants ---
    def test_consonant_ka(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("க")
        assert seq == [("H", False)]

    def test_consonant_pa(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("ப")
        assert seq == [("J", False)]

    # --- Combined consonant-vowel ---
    def test_combined_kaa(self):
        # கா = 'hq' -> [('H', False), ('Q', False)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("கா")
        assert seq == [("H", False), ("Q", False)]

    def test_combined_ki(self):
        # கி = 'hs' -> [('H', False), ('S', False)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("கி")
        assert seq == [("H", False), ("S", False)]

    def test_combined_du(self):
        # டு = 'od' -> [('O', False), ('D', False)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("டு")
        assert seq == [("O", False), ("D", False)]

    # --- Consonant with pulli ---
    def test_pulli_k(self):
        # க் = 'hf' -> [('H', False), ('F', False)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("க்")
        assert seq == [("H", False), ("F", False)]

    # --- Double consonants ---
    def test_double_consonant_kka(self):
        # க்க as 3 codepoints: க + ் + க
        # First, க் is a combined char in CHAR_TO_KEYSTROKES -> 'hf' -> [('H',False), ('F',False)]
        # Then, க -> 'h' -> [('H',False)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("க்க")
        assert seq == [("H", False), ("F", False), ("H", False)]

    # --- Tamil numeral ---
    def test_tamil_numeral_1(self):
        # ௧ = '^#1' -> [('^', False), ('#', False), ('1', False)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("௧")
        assert seq == [("^", False), ("#", False), ("1", False)]

    def test_tamil_numeral_0(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("௦")
        assert seq == [("^", False), ("#", False), ("0", False)]

    # --- Vowel sign (standalone) ---
    def test_vowel_sign_aa(self):
        # ா = '^q' -> [('^', False), ('Q', False)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("ா")
        assert seq == [("^", False), ("Q", False)]

    # --- Grantha consonants (uppercase / shifted) ---
    def test_grantha_sa(self):
        # ஸ = 'Q' -> [('Q', True)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("ஸ")
        assert seq == [("Q", True)]

    def test_grantha_ja(self):
        # ஜ = 'E' -> [('E', True)]
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("ஜ")
        assert seq == [("E", True)]

    # --- Unmapped characters ---
    def test_unmapped_alphabetic(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("A")
        assert seq == [("A", True)]

    def test_unmapped_lowercase(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("z")
        assert seq == [("Z", False)]

    def test_unmapped_digit(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("5")
        assert seq == [("5", False)]

    def test_unmapped_punctuation(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("!")
        assert seq == [("!", False)]

    # --- Empty string ---
    def test_empty_string(self):
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("")
        assert seq == []

    # --- Multi-character text ---
    def test_mixed_text(self):
        # "அ " -> vowel a + space
        seq = Tamil99KeyboardLayout.get_keystroke_sequence("அ ")
        assert seq == [("A", False), ("Space", False)]


# ===========================================================================
# Tamil99KeyboardLayout – get_key_for_char
# ===========================================================================

class TestGetKeyForChar:
    def test_mapped_vowel(self):
        # 'அ' -> 'a' -> 'A'
        assert Tamil99KeyboardLayout.get_key_for_char("அ") == "A"

    def test_mapped_consonant(self):
        # 'க' -> 'h' -> 'H'
        assert Tamil99KeyboardLayout.get_key_for_char("க") == "H"

    def test_tamil_numeral(self):
        # '௧' -> '^#1' -> starts with ^# -> returns '1'.upper() = '1'
        assert Tamil99KeyboardLayout.get_key_for_char("௧") == "1"

    def test_vowel_sign(self):
        # 'ா' -> '^q' -> starts with ^ -> returns 'Q'
        assert Tamil99KeyboardLayout.get_key_for_char("ா") == "Q"

    def test_unmapped_char(self):
        assert Tamil99KeyboardLayout.get_key_for_char("Z") is None

    def test_grantha(self):
        # 'ஸ' -> 'Q' -> returns 'Q'
        assert Tamil99KeyboardLayout.get_key_for_char("ஸ") == "Q"


# ===========================================================================
# KeystrokeTracker – init
# ===========================================================================

class TestKeystrokeTrackerInit:
    def test_initial_state(self):
        tracker = KeystrokeTracker()
        assert tracker.stats["total_strokes"] == 0
        assert tracker.stats["correct_strokes"] == 0
        assert tracker.stats["incorrect_strokes"] == 0
        assert tracker.stats["accuracy"] == 0.0
        assert len(tracker.strokes) == 0


# ===========================================================================
# KeystrokeTracker – record_stroke
# ===========================================================================

class TestRecordStroke:
    def test_correct_stroke(self):
        tracker = KeystrokeTracker()
        result = tracker.record_stroke("a", "a", response_time=100.0)
        assert result["is_correct"] is True
        assert result["expected"] == "a"
        assert result["pressed"] == "a"
        assert tracker.stats["total_strokes"] == 1
        assert tracker.stats["correct_strokes"] == 1
        assert tracker.stats["incorrect_strokes"] == 0

    def test_incorrect_stroke(self):
        tracker = KeystrokeTracker()
        result = tracker.record_stroke("b", "a", response_time=100.0)
        assert result["is_correct"] is False
        assert tracker.stats["incorrect_strokes"] == 1
        assert tracker.stats["common_mistakes"]["a → b"] == 1

    def test_case_insensitive_match(self):
        tracker = KeystrokeTracker()
        result = tracker.record_stroke("A", "a", response_time=100.0)
        assert result["is_correct"] is True

    def test_accuracy_all_correct(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=100.0)
        tracker.record_stroke("b", "b", response_time=100.0)
        assert tracker.stats["accuracy"] == 100.0

    def test_accuracy_half_correct(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=100.0)
        tracker.record_stroke("x", "b", response_time=100.0)
        assert tracker.stats["accuracy"] == 50.0

    def test_response_time_tracked(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=150.0)
        assert tracker.stats["response_times"] == [150.0]

    def test_response_time_auto_calculated(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a")  # no explicit response_time
        assert len(tracker.stats["response_times"]) == 1
        assert tracker.stats["response_times"][0] >= 0

    def test_key_accuracy_tracking(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=100.0)
        tracker.record_stroke("x", "a", response_time=100.0)
        key_acc = tracker.stats["key_accuracy"]["a"]
        assert key_acc["total"] == 2
        assert key_acc["correct"] == 1

    def test_stroke_appended(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=100.0)
        assert len(tracker.strokes) == 1
        assert isinstance(tracker.strokes[0], StrokeData)
        assert tracker.strokes[0].key == "a"
        assert tracker.strokes[0].is_correct is True

    def test_multiple_strokes(self):
        tracker = KeystrokeTracker()
        for char in "hello":
            tracker.record_stroke(char, char, response_time=100.0)
        assert tracker.stats["total_strokes"] == 5
        assert tracker.stats["correct_strokes"] == 5


# ===========================================================================
# KeystrokeTracker – get_session_summary
# ===========================================================================

class TestGetSessionSummary:
    def test_summary_with_strokes(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=100.0)
        tracker.record_stroke("b", "b", response_time=200.0)
        summary = tracker.get_session_summary()
        assert summary["total_strokes"] == 2
        assert summary["correct_strokes"] == 2
        assert summary["incorrect_strokes"] == 0
        assert summary["overall_accuracy"] == 100.0
        assert summary["average_response_time"] == 150.0

    def test_summary_no_strokes(self):
        tracker = KeystrokeTracker()
        summary = tracker.get_session_summary()
        assert summary["total_strokes"] == 0
        assert summary["average_response_time"] == 0
        assert summary["typing_speed"] == 0

    def test_summary_duration_positive(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=100.0)
        summary = tracker.get_session_summary()
        assert summary["session_duration"] >= 0

    def test_summary_typing_speed(self):
        tracker = KeystrokeTracker()
        for _ in range(60):
            tracker.record_stroke("a", "a", response_time=100.0)
        summary = tracker.get_session_summary()
        assert summary["typing_speed"] > 0


# ===========================================================================
# KeystrokeTracker – reset_session
# ===========================================================================

class TestResetSession:
    def test_clears_strokes(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("a", "a", response_time=100.0)
        tracker.record_stroke("b", "a", response_time=100.0)
        tracker.reset_session()
        assert len(tracker.strokes) == 0
        assert tracker.stats["total_strokes"] == 0
        assert tracker.stats["correct_strokes"] == 0
        assert tracker.stats["incorrect_strokes"] == 0
        assert tracker.stats["accuracy"] == 0.0
        assert len(tracker.stats["response_times"]) == 0

    def test_resets_timestamps(self):
        tracker = KeystrokeTracker()
        old_start = tracker.session_start
        tracker.reset_session()
        assert tracker.session_start >= old_start
        assert tracker.last_stroke_time >= old_start

    def test_usable_after_reset(self):
        tracker = KeystrokeTracker()
        tracker.record_stroke("x", "a", response_time=100.0)
        tracker.reset_session()
        result = tracker.record_stroke("a", "a", response_time=100.0)
        assert result["is_correct"] is True
        assert tracker.stats["total_strokes"] == 1
        assert tracker.stats["accuracy"] == 100.0
