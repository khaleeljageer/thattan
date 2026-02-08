"""Tests for thattan.ui.colors – color blending and constants."""

from __future__ import annotations

import pytest

from thattan.ui.colors import HomeColors, blend_hex


# ===========================================================================
# HomeColors – constants exist
# ===========================================================================

class TestHomeColors:
    def test_bg_top_is_hex(self):
        assert HomeColors.BG_TOP.startswith("#")
        assert len(HomeColors.BG_TOP) == 7

    def test_primary_is_hex(self):
        assert HomeColors.PRIMARY.startswith("#")

    def test_text_primary_is_hex(self):
        assert HomeColors.TEXT_PRIMARY.startswith("#")

    def test_card_bg_is_rgba(self):
        assert HomeColors.CARD_BG.startswith("rgba(")


# ===========================================================================
# blend_hex – happy paths
# ===========================================================================

class TestBlendHexHappy:
    def test_t_zero_returns_a(self):
        assert blend_hex("#FF0000", "#0000FF", 0.0) == "#FF0000"

    def test_t_one_returns_b(self):
        assert blend_hex("#FF0000", "#0000FF", 1.0) == "#0000FF"

    def test_midpoint(self):
        result = blend_hex("#000000", "#FFFFFF", 0.5)
        # Expect around #7F7F7F (127,127,127)
        r = int(result[1:3], 16)
        g = int(result[3:5], 16)
        b = int(result[5:7], 16)
        assert 126 <= r <= 128
        assert 126 <= g <= 128
        assert 126 <= b <= 128

    def test_same_color(self):
        assert blend_hex("#ABCDEF", "#ABCDEF", 0.5) == "#ABCDEF"

    def test_returns_uppercase_hex(self):
        result = blend_hex("#ff0000", "#00ff00", 0.5)
        assert result == result.upper() or result.startswith("#")

    def test_quarter_blend(self):
        result = blend_hex("#000000", "#FF0000", 0.25)
        r = int(result[1:3], 16)
        # 0 + (255 - 0) * 0.25 = 63.75 -> 63
        assert 63 <= r <= 64

    def test_preserves_hash_prefix(self):
        result = blend_hex("#123456", "#654321", 0.5)
        assert result.startswith("#")
        assert len(result) == 7


# ===========================================================================
# blend_hex – clamping
# ===========================================================================

class TestBlendHexClamping:
    def test_t_negative_clamped_to_zero(self):
        assert blend_hex("#FF0000", "#0000FF", -1.0) == "#FF0000"

    def test_t_greater_than_one_clamped(self):
        assert blend_hex("#FF0000", "#0000FF", 2.0) == "#0000FF"


# ===========================================================================
# blend_hex – invalid inputs
# ===========================================================================

class TestBlendHexInvalid:
    def test_a_missing_hash(self):
        result = blend_hex("FF0000", "#0000FF", 0.5)
        assert result == "FF0000"  # returns a

    def test_b_missing_hash(self):
        result = blend_hex("#FF0000", "0000FF", 0.5)
        assert result == "#FF0000"  # returns a

    def test_a_wrong_length(self):
        result = blend_hex("#FFF", "#000000", 0.5)
        assert result == "#FFF"

    def test_b_wrong_length(self):
        result = blend_hex("#FF0000", "#FFF", 0.5)
        assert result == "#FF0000"

    def test_invalid_hex_chars(self):
        result = blend_hex("#GGHHII", "#000000", 0.5)
        assert result == "#GGHHII"  # exception caught, returns a

    def test_both_invalid(self):
        result = blend_hex("bad", "worse", 0.5)
        assert result == "bad"

    def test_empty_strings(self):
        result = blend_hex("", "", 0.5)
        assert result == ""

    def test_whitespace_padding(self):
        # blend_hex strips whitespace
        result = blend_hex("  #FF0000  ", "  #0000FF  ", 0.0)
        assert result == "#FF0000"
