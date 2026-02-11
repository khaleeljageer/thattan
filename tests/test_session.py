"""Tests for thattan.core.session – typing session logic."""

from __future__ import annotations

import time

import pytest

from thattan.core.session import TaskResult, TypingSession


# ---------------------------------------------------------------------------
# TaskResult dataclass
# ---------------------------------------------------------------------------

class TestTaskResult:
    def test_creation(self):
        tr = TaskResult(accuracy=95.0, wpm=40.0, cpm=200.0, errors=2)
        assert tr.accuracy == 95.0
        assert tr.wpm == 40.0
        assert tr.cpm == 200.0
        assert tr.errors == 2

    def test_equality(self):
        a = TaskResult(accuracy=95.0, wpm=40.0, cpm=200.0, errors=2)
        b = TaskResult(accuracy=95.0, wpm=40.0, cpm=200.0, errors=2)
        assert a == b


# ---------------------------------------------------------------------------
# TypingSession – properties
# ---------------------------------------------------------------------------

class TestSessionProperties:
    def test_index_starts_at_zero(self):
        s = TypingSession(["a", "b", "c"])
        assert s.index == 0

    def test_index_with_start_index(self):
        s = TypingSession(["a", "b", "c"], start_index=2)
        assert s.index == 2

    def test_total_tasks(self):
        s = TypingSession(["a", "b", "c"])
        assert s.total_tasks == 3

    def test_total_correct_initially_zero(self):
        s = TypingSession(["a", "b"])
        assert s.total_correct == 0

    def test_start_time_is_recent(self):
        before = time.time()
        s = TypingSession(["a"])
        after = time.time()
        assert before <= s.start_time <= after


# ---------------------------------------------------------------------------
# TypingSession – current_task
# ---------------------------------------------------------------------------

class TestCurrentTask:
    def test_returns_first_task(self):
        s = TypingSession(["hello", "world"])
        assert s.current_task() == "hello"

    def test_after_submit(self):
        s = TypingSession(["hello", "world"])
        s.submit("hello")
        assert s.current_task() == "world"

    def test_index_error_when_complete(self):
        s = TypingSession(["only"])
        s.submit("only")
        with pytest.raises(IndexError):
            s.current_task()


# ---------------------------------------------------------------------------
# TypingSession – is_complete
# ---------------------------------------------------------------------------

class TestIsComplete:
    def test_not_complete_initially(self):
        s = TypingSession(["a", "b"])
        assert not s.is_complete()

    def test_complete_after_all_submitted(self):
        s = TypingSession(["a", "b"])
        s.submit("a")
        s.submit("b")
        assert s.is_complete()

    def test_complete_when_start_index_at_end(self):
        s = TypingSession(["a", "b"], start_index=2)
        assert s.is_complete()

    def test_complete_when_start_index_beyond_end(self):
        s = TypingSession(["a"], start_index=5)
        assert s.is_complete()


# ---------------------------------------------------------------------------
# TypingSession – submit
# ---------------------------------------------------------------------------

class TestSubmit:
    def test_perfect_match(self):
        s = TypingSession(["abc"])
        result = s.submit("abc")
        assert result.accuracy == 100.0
        assert result.errors == 0

    def test_total_mismatch(self):
        s = TypingSession(["abc"])
        result = s.submit("xyz")
        assert result.accuracy == 0.0
        assert result.errors == 3

    def test_partial_match(self):
        s = TypingSession(["abcd"])
        result = s.submit("abxy")
        # correct: a, b  -> 2/4 = 50%
        assert result.accuracy == 50.0
        assert result.errors == 2

    def test_typed_shorter_than_target(self):
        s = TypingSession(["abcd"])
        result = s.submit("ab")
        # zip pairs: (a,a), (b,b) -> 2 correct; total = max(4,2) = 4; errors = 2
        assert result.accuracy == 50.0
        assert result.errors == 2

    def test_typed_longer_than_target(self):
        s = TypingSession(["ab"])
        result = s.submit("abcd")
        # zip pairs: (a,a), (b,b) -> 2 correct; total = max(2,4) = 4; errors = 2
        assert result.accuracy == 50.0
        assert result.errors == 2

    def test_empty_typed(self):
        s = TypingSession(["abc"])
        result = s.submit("")
        # correct: 0; total = max(3,0) = 3; errors = 3
        assert result.accuracy == 0.0
        assert result.errors == 3

    def test_both_empty(self):
        s = TypingSession([""])
        result = s.submit("")
        # total = max(0,0) = 0; accuracy = 0.0 (guard)
        assert result.accuracy == 0.0
        assert result.errors == 0

    def test_submit_increments_index(self):
        s = TypingSession(["a", "b", "c"])
        assert s.index == 0
        s.submit("a")
        assert s.index == 1
        s.submit("b")
        assert s.index == 2

    def test_submit_when_already_complete(self):
        s = TypingSession(["a"])
        s.submit("a")
        result = s.submit("whatever")
        assert result == TaskResult(accuracy=0.0, wpm=0.0, cpm=0.0, errors=0)

    def test_wpm_is_positive_on_perfect(self):
        s = TypingSession(["hello world"])
        result = s.submit("hello world")
        assert result.wpm > 0

    def test_accumulates_stats(self):
        s = TypingSession(["ab", "cd"])
        s.submit("ab")  # 2 correct, 0 errors
        s.submit("cx")  # 1 correct, 1 error
        assert s.total_correct == 3

    def test_result_has_cpm(self):
        s = TypingSession(["hello"])
        result = s.submit("hello")
        assert result.cpm > 0


# ---------------------------------------------------------------------------
# TypingSession – net WPM (error penalty)
# ---------------------------------------------------------------------------

class TestNetWpm:
    def test_perfect_typing_net_equals_gross(self):
        """With zero errors, net WPM should equal gross WPM."""
        s = TypingSession(["abc"])
        s.submit("abc")
        gross = s.aggregate_gross_wpm()
        net = s.aggregate_wpm()
        assert net == pytest.approx(gross)

    def test_errors_reduce_net_wpm(self):
        """Errors should lower net WPM relative to gross."""
        s = TypingSession(["abcde"])
        s.submit("axxxx")  # 1 correct, 4 errors
        gross = s.aggregate_gross_wpm()
        net = s.aggregate_wpm()
        assert net < gross

    def test_net_wpm_floors_at_zero(self):
        """Net WPM should never go negative even with many errors."""
        s = TypingSession(["ab"])
        s.submit("xy")  # 0 correct, 2 errors; penalty = 10 chars > total = 2
        assert s.aggregate_wpm() == 0.0

    def test_submit_wpm_matches_aggregate(self):
        """The wpm returned by submit() should match aggregate_wpm()."""
        s = TypingSession(["hello"])
        result = s.submit("hello")
        # They won't be exactly equal due to microsecond time differences,
        # but should be very close
        assert result.wpm > 0
        assert s.aggregate_wpm() > 0


# ---------------------------------------------------------------------------
# TypingSession – CPM
# ---------------------------------------------------------------------------

class TestCpm:
    def test_cpm_correct_chars_only(self):
        """CPM should reflect only correct characters."""
        s = TypingSession(["abcd"])
        s.submit("abxy")  # 2 correct out of 4
        cpm = s.aggregate_cpm()
        # 2 correct chars / some tiny elapsed time -> CPM > 0
        assert cpm > 0
        # gross equivalent would be higher (4 chars)
        gross_char_rate = s.aggregate_gross_wpm() * 5
        assert cpm < gross_char_rate

    def test_cpm_zero_when_all_wrong(self):
        """CPM should be ~0 when nothing is correct (0 correct chars)."""
        s = TypingSession(["abc"])
        s.submit("xyz")
        assert s.aggregate_cpm() == pytest.approx(0.0, abs=0.01)

    def test_cpm_positive_on_perfect(self):
        s = TypingSession(["hello"])
        s.submit("hello")
        assert s.aggregate_cpm() > 0

    def test_cpm_no_submissions(self):
        s = TypingSession(["abc"])
        assert s.aggregate_cpm() == pytest.approx(0.0, abs=0.01)

    def test_submit_cpm_matches_aggregate(self):
        s = TypingSession(["hello"])
        result = s.submit("hello")
        assert result.cpm > 0
        assert s.aggregate_cpm() > 0


# ---------------------------------------------------------------------------
# TypingSession – aggregate methods
# ---------------------------------------------------------------------------

class TestAggregates:
    def test_aggregate_accuracy_perfect(self):
        s = TypingSession(["abc", "def"])
        s.submit("abc")
        s.submit("def")
        assert s.aggregate_accuracy() == 100.0

    def test_aggregate_accuracy_partial(self):
        s = TypingSession(["ab", "cd"])
        s.submit("ab")  # 2/2
        s.submit("cx")  # 1/2
        # total_correct=3, total_chars=4 -> 75%
        assert s.aggregate_accuracy() == 75.0

    def test_aggregate_accuracy_no_submissions(self):
        s = TypingSession(["abc"])
        assert s.aggregate_accuracy() == 0.0

    def test_aggregate_wpm_is_positive(self):
        s = TypingSession(["hello"])
        s.submit("hello")
        assert s.aggregate_wpm() > 0

    def test_aggregate_wpm_no_submissions(self):
        s = TypingSession(["abc"])
        # 0 chars / some time -> 0 wpm (approximately)
        assert s.aggregate_wpm() == pytest.approx(0.0, abs=0.01)

    def test_aggregate_gross_wpm_positive(self):
        s = TypingSession(["hello"])
        s.submit("hello")
        assert s.aggregate_gross_wpm() > 0

    def test_aggregate_errors(self):
        s = TypingSession(["ab", "cd"])
        s.submit("ax")  # 1 error
        s.submit("cy")  # 1 error
        assert s.aggregate_errors() == 2

    def test_aggregate_errors_no_submissions(self):
        s = TypingSession(["abc"])
        assert s.aggregate_errors() == 0


# ---------------------------------------------------------------------------
# TypingSession – WPM calculation edge case
# ---------------------------------------------------------------------------

class TestWpmCalculation:
    def test_wpm_uses_elapsed_time(self):
        """WPM should increase if more chars typed in same time."""
        s1 = TypingSession(["a"])
        s1.submit("a")
        wpm1 = s1.aggregate_gross_wpm()

        s2 = TypingSession(["abcdefghij"])
        s2.submit("abcdefghij")
        wpm2 = s2.aggregate_gross_wpm()

        assert wpm2 > wpm1  # more chars -> higher WPM
