"""
Markov chain generator - generates strings based on n-gram transitions.
"""

from collections import defaultdict
from typing import Optional, Dict, List

from edap.generators.base import BaseGenerator
from edap.models import AnalysisResult


class MarkovGenerator(BaseGenerator):
    """
    Generates strings using Markov chain transitions.

    This generator learns n-gram transitions from the input data
    and generates new strings by following these transitions.
    For example, if "pa" is often followed by "ss", the generator
    will tend to produce "pass" sequences.
    """

    # Special tokens for start/end of word
    START = "\x00"
    END = "\x01"

    def __init__(
        self,
        analysis: AnalysisResult,
        seed: Optional[int] = None,
        exclude_original: bool = True,
        order: int = 2,
    ):
        """
        Initialize the Markov generator.

        Args:
            analysis: Analysis result from PatternAnalyzer
            seed: Random seed for reproducibility
            exclude_original: If True, don't generate words from original set
            order: Markov chain order (n-gram size). Higher = more similar to input.
                   1 = bigram (char pairs), 2 = trigram, etc.
        """
        super().__init__(analysis, seed, exclude_original)
        self.order = order
        self._transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._build_transitions()

    def _build_transitions(self) -> None:
        """Build transition probabilities from the analysis data."""
        # We need access to original words to build n-gram transitions
        # Use the words stored during analysis
        for length, length_stats in self.analysis.length_stats.items():
            # Reconstruct possible words from position data
            # This is an approximation - ideally we'd have original words
            pass

        # For now, build from co-occurrence data which gives us char pairs
        # This creates a 1st order Markov chain
        cooc = self.analysis.cooccurrence

        for char, pos_data in cooc.items():
            for from_pos, to_pos_data in pos_data.items():
                for to_pos, next_chars in to_pos_data.items():
                    # If positions are adjacent, record transition
                    if to_pos == from_pos + 1:
                        for next_char in next_chars:
                            self._transitions[char][next_char] += 1

        # Add start transitions from position 0 characters
        for length, length_stats in self.analysis.length_stats.items():
            if 0 in length_stats.positions:
                for char, count in length_stats.positions[0].char_counts.items():
                    self._transitions[self.START][char] += count

        # Add end transitions from last position characters
        for length, length_stats in self.analysis.length_stats.items():
            last_pos = length - 1
            if last_pos in length_stats.positions:
                for char, count in length_stats.positions[last_pos].char_counts.items():
                    self._transitions[char][self.END] += count

    def train_on_words(self, words: List[str]) -> None:
        """
        Train the Markov chain on a list of words.

        This provides better transitions than using just the analysis data.

        Args:
            words: List of words to train on
        """
        self._transitions.clear()

        for word in words:
            # Add start token
            padded = self.START * self.order + word + self.END

            # Build n-gram transitions
            for i in range(len(padded) - self.order):
                context = padded[i:i + self.order]
                next_char = padded[i + self.order]
                self._transitions[context][next_char] += 1

    def generate_one(self) -> Optional[str]:
        """Generate a single string using Markov chain transitions."""
        if not self._transitions:
            return None

        # Start with the start token(s)
        current = self.START * self.order
        result = []

        # Maximum length to prevent infinite loops
        max_length = max(self.analysis.length_stats.keys()) * 2 if self.analysis.length_stats else 20

        while len(result) < max_length:
            # Get possible next characters
            if current not in self._transitions:
                # No transitions from current state, try shorter context
                for i in range(1, len(current)):
                    shorter = current[i:]
                    if shorter in self._transitions:
                        current = shorter
                        break
                else:
                    # Fall back to random char from charset
                    if self.analysis.charset:
                        next_char = self._random_choice(list(self.analysis.charset))
                        result.append(next_char)
                        current = (current + next_char)[-self.order:]
                        continue
                    else:
                        break

            transitions = self._transitions.get(current, {})
            if not transitions:
                break

            # Choose next character weighted by frequency
            next_char = self._weighted_choice(dict(transitions))

            if next_char == self.END:
                break

            result.append(next_char)

            # Update context
            current = (current + next_char)[-self.order:]

        return "".join(result) if result else None

    def generate_one_with_length(self, target_length: int) -> Optional[str]:
        """
        Generate a string of approximately the target length.

        Args:
            target_length: Desired string length

        Returns:
            Generated string or None
        """
        # Try multiple times to get close to target length
        best = None
        best_diff = float('inf')

        for _ in range(50):
            word = self.generate_one()
            if word:
                diff = abs(len(word) - target_length)
                if diff < best_diff:
                    best = word
                    best_diff = diff
                if diff == 0:
                    break

        return best
