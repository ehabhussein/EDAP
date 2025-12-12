"""
Random generator - generates strings based on charset and length distribution.
"""

from typing import Optional

from edap.generators.base import BaseGenerator
from edap.models import AnalysisResult


class RandomGenerator(BaseGenerator):
    """
    Generates random strings based on observed charset and length distribution.

    This is the fastest but least strict generator - it only ensures:
    - Characters come from the observed charset
    - Lengths follow the observed distribution
    - Characters at each position come from chars seen at that position
    """

    def __init__(
        self,
        analysis: AnalysisResult,
        seed: Optional[int] = None,
        exclude_original: bool = True,
        use_position_charset: bool = True,
    ):
        """
        Initialize the random generator.

        Args:
            analysis: Analysis result from PatternAnalyzer
            seed: Random seed for reproducibility
            exclude_original: If True, don't generate words from original set
            use_position_charset: If True, only use chars seen at each position
        """
        super().__init__(analysis, seed, exclude_original)
        self.use_position_charset = use_position_charset

    def generate_one(self) -> Optional[str]:
        """Generate a single random string."""
        # Choose length based on distribution
        length = self._choose_length()

        if length not in self.analysis.length_stats:
            return None

        length_stats = self.analysis.length_stats[length]
        chars = []

        # Check if we have enough variety (more than 1 word of this length)
        has_variety = length_stats.count > 1

        for pos in range(length):
            if self.use_position_charset and has_variety and pos in length_stats.positions:
                # Use only characters seen at this position
                pos_stats = length_stats.positions[pos]
                if len(pos_stats.char_counts) > 1:
                    char = self._random_choice(list(pos_stats.char_counts.keys()))
                else:
                    # Only 1 char seen at this position, use global charset for variety
                    char = self._random_choice(list(self.analysis.charset))
            else:
                # Use global charset
                char = self._random_choice(list(self.analysis.charset))

            chars.append(char)

        return "".join(chars)

    def generate_one_weighted(self) -> Optional[str]:
        """
        Generate a string with weighted character selection.

        More common characters at each position are more likely to be chosen.
        """
        length = self._choose_length()

        if length not in self.analysis.length_stats:
            return None

        length_stats = self.analysis.length_stats[length]
        chars = []

        for pos in range(length):
            if pos in length_stats.positions:
                pos_stats = length_stats.positions[pos]
                if pos_stats.char_counts:
                    char = self._weighted_choice(dict(pos_stats.char_counts))
                else:
                    char = self._random_choice(list(self.analysis.charset))
            else:
                char = self._random_choice(list(self.analysis.charset))

            chars.append(char)

        return "".join(chars)
