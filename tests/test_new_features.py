"""Tests for new EDAP features."""

import pytest
from edap import (
    PatternAnalyzer,
    MarkovGenerator,
    HybridGenerator,
    create_hybrid_generator,
    SmartGenerator,
    RandomGenerator,
    Mutator,
    RULE_PRESETS,
    Scorer,
    Filter,
    FilterConfig,
    create_filter,
    FILTER_PRESETS,
    StatsExporter,
)


@pytest.fixture
def sample_words():
    """Sample words for testing."""
    return [
        "password",
        "Password1",
        "admin123",
        "Admin@2024",
        "test",
        "Test123!",
        "hello",
        "Hello123",
        "world",
        "World2025",
    ]


@pytest.fixture
def analysis(sample_words):
    """Analysis result for testing."""
    analyzer = PatternAnalyzer()
    return analyzer.analyze_words(sample_words)


class TestMarkovGenerator:
    """Tests for MarkovGenerator."""

    def test_create(self, analysis):
        gen = MarkovGenerator(analysis, seed=42)
        assert gen is not None

    def test_generate_one(self, analysis):
        gen = MarkovGenerator(analysis, seed=42)
        word = gen.generate_one()
        assert word is not None
        assert len(word) > 0

    def test_generate_multiple(self, analysis):
        gen = MarkovGenerator(analysis, seed=42)
        words = gen.generate(5)
        assert len(words) == 5

    def test_train_on_words(self, analysis, sample_words):
        gen = MarkovGenerator(analysis, seed=42, order=2)
        gen.train_on_words(sample_words)
        word = gen.generate_one()
        assert word is not None

    def test_different_orders(self, analysis, sample_words):
        for order in [1, 2, 3]:
            gen = MarkovGenerator(analysis, seed=42, order=order)
            gen.train_on_words(sample_words)
            word = gen.generate_one()
            assert word is not None


class TestHybridGenerator:
    """Tests for HybridGenerator."""

    def test_create(self, analysis):
        gen = HybridGenerator(
            analysis,
            generators=[
                (SmartGenerator, 0.5, {}),
                (RandomGenerator, 0.5, {}),
            ],
            seed=42,
        )
        assert gen is not None

    def test_generate_one(self, analysis):
        gen = HybridGenerator(
            analysis,
            generators=[
                (SmartGenerator, 0.6, {}),
                (RandomGenerator, 0.4, {}),
            ],
            seed=42,
        )
        word = gen.generate_one()
        assert word is not None

    def test_generate_multiple(self, analysis):
        gen = HybridGenerator(
            analysis,
            generators=[
                (SmartGenerator, 0.7, {}),
                (RandomGenerator, 0.3, {}),
            ],
            seed=42,
        )
        words = gen.generate(10)
        assert len(words) == 10

    def test_create_hybrid_balanced(self, analysis):
        gen = create_hybrid_generator(analysis, mode="balanced", seed=42)
        words = gen.generate(5)
        assert len(words) == 5

    def test_create_hybrid_strict(self, analysis):
        gen = create_hybrid_generator(analysis, mode="strict", seed=42)
        words = gen.generate(5)
        assert len(words) == 5

    def test_create_hybrid_creative(self, analysis):
        gen = create_hybrid_generator(analysis, mode="creative", seed=42)
        words = gen.generate(5)
        assert len(words) == 5


class TestMutator:
    """Tests for Mutator."""

    def test_create(self):
        mutator = Mutator(seed=42)
        assert mutator is not None

    def test_list_rules(self):
        mutator = Mutator()
        rules = mutator.list_rules()
        assert len(rules) > 0
        assert "lowercase" in rules
        assert "uppercase" in rules

    def test_apply_lowercase(self):
        mutator = Mutator()
        result = mutator.apply_rule("HELLO", "lowercase")
        assert result == "hello"

    def test_apply_uppercase(self):
        mutator = Mutator()
        result = mutator.apply_rule("hello", "uppercase")
        assert result == "HELLO"

    def test_apply_capitalize(self):
        mutator = Mutator()
        result = mutator.apply_rule("hello", "capitalize")
        assert result == "Hello"

    def test_apply_reverse(self):
        mutator = Mutator()
        result = mutator.apply_rule("hello", "reverse")
        assert result == "olleh"

    def test_apply_leetspeak(self):
        mutator = Mutator()
        result = mutator.apply_rule("password", "leetspeak")
        assert "4" in result or "$" in result

    def test_apply_append(self):
        mutator = Mutator()
        result = mutator.apply_rule("password", "append_123")
        assert result == "password123"

    def test_apply_multiple_rules(self):
        mutator = Mutator()
        result = mutator.apply_rules("hello", ["uppercase", "reverse"])
        assert result == "OLLEH"

    def test_mutate_random(self):
        mutator = Mutator(seed=42)
        result = mutator.mutate("password", num_mutations=2)
        assert result != "password"

    def test_expand(self):
        mutator = Mutator()
        expanded = list(mutator.expand("test", rules=["uppercase", "lowercase"]))
        assert "test" in expanded
        assert "TEST" in expanded

    def test_presets(self):
        assert "basic" in RULE_PRESETS
        assert "leet" in RULE_PRESETS
        assert "common" in RULE_PRESETS


class TestScorer:
    """Tests for Scorer."""

    def test_create(self):
        scorer = Scorer()
        assert scorer is not None

    def test_score_empty(self):
        scorer = Scorer()
        result = scorer.score("")
        assert result.score == 0
        assert result.length == 0

    def test_score_weak(self):
        scorer = Scorer()
        result = scorer.score("password")
        assert result.score < 40
        assert result.rating in ["Very Weak", "Weak"]

    def test_score_moderate(self):
        scorer = Scorer()
        result = scorer.score("Password1")
        assert result.score >= 20

    def test_score_strong(self):
        scorer = Scorer()
        result = scorer.score("MyP@ssw0rd!2024")
        assert result.score >= 50
        assert result.has_upper
        assert result.has_lower
        assert result.has_digit
        assert result.has_symbol

    def test_score_entropy(self):
        scorer = Scorer()
        short = scorer.score("abc")
        long = scorer.score("abcdefghijklmnop")
        assert long.entropy > short.entropy

    def test_score_feedback(self):
        scorer = Scorer()
        result = scorer.score("abc")
        assert len(result.feedback) > 0

    def test_score_many(self):
        scorer = Scorer()
        results = scorer.score_many(["abc", "Password1!", "test"])
        assert len(results) == 3

    def test_average_score(self):
        scorer = Scorer()
        avg = scorer.average_score(["abc", "Password1!", "test"])
        assert 0 <= avg <= 100

    def test_filter_by_strength(self):
        scorer = Scorer()
        passwords = ["a", "Password1!", "MyS3cur3P@ss!"]
        strong = scorer.filter_by_strength(passwords, min_score=40)
        assert len(strong) < len(passwords)


class TestFilter:
    """Tests for Filter."""

    def test_create(self):
        f = Filter()
        assert f is not None

    def test_length_filter(self):
        config = FilterConfig(min_length=8, max_length=12)
        f = Filter(config)
        assert f.passes("password")  # 8 chars
        assert f.passes("password123")  # 11 chars
        assert not f.passes("abc")  # 3 chars
        assert not f.passes("verylongpassword")  # 16 chars

    def test_exact_length(self):
        config = FilterConfig(exact_length=8)
        f = Filter(config)
        assert f.passes("password")
        assert not f.passes("pass")

    def test_char_type_filter(self):
        config = FilterConfig(require_upper=True, require_digit=True)
        f = Filter(config)
        assert f.passes("Password1")
        assert not f.passes("password1")
        assert not f.passes("Password")

    def test_min_char_types(self):
        config = FilterConfig(min_char_types=3)
        f = Filter(config)
        assert f.passes("Password1")  # upper, lower, digit
        assert not f.passes("password")  # only lower

    def test_score_filter(self):
        config = FilterConfig(min_score=40)
        f = Filter(config)
        assert f.passes("Password1!")
        assert not f.passes("abc")

    def test_pattern_filter(self):
        config = FilterConfig(must_match=r"^[A-Z]")
        f = Filter(config)
        assert f.passes("Password")
        assert not f.passes("password")

    def test_must_not_match(self):
        config = FilterConfig(must_not_match=r"password")
        f = Filter(config)
        assert not f.passes("password123")
        assert f.passes("secret123")

    def test_exclude_words(self):
        config = FilterConfig(exclude_words={"password", "admin"})
        f = Filter(config)
        assert not f.passes("password")
        assert not f.passes("admin")
        assert f.passes("secret")

    def test_filter_list(self):
        f = create_filter(min_length=5, require_digit=True)
        words = ["abc", "hello", "hello1", "test123"]
        filtered = f.filter(words)
        assert "hello1" in filtered
        assert "test123" in filtered
        assert "abc" not in filtered

    def test_presets(self):
        assert "strong" in FILTER_PRESETS
        assert "complex" in FILTER_PRESETS


class TestStatsExporter:
    """Tests for StatsExporter."""

    def test_create(self, analysis):
        exporter = StatsExporter(analysis)
        assert exporter is not None

    def test_to_dict(self, analysis):
        exporter = StatsExporter(analysis)
        data = exporter.to_dict()
        assert "summary" in data
        assert "charset" in data
        assert "length_distribution" in data

    def test_to_json(self, analysis):
        exporter = StatsExporter(analysis)
        json_str = exporter.to_json()
        assert len(json_str) > 0
        import json
        parsed = json.loads(json_str)
        assert "summary" in parsed

    def test_to_csv(self, analysis):
        exporter = StatsExporter(analysis)
        csv_str = exporter.to_csv()
        assert "Length" in csv_str
        assert "Count" in csv_str

    def test_to_position_csv(self, analysis):
        exporter = StatsExporter(analysis)
        csv_str = exporter.to_position_csv()
        assert "Position" in csv_str

    def test_to_summary(self, analysis):
        exporter = StatsExporter(analysis)
        summary = exporter.to_summary()
        assert "EDAP Analysis Summary" in summary
        assert "Total words" in summary
