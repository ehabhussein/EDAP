"""Tests for EDAP generators."""

import pytest
from collections import Counter

from edap.analyzer import PatternAnalyzer
from edap.generators import (
    RandomGenerator,
    SmartGenerator,
    PatternGenerator,
    RegexGenerator,
)
from edap.models import CharType


@pytest.fixture
def simple_analysis():
    """Create a simple analysis result for testing."""
    analyzer = PatternAnalyzer()
    words = [
        'abc', 'abd', 'abe',
        'ABC', 'ABD', 'ABE',
        'a1c', 'a2c', 'a3c',
    ]
    return analyzer.analyze_words(words)


@pytest.fixture
def varied_length_analysis():
    """Create analysis with variable length words."""
    analyzer = PatternAnalyzer()
    words = [
        'ab', 'cd', 'ef',
        'abc', 'def', 'ghi',
        'abcd', 'efgh', 'ijkl',
    ]
    return analyzer.analyze_words(words)


class TestRandomGenerator:
    """Tests for RandomGenerator."""

    def test_generate_one(self, simple_analysis):
        gen = RandomGenerator(simple_analysis, seed=42)
        word = gen.generate_one()

        assert word is not None
        assert len(word) == 3

    def test_generate_multiple(self, simple_analysis):
        gen = RandomGenerator(simple_analysis, seed=42)
        words = gen.generate(10)

        assert len(words) == 10
        for word in words:
            assert len(word) == 3

    def test_generate_uses_charset(self, simple_analysis):
        gen = RandomGenerator(simple_analysis, seed=42)
        words = gen.generate(100)

        all_chars = set(''.join(words))
        # All generated chars should be from the analysis charset
        assert all_chars <= simple_analysis.charset

    def test_generate_with_seed_reproducible(self, simple_analysis):
        gen1 = RandomGenerator(simple_analysis, seed=42)
        gen2 = RandomGenerator(simple_analysis, seed=42)

        words1 = gen1.generate(10)
        words2 = gen2.generate(10)

        assert words1 == words2

    def test_generate_variable_length(self, varied_length_analysis):
        gen = RandomGenerator(varied_length_analysis, seed=42)
        words = gen.generate(30)

        lengths = Counter(len(w) for w in words)
        # Should generate words of different lengths
        assert len(lengths) > 1

    def test_exclude_original(self, simple_analysis):
        gen = RandomGenerator(simple_analysis, seed=42, exclude_original=True)
        gen.set_original_words({'abc', 'abd', 'abe'})

        words = gen.generate(50)

        # Should not contain original words
        assert 'abc' not in words
        assert 'abd' not in words
        assert 'abe' not in words


class TestSmartGenerator:
    """Tests for SmartGenerator."""

    def test_generate_one(self, simple_analysis):
        gen = SmartGenerator(simple_analysis, seed=42)
        word = gen.generate_one()

        assert word is not None
        assert len(word) == 3

    def test_generate_multiple(self, simple_analysis):
        gen = SmartGenerator(simple_analysis, seed=42)
        words = gen.generate(10)

        assert len(words) <= 10  # May be fewer due to strict matching

    def test_generate_respects_cooccurrence(self, simple_analysis):
        """Test that smart generator uses co-occurrence data."""
        gen = SmartGenerator(simple_analysis, seed=42)

        # Generate many words and check patterns
        words = gen.generate(50)

        # Words should follow patterns seen in training data
        # The first position should mostly have 'a' or 'A' (common in training)
        first_chars = Counter(w[0] for w in words if w)
        assert 'a' in first_chars or 'A' in first_chars

    def test_calculate_weight(self, simple_analysis):
        gen = SmartGenerator(simple_analysis, seed=42)

        # A word matching training patterns should have higher weight
        weight_abc = gen.calculate_weight('abc')
        assert weight_abc > 0


class TestPatternGenerator:
    """Tests for PatternGenerator."""

    def test_generate_one(self, simple_analysis):
        gen = PatternGenerator(simple_analysis, seed=42)
        word = gen.generate_one()

        assert word is not None
        assert len(word) == 3

    def test_generate_follows_pattern(self, simple_analysis):
        gen = PatternGenerator(simple_analysis, seed=42)
        words = gen.generate(20)

        # Each word should match a pattern from training
        valid_patterns = {'lll', 'UUU', 'lnl'}

        for word in words:
            if word:
                pattern = ''.join(str(CharType.from_char(c)) for c in word)
                assert pattern in valid_patterns

    def test_generate_from_explicit_pattern(self, simple_analysis):
        gen = PatternGenerator(simple_analysis, seed=42)

        # Generate with explicit lowercase pattern
        word = gen.generate_from_explicit_pattern('lll')

        if word:
            assert word.islower() or all(c.islower() or c.isdigit() for c in word)

    def test_get_available_patterns(self, simple_analysis):
        gen = PatternGenerator(simple_analysis, seed=42)

        patterns = gen.get_available_patterns(length=3)

        assert len(patterns) > 0
        # Most common pattern should be first
        assert patterns[0][1] >= patterns[-1][1]


class TestRegexGenerator:
    """Tests for RegexGenerator."""

    def test_generate_simple_pattern(self, simple_analysis):
        gen = RegexGenerator(
            simple_analysis,
            pattern=r'[a-z]{3}',
            seed=42,
        )

        word = gen.generate_one()

        if word:
            assert len(word) == 3
            assert word.islower()

    def test_generate_digit_pattern(self, simple_analysis):
        gen = RegexGenerator(
            simple_analysis,
            pattern=r'\d{3}',
            seed=42,
            use_learned_charset=False,  # Allow any digits
        )

        words = gen.generate(10)

        for word in words:
            if word:
                assert word.isdigit()
                assert len(word) == 3

    def test_generate_mixed_pattern(self, simple_analysis):
        gen = RegexGenerator(
            simple_analysis,
            pattern=r'[A-Z][a-z]\d',
            seed=42,
            use_learned_charset=False,
        )

        word = gen.generate_one()

        if word:
            assert len(word) == 3
            assert word[0].isupper()
            assert word[1].islower()
            assert word[2].isdigit()

    def test_generate_with_quantifier(self, simple_analysis):
        gen = RegexGenerator(
            simple_analysis,
            pattern=r'[a-z]{2,4}',
            seed=42,
        )

        words = gen.generate(20)

        for word in words:
            if word:
                assert 2 <= len(word) <= 4

    def test_generate_validated(self, simple_analysis):
        gen = RegexGenerator(
            simple_analysis,
            pattern=r'^[a-z]{3}$',
            seed=42,
        )

        words = gen.generate_validated(10)

        # All words should match the full pattern
        import re
        pattern = re.compile(r'^[a-z]{3}$')

        for word in words:
            assert pattern.match(word)

    def test_generate_alternation(self, simple_analysis):
        """Test that alternation (|) works in regex patterns."""
        gen = RegexGenerator(
            simple_analysis,
            pattern=r'(user|admin)[0-9]{3}',
            seed=42,
            use_learned_charset=False,
        )

        words = gen.generate(10)

        import re
        pattern = re.compile(r'^(user|admin)[0-9]{3}$')

        for word in words:
            assert pattern.match(word)
            assert word.startswith('user') or word.startswith('admin')

    def test_generate_top_level_alternation(self, simple_analysis):
        """Test top-level alternation without parentheses."""
        gen = RegexGenerator(
            simple_analysis,
            pattern=r'hello|world',
            seed=42,
            use_learned_charset=False,
        )

        words = gen.generate(10)

        for word in words:
            assert word in ['hello', 'world']


class TestGeneratorWeight:
    """Tests for weight calculation across generators."""

    def test_weight_higher_for_matching_patterns(self):
        """Words matching training patterns should have higher weights."""
        analyzer = PatternAnalyzer()
        # Training data has strong pattern: first char is 'a'
        words = ['abc', 'abd', 'abe', 'abf', 'abg'] * 10
        result = analyzer.analyze_words(words)

        gen = SmartGenerator(result, seed=42)

        # Word starting with 'a' should have higher weight
        weight_abc = gen.calculate_weight('abc')
        weight_xyz = gen.calculate_weight('xyz')

        assert weight_abc > weight_xyz
