"""
Filter options for generated strings.
"""

import re
from typing import List, Optional, Callable, Iterator, Set
from dataclasses import dataclass, field

from edap.scorer import Scorer


@dataclass
class FilterConfig:
    """Configuration for filtering generated strings."""
    # Length filters
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    exact_length: Optional[int] = None

    # Character type filters
    require_upper: bool = False
    require_lower: bool = False
    require_digit: bool = False
    require_symbol: bool = False
    min_char_types: int = 0  # Minimum different character types

    # Strength filters
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    min_entropy: Optional[float] = None

    # Pattern filters
    must_match: Optional[str] = None  # Regex that must match
    must_not_match: Optional[str] = None  # Regex that must not match
    must_contain: Optional[str] = None  # Substring that must be present
    must_not_contain: Optional[str] = None  # Substring that must not be present

    # Charset filters
    allowed_chars: Optional[Set[str]] = None  # Only these chars allowed
    forbidden_chars: Optional[Set[str]] = None  # These chars not allowed

    # Uniqueness
    exclude_words: Set[str] = field(default_factory=set)  # Exclude these specific words


class Filter:
    """
    Filter generated strings based on various criteria.

    Supports filtering by:
    - Length
    - Character type requirements
    - Strength score
    - Regex patterns
    - Allowed/forbidden characters
    """

    def __init__(self, config: Optional[FilterConfig] = None):
        """
        Initialize the filter.

        Args:
            config: Filter configuration
        """
        self.config = config or FilterConfig()
        self._scorer = Scorer()
        self._compiled_must_match: Optional[re.Pattern] = None
        self._compiled_must_not_match: Optional[re.Pattern] = None

        if self.config.must_match:
            self._compiled_must_match = re.compile(self.config.must_match)
        if self.config.must_not_match:
            self._compiled_must_not_match = re.compile(self.config.must_not_match)

    def passes(self, s: str) -> bool:
        """
        Check if a string passes all filters.

        Args:
            s: String to check

        Returns:
            True if passes all filters
        """
        # Exclusion check
        if s in self.config.exclude_words:
            return False

        # Length checks
        if self.config.exact_length is not None:
            if len(s) != self.config.exact_length:
                return False
        else:
            if self.config.min_length is not None and len(s) < self.config.min_length:
                return False
            if self.config.max_length is not None and len(s) > self.config.max_length:
                return False

        # Character type checks
        has_upper = any(c.isupper() for c in s)
        has_lower = any(c.islower() for c in s)
        has_digit = any(c.isdigit() for c in s)
        has_symbol = any(not c.isalnum() for c in s)

        if self.config.require_upper and not has_upper:
            return False
        if self.config.require_lower and not has_lower:
            return False
        if self.config.require_digit and not has_digit:
            return False
        if self.config.require_symbol and not has_symbol:
            return False

        char_types = sum([has_upper, has_lower, has_digit, has_symbol])
        if char_types < self.config.min_char_types:
            return False

        # Strength checks
        if self.config.min_score is not None or self.config.max_score is not None or self.config.min_entropy is not None:
            score = self._scorer.score(s)

            if self.config.min_score is not None and score.score < self.config.min_score:
                return False
            if self.config.max_score is not None and score.score > self.config.max_score:
                return False
            if self.config.min_entropy is not None and score.entropy < self.config.min_entropy:
                return False

        # Pattern checks
        if self._compiled_must_match and not self._compiled_must_match.search(s):
            return False
        if self._compiled_must_not_match and self._compiled_must_not_match.search(s):
            return False

        # Substring checks
        if self.config.must_contain and self.config.must_contain not in s:
            return False
        if self.config.must_not_contain and self.config.must_not_contain in s:
            return False

        # Charset checks
        if self.config.allowed_chars:
            if not all(c in self.config.allowed_chars for c in s):
                return False
        if self.config.forbidden_chars:
            if any(c in self.config.forbidden_chars for c in s):
                return False

        return True

    def filter(self, strings: List[str]) -> List[str]:
        """
        Filter a list of strings.

        Args:
            strings: Input strings

        Returns:
            Filtered list
        """
        return [s for s in strings if self.passes(s)]

    def filter_iter(self, strings: Iterator[str]) -> Iterator[str]:
        """
        Filter an iterator of strings.

        Args:
            strings: Input iterator

        Yields:
            Strings that pass the filter
        """
        for s in strings:
            if self.passes(s):
                yield s

    def count_passing(self, strings: List[str]) -> int:
        """
        Count how many strings pass the filter.

        Args:
            strings: Input strings

        Returns:
            Count of passing strings
        """
        return sum(1 for s in strings if self.passes(s))


def create_filter(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    require_upper: bool = False,
    require_lower: bool = False,
    require_digit: bool = False,
    require_symbol: bool = False,
    min_score: Optional[float] = None,
    min_entropy: Optional[float] = None,
    must_match: Optional[str] = None,
    must_not_match: Optional[str] = None,
    exclude: Optional[List[str]] = None,
) -> Filter:
    """
    Convenience function to create a filter.

    Args:
        min_length: Minimum string length
        max_length: Maximum string length
        require_upper: Require uppercase letters
        require_lower: Require lowercase letters
        require_digit: Require digits
        require_symbol: Require symbols
        min_score: Minimum strength score
        min_entropy: Minimum entropy bits
        must_match: Regex pattern that must match
        must_not_match: Regex pattern that must not match
        exclude: List of words to exclude

    Returns:
        Configured Filter
    """
    config = FilterConfig(
        min_length=min_length,
        max_length=max_length,
        require_upper=require_upper,
        require_lower=require_lower,
        require_digit=require_digit,
        require_symbol=require_symbol,
        min_score=min_score,
        min_entropy=min_entropy,
        must_match=must_match,
        must_not_match=must_not_match,
        exclude_words=set(exclude) if exclude else set(),
    )
    return Filter(config)


# Common filter presets
FILTER_PRESETS = {
    "strong": FilterConfig(
        min_length=12,
        min_char_types=3,
        min_score=60,
    ),
    "very_strong": FilterConfig(
        min_length=16,
        min_char_types=4,
        min_score=80,
    ),
    "alphanumeric": FilterConfig(
        require_upper=True,
        require_lower=True,
        require_digit=True,
    ),
    "complex": FilterConfig(
        min_length=10,
        require_upper=True,
        require_lower=True,
        require_digit=True,
        require_symbol=True,
    ),
    "short": FilterConfig(
        max_length=8,
    ),
    "medium": FilterConfig(
        min_length=8,
        max_length=12,
    ),
    "long": FilterConfig(
        min_length=16,
    ),
}
