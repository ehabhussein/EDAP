"""
Smart generator - uses co-occurrence patterns and position weights.
"""

from typing import Optional, Set

from edap.generators.base import BaseGenerator
from edap.models import AnalysisResult


class SmartGenerator(BaseGenerator):
    """
    Generates strings using character co-occurrence and position weights.

    This generator is "smart" because it considers:
    - Which characters tend to appear together in words
    - Position-specific character frequencies
    - Co-occurrence relationships between positions
    """

    def __init__(
        self,
        analysis: AnalysisResult,
        seed: Optional[int] = None,
        exclude_original: bool = True,
        max_retries_per_position: int = 50,
    ):
        """
        Initialize the smart generator.

        Args:
            analysis: Analysis result from PatternAnalyzer
            seed: Random seed for reproducibility
            exclude_original: If True, don't generate words from original set
            max_retries_per_position: Max retries when finding compatible char
        """
        super().__init__(analysis, seed, exclude_original)
        self.max_retries = max_retries_per_position

    def generate_one(self) -> Optional[str]:
        """
        Generate a single string using smart selection.

        Algorithm:
        1. Choose a length based on distribution
        2. Pick a random starting position and character
        3. For remaining positions, pick characters that:
           - Were seen at that position
           - Are compatible with already-chosen characters
           - Weighted by frequency
        """
        length = self._choose_length()

        if length not in self.analysis.length_stats:
            return None

        length_stats = self.analysis.length_stats[length]
        positions = list(range(length))

        # Check if we have enough variety to do smart generation
        # If only 1 word of this length, fall back to global charset
        has_variety = length_stats.count > 1

        # Result array
        result = [""] * length

        # Start with a random position
        start_pos = self._random_choice(positions)
        positions.remove(start_pos)

        # Pick initial character weighted by frequency
        if has_variety and start_pos in length_stats.positions:
            pos_stats = length_stats.positions[start_pos]
            if len(pos_stats.char_counts) > 1:
                start_char = self._weighted_choice(dict(pos_stats.char_counts))
            else:
                # Only 1 char at this position, use global charset
                start_char = self._random_choice(list(self.analysis.charset))
        else:
            start_char = self._random_choice(list(self.analysis.charset))

        result[start_pos] = start_char

        # Fill remaining positions
        while positions:
            pos = self._random_choice(positions)
            positions.remove(pos)

            # Find compatible characters (only if we have variety)
            compatible = set()
            if has_variety:
                compatible = self._find_compatible_chars(result, pos, length_stats)

            if compatible and len(compatible) > 1:
                # Weight by position frequency
                pos_counts = length_stats.positions[pos].char_counts
                weighted_compatible = {
                    c: pos_counts.get(c, 1) for c in compatible
                }
                char = self._weighted_choice(weighted_compatible)
            elif has_variety and pos in length_stats.positions and len(length_stats.positions[pos].char_counts) > 1:
                # Fallback: use any char seen at this position (if variety exists)
                char = self._weighted_choice(
                    dict(length_stats.positions[pos].char_counts)
                )
            else:
                # No variety at this position, use global charset
                char = self._random_choice(list(self.analysis.charset))

            result[pos] = char

        return "".join(result)

    def _find_compatible_chars(
        self,
        current: list,
        target_pos: int,
        length_stats,
    ) -> Set[str]:
        """
        Find characters compatible with already-placed characters.

        A character is compatible if it was seen in the same word
        with all currently placed characters at their positions.
        """
        cooc = self.analysis.cooccurrence

        # Get chars that can go at target_pos
        if target_pos not in length_stats.positions:
            return set()

        candidates = set(length_stats.positions[target_pos].char_counts.keys())

        # Filter by co-occurrence with each placed character
        for pos, char in enumerate(current):
            if not char:
                continue

            # What chars did we see at target_pos when char was at pos?
            if char in cooc and pos in cooc[char] and target_pos in cooc[char][pos]:
                seen_at_target = cooc[char][pos][target_pos]
                candidates &= seen_at_target
            else:
                # No co-occurrence data, don't filter
                pass

        return candidates

    def generate_one_strict(self) -> Optional[str]:
        """
        Generate with stricter co-occurrence requirements.

        Will return None more often but produces higher-quality matches.
        """
        length = self._choose_length()

        if length not in self.analysis.length_stats:
            return None

        length_stats = self.analysis.length_stats[length]
        positions = list(range(length))

        result = [""] * length
        retries = 0

        # Start with a random position
        start_pos = self._random_choice(positions)
        positions.remove(start_pos)

        if start_pos in length_stats.positions:
            start_char = self._weighted_choice(
                dict(length_stats.positions[start_pos].char_counts)
            )
        else:
            return None

        result[start_pos] = start_char

        while positions and retries < self.max_retries * length:
            pos = self._random_choice(positions)

            compatible = self._find_compatible_chars(result, pos, length_stats)

            if not compatible:
                retries += 1
                continue

            pos_counts = length_stats.positions[pos].char_counts
            weighted = {c: pos_counts.get(c, 1) for c in compatible}
            char = self._weighted_choice(weighted)

            result[pos] = char
            positions.remove(pos)
            retries = 0

        if positions:
            # Couldn't fill all positions
            return None

        return "".join(result)
