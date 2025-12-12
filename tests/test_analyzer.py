"""Tests for EDAP analyzer."""

import pytest
import tempfile
from pathlib import Path

from edap.analyzer import PatternAnalyzer
from edap.models import CharType


class TestPatternAnalyzer:
    """Tests for PatternAnalyzer."""

    def test_analyze_words_basic(self):
        analyzer = PatternAnalyzer()
        words = ['abc', 'def', 'ghi']

        result = analyzer.analyze_words(words)

        assert result.total_words == 3
        assert result.unique_words == 3
        assert result.min_length == 3
        assert result.max_length == 3

    def test_analyze_words_variable_length(self):
        """Test that variable length words are handled correctly."""
        analyzer = PatternAnalyzer()
        words = ['a', 'ab', 'abc', 'abcd', 'abcde']

        result = analyzer.analyze_words(words)

        assert result.total_words == 5
        assert result.min_length == 1
        assert result.max_length == 5
        assert len(result.length_stats) == 5

        # Check each length has correct count
        assert result.length_stats[1].count == 1
        assert result.length_stats[2].count == 1
        assert result.length_stats[5].count == 1

    def test_analyze_words_charset(self):
        analyzer = PatternAnalyzer()
        words = ['ABC', '123', 'abc']

        result = analyzer.analyze_words(words)

        assert 'A' in result.charset
        assert 'a' in result.charset
        assert '1' in result.charset

    def test_analyze_words_frequency(self):
        analyzer = PatternAnalyzer()
        words = ['aaa', 'aab', 'abc']

        result = analyzer.analyze_words(words)

        # 'a' appears 6 times total
        assert result.global_char_frequency['a'] == 6
        assert result.global_char_frequency['b'] == 2
        assert result.global_char_frequency['c'] == 1

    def test_analyze_words_type_frequency(self):
        analyzer = PatternAnalyzer()
        words = ['Abc', 'DEF', '123']

        result = analyzer.analyze_words(words)

        # 4 uppercase, 2 lowercase, 3 digits
        assert result.global_type_frequency[CharType.UPPER] == 4
        assert result.global_type_frequency[CharType.LOWER] == 2
        assert result.global_type_frequency[CharType.DIGIT] == 3

    def test_analyze_words_patterns(self):
        analyzer = PatternAnalyzer()
        words = ['Abc', 'Def', 'Ghi', 'ABC']

        result = analyzer.analyze_words(words)

        length_stats = result.length_stats[3]
        assert length_stats.patterns['Ull'] == 3
        assert length_stats.patterns['UUU'] == 1

    def test_analyze_words_empty(self):
        analyzer = PatternAnalyzer()
        words = []

        result = analyzer.analyze_words(words)

        assert result.total_words == 0
        assert result.unique_words == 0

    def test_analyze_words_duplicates(self):
        analyzer = PatternAnalyzer()
        words = ['abc', 'abc', 'abc', 'def']

        result = analyzer.analyze_words(words)

        assert result.total_words == 4
        assert result.unique_words == 2

    def test_analyze_words_min_max_length_filter(self):
        analyzer = PatternAnalyzer(min_length=3, max_length=5)
        words = ['a', 'ab', 'abc', 'abcd', 'abcde', 'abcdef']

        result = analyzer.analyze_words(words)

        assert result.total_words == 3  # abc, abcd, abcde
        assert result.min_length == 3
        assert result.max_length == 5

    def test_analyze_file(self):
        analyzer = PatternAnalyzer()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('abc\n')
            f.write('def\n')
            f.write('ghi\n')
            filepath = Path(f.name)

        try:
            result = analyzer.analyze_file(filepath)

            assert result.total_words == 3
            assert result.unique_words == 3
        finally:
            filepath.unlink()

    def test_analyze_file_not_found(self):
        analyzer = PatternAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file(Path('/nonexistent/file.txt'))

    def test_analyze_file_with_empty_lines(self):
        analyzer = PatternAnalyzer()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('abc\n')
            f.write('\n')
            f.write('def\n')
            f.write('   \n')
            f.write('ghi\n')
            filepath = Path(f.name)

        try:
            result = analyzer.analyze_file(filepath)

            assert result.total_words == 3
        finally:
            filepath.unlink()

    def test_cooccurrence_tracking(self):
        """Test that character co-occurrence is tracked correctly."""
        analyzer = PatternAnalyzer()
        words = ['abc', 'abd', 'aec']

        result = analyzer.analyze_words(words)

        # 'a' at position 0 should have co-occurrence with 'b', 'e' at position 1
        # and 'c', 'd' at position 2
        cooc = result.cooccurrence

        assert 'a' in cooc
        assert 0 in cooc['a']
        assert 1 in cooc['a'][0]
        assert 'b' in cooc['a'][0][1]
        assert 'e' in cooc['a'][0][1]

    def test_position_stats_per_length(self):
        """Test that position stats are tracked per length."""
        analyzer = PatternAnalyzer()
        words = ['AB', 'CD', 'abc', 'def']

        result = analyzer.analyze_words(words)

        # Length 2 should have different stats than length 3
        len2_stats = result.length_stats[2]
        len3_stats = result.length_stats[3]

        # Position 0 in length 2 words has A, C (uppercase)
        assert len2_stats.positions[0].type_counts[CharType.UPPER] == 2

        # Position 0 in length 3 words has a, d (lowercase)
        assert len3_stats.positions[0].type_counts[CharType.LOWER] == 2

    def test_get_word_analysis(self):
        analyzer = PatternAnalyzer()
        words = ['abc', 'abd', 'aec']
        analyzer.analyze_words(words)

        analysis = analyzer.get_word_analysis('abc')

        assert analysis.word == 'abc'
        assert analysis.length == 3
        assert analysis.pattern == 'lll'
        # 'a' appears 3 times at position 0
        assert analysis.char_weights[0] == 3
