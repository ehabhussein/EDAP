"""
Pattern generator - generates strings matching character type patterns.
"""

from typing import Optional, List

from edap.generators.base import BaseGenerator
from edap.models import AnalysisResult, CharType


class PatternGenerator(BaseGenerator):
    """
    Generates strings that match observed character type patterns.

    This is the most strict generator - it ensures generated strings
    follow patterns like "UllnnU" (Upper, lower, lower, digit, digit, Upper).
    """

    def __init__(
        self,
        analysis: AnalysisResult,
        seed: Optional[int] = None,
        exclude_original: bool = True,
        max_retries_per_position: int = 100,
    ):
        """
        Initialize the pattern generator.

        Args:
            analysis: Analysis result from PatternAnalyzer
            seed: Random seed for reproducibility
            exclude_original: If True, don't generate words from original set
            max_retries_per_position: Max retries when finding compatible char
        """
        super().__init__(analysis, seed, exclude_original)
        self.max_retries = max_retries_per_position

    def _choose_pattern(self, length: int) -> Optional[str]:
        """Choose a pattern for the given length based on frequency."""
        if length not in self.analysis.length_stats:
            return None

        length_stats = self.analysis.length_stats[length]
        if not length_stats.patterns:
            return None

        return self._weighted_choice(dict(length_stats.patterns))

    def generate_one(self) -> Optional[str]:
        """
        Generate a string matching a randomly chosen pattern.

        Algorithm:
        1. Choose a length based on distribution
        2. Choose a pattern for that length (e.g., "UllnnU")
        3. Fill each position with a character of the required type
        4. Use co-occurrence to prefer compatible characters
        """
        length = self._choose_length()

        if length not in self.analysis.length_stats:
            return None

        pattern = self._choose_pattern(length)
        if not pattern or len(pattern) != length:
            return None

        return self._generate_from_pattern(pattern)

    def _generate_from_pattern(self, pattern: str) -> Optional[str]:
        """Generate a string following the exact pattern."""
        length = len(pattern)

        if length not in self.analysis.length_stats:
            # No stats for this length - use global charset
            return self._generate_from_pattern_global(pattern)

        length_stats = self.analysis.length_stats[length]
        cooc = self.analysis.cooccurrence

        # Check if we have enough variety for co-occurrence based generation
        has_variety = length_stats.count > 1

        positions = list(range(length))
        result = [""] * length
        retries = 0

        # Start with a random position
        start_pos = self._random_choice(positions)
        positions.remove(start_pos)

        required_type = CharType(pattern[start_pos])
        start_char = self._get_char_of_type(start_pos, required_type, length_stats)

        if not start_char:
            return None

        result[start_pos] = start_char

        # Fill remaining positions
        while positions and retries < self.max_retries:
            pos = self._random_choice(positions)
            required_type = CharType(pattern[pos])

            # Only use co-occurrence filtering if we have variety
            compatible = []
            if has_variety:
                compatible = self._find_compatible_typed_chars(
                    result, pos, required_type, length_stats, cooc
                )

            if compatible and len(compatible) > 1:
                # Weight by position frequency
                pos_counts = length_stats.positions[pos].char_counts
                weighted = {c: pos_counts.get(c, 1) for c in compatible}
                char = self._weighted_choice(weighted)
                result[pos] = char
                positions.remove(pos)
                retries = 0
            else:
                # Low variety - get any char of the required type
                char = self._get_char_of_type(pos, required_type, length_stats)
                if char:
                    result[pos] = char
                    positions.remove(pos)
                    retries = 0
                else:
                    retries += 1

        if positions:
            # Couldn't fill all positions, fall back to global charset
            for pos in positions:
                required_type = CharType(pattern[pos])
                char = self._get_char_of_type(pos, required_type, length_stats)
                if char:
                    result[pos] = char
                else:
                    return None

        return "".join(result)

    def _generate_from_pattern_global(self, pattern: str) -> Optional[str]:
        """Generate a string using only global charset (for unknown lengths)."""
        result = []
        for char_code in pattern:
            required_type = CharType(char_code)
            chars_of_type = list(self.analysis.get_charset_by_type(required_type))
            if chars_of_type:
                result.append(self._random_choice(chars_of_type))
            else:
                return None
        return "".join(result)

    def _get_char_of_type(
        self,
        pos: int,
        char_type: CharType,
        length_stats,
    ) -> Optional[str]:
        """Get a character of the specified type at the given position."""
        if pos not in length_stats.positions:
            # Fallback to global charset
            chars_of_type = list(self.analysis.get_charset_by_type(char_type))
            if chars_of_type:
                return self._random_choice(chars_of_type)
            return None

        pos_stats = length_stats.positions[pos]
        chars_of_type = pos_stats.get_chars_by_type(char_type)

        if not chars_of_type:
            # Fallback to global charset
            chars_of_type = list(self.analysis.get_charset_by_type(char_type))

        if chars_of_type:
            # Weight by frequency
            weighted = {c: pos_stats.char_counts.get(c, 1) for c in chars_of_type}
            return self._weighted_choice(weighted)

        return None

    def _find_compatible_typed_chars(
        self,
        current: list,
        target_pos: int,
        required_type: CharType,
        length_stats,
        cooc: dict,
    ) -> List[str]:
        """
        Find chars of required type compatible with placed chars.
        """
        if target_pos not in length_stats.positions:
            return []

        # Start with all chars of the required type at this position
        pos_stats = length_stats.positions[target_pos]
        candidates = set(pos_stats.get_chars_by_type(required_type))

        if not candidates:
            return []

        # Filter by co-occurrence
        for pos, char in enumerate(current):
            if not char:
                continue

            if char in cooc and pos in cooc[char] and target_pos in cooc[char][pos]:
                seen_at_target = cooc[char][pos][target_pos]
                candidates &= seen_at_target

            if not candidates:
                break

        return list(candidates)

    def generate_from_explicit_pattern(self, pattern: str) -> Optional[str]:
        """
        Generate a string from an explicitly provided pattern.

        Args:
            pattern: String of CharType values like "UllnnU@"

        Returns:
            Generated string or None
        """
        return self._generate_from_pattern(pattern)

    def get_available_patterns(self, length: Optional[int] = None) -> List[tuple]:
        """
        Get available patterns with their frequencies.

        Args:
            length: If provided, only return patterns of this length

        Returns:
            List of (pattern, count) tuples sorted by count
        """
        patterns = []

        if length is not None:
            if length in self.analysis.length_stats:
                patterns.extend(
                    self.analysis.length_stats[length].patterns.most_common()
                )
        else:
            for length_stats in self.analysis.length_stats.values():
                patterns.extend(length_stats.patterns.most_common())

        return sorted(patterns, key=lambda x: x[1], reverse=True)
