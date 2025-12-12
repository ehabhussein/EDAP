"""Tests for EDAP models."""

import pytest
from collections import Counter

from edap.models import (
    CharType,
    PositionStats,
    LengthStats,
    WordAnalysis,
    AnalysisResult,
)


class TestCharType:
    """Tests for CharType enum."""

    def test_from_char_uppercase(self):
        assert CharType.from_char('A') == CharType.UPPER
        assert CharType.from_char('Z') == CharType.UPPER

    def test_from_char_lowercase(self):
        assert CharType.from_char('a') == CharType.LOWER
        assert CharType.from_char('z') == CharType.LOWER

    def test_from_char_digit(self):
        assert CharType.from_char('0') == CharType.DIGIT
        assert CharType.from_char('9') == CharType.DIGIT

    def test_from_char_symbol(self):
        assert CharType.from_char('!') == CharType.SYMBOL
        assert CharType.from_char('@') == CharType.SYMBOL
        assert CharType.from_char('-') == CharType.SYMBOL
        assert CharType.from_char('_') == CharType.SYMBOL

    def test_str_representation(self):
        assert str(CharType.UPPER) == 'U'
        assert str(CharType.LOWER) == 'l'
        assert str(CharType.DIGIT) == 'n'
        assert str(CharType.SYMBOL) == '@'


class TestPositionStats:
    """Tests for PositionStats."""

    def test_add_char(self):
        stats = PositionStats(position=0, length=5)
        stats.add_char('A')
        stats.add_char('A')
        stats.add_char('B')

        assert stats.char_counts['A'] == 2
        assert stats.char_counts['B'] == 1
        assert stats.type_counts[CharType.UPPER] == 3

    def test_total_chars(self):
        stats = PositionStats(position=0, length=5)
        stats.add_char('A')
        stats.add_char('B')
        stats.add_char('C')

        assert stats.total_chars == 3

    def test_get_char_probability(self):
        stats = PositionStats(position=0, length=5)
        stats.add_char('A')
        stats.add_char('A')
        stats.add_char('B')
        stats.add_char('B')

        assert stats.get_char_probability('A') == 0.5
        assert stats.get_char_probability('B') == 0.5
        assert stats.get_char_probability('C') == 0.0

    def test_get_type_probability(self):
        stats = PositionStats(position=0, length=5)
        stats.add_char('A')  # Upper
        stats.add_char('B')  # Upper
        stats.add_char('a')  # Lower
        stats.add_char('1')  # Digit

        assert stats.get_type_probability(CharType.UPPER) == 0.5
        assert stats.get_type_probability(CharType.LOWER) == 0.25
        assert stats.get_type_probability(CharType.DIGIT) == 0.25

    def test_get_chars_by_type(self):
        stats = PositionStats(position=0, length=5)
        stats.add_char('A')
        stats.add_char('B')
        stats.add_char('a')
        stats.add_char('1')

        upper_chars = stats.get_chars_by_type(CharType.UPPER)
        assert set(upper_chars) == {'A', 'B'}

        lower_chars = stats.get_chars_by_type(CharType.LOWER)
        assert lower_chars == ['a']


class TestLengthStats:
    """Tests for LengthStats."""

    def test_init_creates_positions(self):
        stats = LengthStats(length=5)

        assert len(stats.positions) == 5
        for i in range(5):
            assert i in stats.positions
            assert stats.positions[i].position == i
            assert stats.positions[i].length == 5

    def test_add_word(self):
        stats = LengthStats(length=5)
        stats.add_word('Hello')

        assert stats.count == 1
        assert 'Ullll' in stats.patterns

    def test_add_word_wrong_length(self):
        stats = LengthStats(length=5)

        with pytest.raises(ValueError):
            stats.add_word('Hi')

    def test_patterns_counted(self):
        stats = LengthStats(length=3)
        stats.add_word('ABC')  # UUU
        stats.add_word('DEF')  # UUU
        stats.add_word('abc')  # lll

        assert stats.patterns['UUU'] == 2
        assert stats.patterns['lll'] == 1

    def test_get_common_patterns(self):
        stats = LengthStats(length=3)
        stats.add_word('ABC')
        stats.add_word('DEF')
        stats.add_word('GHI')
        stats.add_word('abc')

        patterns = stats.get_common_patterns(2)
        assert patterns[0] == ('UUU', 3)
        assert patterns[1] == ('lll', 1)


class TestWordAnalysis:
    """Tests for WordAnalysis."""

    def test_basic_analysis(self):
        analysis = WordAnalysis(word='Test123!')

        assert analysis.length == 8
        assert analysis.pattern == 'Ulllnnn@'
        assert len(analysis.char_types) == 8
        assert analysis.char_types[0] == CharType.UPPER
        assert analysis.char_types[1] == CharType.LOWER

    def test_all_uppercase(self):
        analysis = WordAnalysis(word='ABC')

        assert analysis.pattern == 'UUU'

    def test_mixed_pattern(self):
        analysis = WordAnalysis(word='Ab1@')

        assert analysis.pattern == 'Uln@'


class TestAnalysisResult:
    """Tests for AnalysisResult."""

    def test_length_distribution(self):
        length_stats = {
            3: LengthStats(length=3),
            5: LengthStats(length=5),
        }
        length_stats[3].count = 10
        length_stats[5].count = 10

        result = AnalysisResult(
            total_words=20,
            unique_words=20,
            charset={'a', 'b', 'c'},
            discarded_charset=set(),
            length_stats=length_stats,
            global_char_frequency=Counter(),
            global_type_frequency=Counter(),
            min_length=3,
            max_length=5,
        )

        dist = result.length_distribution
        assert dist[3] == 0.5
        assert dist[5] == 0.5

    def test_get_charset_by_type(self):
        result = AnalysisResult(
            total_words=10,
            unique_words=10,
            charset={'A', 'B', 'a', 'b', '1', '2', '!'},
            discarded_charset=set(),
            length_stats={},
            global_char_frequency=Counter(),
            global_type_frequency=Counter(),
            min_length=1,
            max_length=5,
        )

        upper = result.get_charset_by_type(CharType.UPPER)
        assert upper == {'A', 'B'}

        digits = result.get_charset_by_type(CharType.DIGIT)
        assert digits == {'1', '2'}
