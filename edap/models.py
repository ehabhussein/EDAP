"""
Data models and enums for EDAP.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional
from collections import Counter


class CharType(Enum):
    """Character type classification."""
    UPPER = "U"
    LOWER = "l"
    DIGIT = "n"
    SYMBOL = "@"

    @classmethod
    def from_char(cls, char: str) -> "CharType":
        """Classify a single character."""
        if char.isupper():
            return cls.UPPER
        if char.islower():
            return cls.LOWER
        if char.isdigit():
            return cls.DIGIT
        return cls.SYMBOL

    def __str__(self) -> str:
        return self.value


@dataclass
class PositionStats:
    """Statistics for a specific position in words of a given length."""
    position: int
    length: int  # The word length this position belongs to
    char_counts: Counter = field(default_factory=Counter)
    type_counts: Counter = field(default_factory=Counter)

    @property
    def total_chars(self) -> int:
        return sum(self.char_counts.values())

    def add_char(self, char: str) -> None:
        """Record a character at this position."""
        self.char_counts[char] += 1
        self.type_counts[CharType.from_char(char)] += 1

    def get_char_probability(self, char: str) -> float:
        """Get probability of a specific character at this position."""
        total = self.total_chars
        if total == 0:
            return 0.0
        return self.char_counts[char] / total

    def get_type_probability(self, char_type: CharType) -> float:
        """Get probability of a character type at this position."""
        total = self.total_chars
        if total == 0:
            return 0.0
        return self.type_counts[char_type] / total

    def get_weighted_chars(self) -> List[tuple]:
        """Return characters sorted by frequency (most common first)."""
        return self.char_counts.most_common()

    def get_chars_by_type(self, char_type: CharType) -> List[str]:
        """Get all characters of a specific type seen at this position."""
        return [c for c in self.char_counts if CharType.from_char(c) == char_type]


@dataclass
class LengthStats:
    """Statistics for words of a specific length."""
    length: int
    count: int = 0
    positions: Dict[int, PositionStats] = field(default_factory=dict)
    patterns: Counter = field(default_factory=Counter)  # e.g., "UllnnU" -> count

    def __post_init__(self):
        # Initialize position stats for each position
        for i in range(self.length):
            if i not in self.positions:
                self.positions[i] = PositionStats(position=i, length=self.length)

    @property
    def probability(self) -> float:
        """Probability placeholder - set by analyzer."""
        return 0.0

    def add_word(self, word: str) -> None:
        """Analyze and record a word of this length."""
        if len(word) != self.length:
            raise ValueError(f"Word '{word}' length {len(word)} != expected {self.length}")

        self.count += 1
        pattern = ""

        for i, char in enumerate(word):
            self.positions[i].add_char(char)
            pattern += str(CharType.from_char(char))

        self.patterns[pattern] += 1

    def get_common_patterns(self, n: int = 10) -> List[tuple]:
        """Get the N most common character type patterns."""
        return self.patterns.most_common(n)


@dataclass
class WordAnalysis:
    """Complete analysis of a single word."""
    word: str
    length: int = field(init=False)
    pattern: str = field(init=False)
    char_types: List[CharType] = field(init=False)
    char_weights: Dict[int, int] = field(default_factory=dict)

    def __post_init__(self):
        self.length = len(self.word)
        self.char_types = [CharType.from_char(c) for c in self.word]
        self.pattern = "".join(str(t) for t in self.char_types)


@dataclass
class AnalysisResult:
    """Complete analysis result from PatternAnalyzer."""
    total_words: int
    unique_words: int
    charset: Set[str]
    discarded_charset: Set[str]
    length_stats: Dict[int, LengthStats]
    global_char_frequency: Counter
    global_type_frequency: Counter
    min_length: int
    max_length: int

    # Co-occurrence data: char -> position -> next_position -> set of chars seen
    cooccurrence: Dict[str, Dict[int, Dict[int, Set[str]]]] = field(default_factory=dict)

    @property
    def length_distribution(self) -> Dict[int, float]:
        """Get probability distribution of word lengths."""
        total = sum(ls.count for ls in self.length_stats.values())
        if total == 0:
            return {}
        return {length: ls.count / total for length, ls in self.length_stats.items()}

    def get_charset_by_type(self, char_type: CharType) -> Set[str]:
        """Get all characters of a specific type in the charset."""
        return {c for c in self.charset if CharType.from_char(c) == char_type}

    def summary(self) -> str:
        """Generate a summary string of the analysis."""
        lines = [
            f"Total words analyzed: {self.total_words}",
            f"Unique words: {self.unique_words}",
            f"Length range: {self.min_length} - {self.max_length}",
            f"Charset size: {len(self.charset)}",
            f"Charset: {''.join(sorted(self.charset))}",
            "",
            "Length distribution:",
        ]

        for length, prob in sorted(self.length_distribution.items()):
            count = self.length_stats[length].count
            bar = "#" * int(prob * 50)
            lines.append(f"  {length:3d}: {bar} ({count} words, {prob:.1%})")

        lines.extend([
            "",
            "Character type frequency:",
        ])
        total_chars = sum(self.global_type_frequency.values())
        for char_type in CharType:
            count = self.global_type_frequency[char_type]
            pct = count / total_chars * 100 if total_chars > 0 else 0
            lines.append(f"  {char_type.name:8s}: {count:6d} ({pct:.1f}%)")

        return "\n".join(lines)
