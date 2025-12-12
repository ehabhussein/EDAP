"""
Base generator class for EDAP.
"""

import secrets
from abc import ABC, abstractmethod
from typing import Iterator, List, Optional, Set

from edap.models import AnalysisResult, CharType


class BaseGenerator(ABC):
    """
    Abstract base class for string generators.

    All generators use the analysis result to generate new strings
    that match learned patterns.
    """

    def __init__(
        self,
        analysis: AnalysisResult,
        seed: Optional[int] = None,
        exclude_original: bool = True,
    ):
        """
        Initialize the generator.

        Args:
            analysis: Analysis result from PatternAnalyzer
            seed: Random seed for reproducibility (None for secure random)
            exclude_original: If True, don't generate words from original set
        """
        self.analysis = analysis
        self.exclude_original = exclude_original
        self._original_words: Set[str] = set()
        self._generated: Set[str] = set()

        # Use secrets for cryptographic randomness by default
        # For reproducibility, we'd need to use random module with seed
        self._use_secure_random = seed is None
        if seed is not None:
            import random
            self._rng = random.Random(seed)
        else:
            self._rng = None

    def _random_choice(self, seq: list):
        """Choose a random element from a sequence."""
        if not seq:
            raise ValueError("Cannot choose from empty sequence")
        if self._use_secure_random:
            return secrets.choice(seq)
        return self._rng.choice(seq)

    def _weighted_choice(self, weights: dict):
        """
        Choose a key based on weights (values).

        Args:
            weights: Dict of {item: weight}

        Returns:
            A randomly chosen key, weighted by value
        """
        if not weights:
            raise ValueError("Cannot choose from empty weights")

        items = list(weights.keys())
        weight_values = list(weights.values())
        total = sum(weight_values)

        if total == 0:
            return self._random_choice(items)

        if self._use_secure_random:
            r = secrets.randbelow(total)
        else:
            r = self._rng.randint(0, total - 1)

        cumulative = 0
        for item, weight in zip(items, weight_values):
            cumulative += weight
            if r < cumulative:
                return item

        return items[-1]  # Fallback

    def _choose_length(self) -> int:
        """Choose a word length based on the length distribution."""
        length_weights = {
            length: ls.count
            for length, ls in self.analysis.length_stats.items()
        }
        return self._weighted_choice(length_weights)

    def set_original_words(self, words: Set[str]) -> None:
        """Set the original wordlist for exclusion checking."""
        self._original_words = words

    def is_duplicate(self, word: str) -> bool:
        """Check if word is a duplicate (original or already generated)."""
        if self.exclude_original and word in self._original_words:
            return True
        return word in self._generated

    @abstractmethod
    def generate_one(self) -> Optional[str]:
        """
        Generate a single new string.

        Returns:
            Generated string, or None if generation failed
        """
        pass

    def generate(
        self,
        count: int,
        max_attempts: int = 0,
        allow_duplicates: bool = False,
    ) -> List[str]:
        """
        Generate multiple strings.

        Args:
            count: Number of strings to generate
            max_attempts: Max attempts before giving up (0 = count * 100)
            allow_duplicates: If True, allow duplicate generation

        Returns:
            List of generated strings
        """
        if max_attempts == 0:
            max_attempts = count * 100

        results = []
        attempts = 0

        while len(results) < count and attempts < max_attempts:
            attempts += 1
            word = self.generate_one()

            if word is None:
                continue

            if not allow_duplicates and self.is_duplicate(word):
                continue

            results.append(word)
            self._generated.add(word)

        return results

    def generate_iter(
        self,
        count: int,
        max_attempts_per: int = 100,
    ) -> Iterator[str]:
        """
        Generate strings as an iterator.

        Args:
            count: Number of strings to generate
            max_attempts_per: Max attempts per string before giving up

        Yields:
            Generated strings
        """
        generated = 0
        while generated < count:
            attempts = 0
            while attempts < max_attempts_per:
                attempts += 1
                word = self.generate_one()

                if word is None:
                    continue

                if not self.is_duplicate(word):
                    self._generated.add(word)
                    yield word
                    generated += 1
                    break
            else:
                # Max attempts reached for this word, move on
                generated += 1

    def calculate_weight(self, word: str) -> int:
        """
        Calculate the weight/score of a generated word.

        Higher weight means the word better matches observed patterns.
        """
        length = len(word)
        if length not in self.analysis.length_stats:
            return 0

        length_stats = self.analysis.length_stats[length]
        weight = 0

        for i, char in enumerate(word):
            if i in length_stats.positions:
                weight += length_stats.positions[i].char_counts.get(char, 0)

        return weight
