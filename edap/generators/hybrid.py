"""
Hybrid generator - combines multiple generation strategies.
"""

from typing import Optional, List, Type

from edap.generators.base import BaseGenerator
from edap.models import AnalysisResult


class HybridGenerator(BaseGenerator):
    """
    Combines multiple generators with configurable weights.

    This allows mixing different generation strategies, for example:
    - 50% Smart + 50% Pattern for balanced output
    - 70% Markov + 30% Random for variety with structure
    """

    def __init__(
        self,
        analysis: AnalysisResult,
        generators: List[tuple],  # List of (GeneratorClass, weight, kwargs)
        seed: Optional[int] = None,
        exclude_original: bool = True,
    ):
        """
        Initialize the hybrid generator.

        Args:
            analysis: Analysis result from PatternAnalyzer
            generators: List of (GeneratorClass, weight, kwargs) tuples
                        e.g., [(SmartGenerator, 0.6, {}), (RandomGenerator, 0.4, {})]
            seed: Random seed for reproducibility
            exclude_original: If True, don't generate words from original set
        """
        super().__init__(analysis, seed, exclude_original)

        self._generators: List[BaseGenerator] = []
        self._weights: List[float] = []

        for gen_class, weight, kwargs in generators:
            gen = gen_class(
                analysis,
                seed=seed,
                exclude_original=exclude_original,
                **kwargs
            )
            self._generators.append(gen)
            self._weights.append(weight)

        # Normalize weights
        total = sum(self._weights)
        if total > 0:
            self._weights = [w / total for w in self._weights]

    def set_original_words(self, words: set) -> None:
        """Set original words for all sub-generators."""
        super().set_original_words(words)
        for gen in self._generators:
            gen.set_original_words(words)

    def generate_one(self) -> Optional[str]:
        """Generate using a randomly selected generator based on weights."""
        if not self._generators:
            return None

        # Select generator based on weights
        gen = self._select_generator()
        return gen.generate_one()

    def _select_generator(self) -> BaseGenerator:
        """Select a generator based on weights."""
        if self._use_secure_random:
            import secrets
            r = secrets.randbelow(1000) / 1000
        else:
            r = self._rng.random()

        cumulative = 0
        for gen, weight in zip(self._generators, self._weights):
            cumulative += weight
            if r < cumulative:
                return gen

        return self._generators[-1]

    def generate_blended(self) -> Optional[str]:
        """
        Generate by blending output from multiple generators.

        Takes partial output from each generator and combines them.
        """
        if not self._generators or len(self._generators) < 2:
            return self.generate_one()

        # Get candidates from each generator
        candidates = []
        for gen in self._generators:
            word = gen.generate_one()
            if word:
                candidates.append(word)

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Blend by taking parts from different candidates
        # Use the shortest length
        min_len = min(len(w) for w in candidates)
        if min_len == 0:
            return self._random_choice(candidates)

        result = []
        for i in range(min_len):
            # Pick character from random candidate at this position
            candidate = self._random_choice(candidates)
            result.append(candidate[i])

        return "".join(result)


def create_hybrid_generator(
    analysis: AnalysisResult,
    mode: str = "balanced",
    seed: Optional[int] = None,
    exclude_original: bool = True,
) -> HybridGenerator:
    """
    Factory function to create common hybrid configurations.

    Args:
        analysis: Analysis result
        mode: Preset mode - "balanced", "strict", "creative", "markov_smart"
        seed: Random seed
        exclude_original: Exclude original words

    Returns:
        Configured HybridGenerator
    """
    from edap.generators.smart import SmartGenerator
    from edap.generators.random_gen import RandomGenerator
    from edap.generators.pattern import PatternGenerator

    presets = {
        "balanced": [
            (SmartGenerator, 0.5, {}),
            (PatternGenerator, 0.3, {}),
            (RandomGenerator, 0.2, {}),
        ],
        "strict": [
            (PatternGenerator, 0.7, {}),
            (SmartGenerator, 0.3, {}),
        ],
        "creative": [
            (RandomGenerator, 0.5, {}),
            (SmartGenerator, 0.3, {}),
            (PatternGenerator, 0.2, {}),
        ],
    }

    generators = presets.get(mode, presets["balanced"])

    return HybridGenerator(
        analysis,
        generators=generators,
        seed=seed,
        exclude_original=exclude_original,
    )
