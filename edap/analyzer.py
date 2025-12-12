"""
Pattern analysis module for EDAP.
Handles character frequency, position analysis, and co-occurrence patterns.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, TextIO, Union

from edap.models import (
    AnalysisResult,
    CharType,
    LengthStats,
    PositionStats,
    WordAnalysis,
)

logger = logging.getLogger(__name__)


# Standard keyboard charset for reference
FULL_KEYBOARD = set(
    "`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./"
    "~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:\"ZXCVBNM<>?"
)


class PatternAnalyzer:
    """
    Analyzes patterns in a wordlist to build statistical models.

    Supports variable-length words and builds per-length statistics.
    """

    def __init__(self, min_length: int = 1, max_length: int = 256):
        """
        Initialize the analyzer.

        Args:
            min_length: Minimum word length to analyze (inclusive)
            max_length: Maximum word length to analyze (inclusive)
        """
        self.min_length = min_length
        self.max_length = max_length
        self._reset()

    def _reset(self) -> None:
        """Reset all analysis state."""
        self._words: List[str] = []
        self._unique_words: Set[str] = set()
        self._charset: Set[str] = set()
        self._length_stats: Dict[int, LengthStats] = {}
        self._global_char_freq: Counter = Counter()
        self._global_type_freq: Counter = Counter()
        self._cooccurrence: Dict[str, Dict[int, Dict[int, Set[str]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(set))
        )
        self._analyzed = False

    def analyze_file(
        self,
        filepath: Union[str, Path],
        encoding: str = "utf-8",
        skip_errors: bool = True,
    ) -> AnalysisResult:
        """
        Analyze words from a file.

        Args:
            filepath: Path to the wordlist file
            encoding: File encoding
            skip_errors: If True, skip lines that can't be decoded

        Returns:
            AnalysisResult with complete statistics
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        self._reset()
        error_mode = "ignore" if skip_errors else "strict"

        logger.info(f"Analyzing file: {filepath}")

        with open(filepath, "r", encoding=encoding, errors=error_mode) as f:
            self._analyze_stream(f)

        return self._build_result()

    def analyze_words(self, words: List[str]) -> AnalysisResult:
        """
        Analyze a list of words directly.

        Args:
            words: List of words to analyze

        Returns:
            AnalysisResult with complete statistics
        """
        self._reset()
        self._analyze_stream(iter(words))
        return self._build_result()

    def _analyze_stream(self, stream: Iterator[str]) -> None:
        """Process words from any iterable source."""
        for line in stream:
            word = line.strip()
            if not word:
                continue

            length = len(word)
            if length < self.min_length or length > self.max_length:
                logger.debug(f"Skipping word of length {length}: {word[:20]}...")
                continue

            self._process_word(word)

        self._analyzed = True
        logger.info(
            f"Analysis complete: {len(self._words)} words, "
            f"{len(self._unique_words)} unique"
        )

    def _process_word(self, word: str) -> None:
        """Process a single word and update all statistics."""
        self._words.append(word)
        self._unique_words.add(word)

        length = len(word)

        # Initialize length stats if needed
        if length not in self._length_stats:
            self._length_stats[length] = LengthStats(length=length)

        # Update length-specific stats
        self._length_stats[length].add_word(word)

        # Update global frequencies and charset
        for i, char in enumerate(word):
            self._charset.add(char)
            self._global_char_freq[char] += 1
            self._global_type_freq[CharType.from_char(char)] += 1

            # Build co-occurrence matrix
            # For each char at position i, record what chars appear at other positions
            for j, other_char in enumerate(word):
                if i != j:
                    self._cooccurrence[char][i][j].add(other_char)

    def _build_result(self) -> AnalysisResult:
        """Build the final analysis result."""
        if not self._analyzed:
            raise RuntimeError("No analysis has been performed yet")

        lengths = list(self._length_stats.keys())
        min_len = min(lengths) if lengths else 0
        max_len = max(lengths) if lengths else 0

        # Calculate discarded charset (keyboard chars not seen)
        discarded = FULL_KEYBOARD - self._charset

        return AnalysisResult(
            total_words=len(self._words),
            unique_words=len(self._unique_words),
            charset=self._charset.copy(),
            discarded_charset=discarded,
            length_stats=self._length_stats.copy(),
            global_char_frequency=self._global_char_freq.copy(),
            global_type_frequency=self._global_type_freq.copy(),
            min_length=min_len,
            max_length=max_len,
            cooccurrence=dict(self._cooccurrence),
        )

    def get_word_analysis(self, word: str) -> WordAnalysis:
        """
        Get detailed analysis of a single word.

        Includes character weights based on position frequency.
        """
        analysis = WordAnalysis(word=word)
        length = len(word)

        if length in self._length_stats:
            length_stat = self._length_stats[length]
            for i, char in enumerate(word):
                if i in length_stat.positions:
                    # Weight = how often this char appears at this position
                    analysis.char_weights[i] = length_stat.positions[i].char_counts[char]

        return analysis

    def print_detailed_stats(self, result: Optional[AnalysisResult] = None) -> None:
        """Print detailed statistics (mimics original verbose output)."""
        if result is None:
            result = self._build_result()

        print("\n" + "=" * 60)
        print("EDAP Pattern Analysis Results")
        print("=" * 60)

        print(result.summary())

        # Print per-length position analysis
        print("\n" + "-" * 60)
        print("Position Analysis by Length")
        print("-" * 60)

        for length in sorted(result.length_stats.keys()):
            ls = result.length_stats[length]
            print(f"\nLength {length} ({ls.count} words):")

            # Show type distribution per position
            for pos in range(length):
                ps = ls.positions[pos]
                type_dist = []
                for ct in CharType:
                    prob = ps.get_type_probability(ct)
                    if prob > 0:
                        type_dist.append(f"{ct.value}:{prob:.0%}")
                print(f"  Position {pos}: {', '.join(type_dist)}")

            # Show top patterns
            patterns = ls.get_common_patterns(5)
            if patterns:
                print(f"  Top patterns: {patterns}")

        # Print character frequency
        print("\n" + "-" * 60)
        print("Top 20 Characters by Frequency")
        print("-" * 60)
        for char, count in result.global_char_frequency.most_common(20):
            char_display = repr(char) if char in " \t\n" else char
            print(f"  {char_display}: {count}")
