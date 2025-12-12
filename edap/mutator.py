"""
Rule-based mutations - apply transformations like hashcat rules.
"""

import secrets
import random
from typing import List, Optional, Callable, Iterator


class Mutator:
    """
    Applies rule-based mutations to strings.

    Supports hashcat-style rules and custom transformations.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the mutator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            self._rng = random.Random(seed)
            self._use_secure = False
        else:
            self._rng = None
            self._use_secure = True

        # Built-in rule functions
        self._rules: dict[str, Callable[[str], str]] = {
            # Case rules
            "lowercase": str.lower,
            "uppercase": str.upper,
            "capitalize": str.capitalize,
            "toggle_case": self._toggle_case,
            "swapcase": str.swapcase,

            # Reverse/rotate
            "reverse": lambda s: s[::-1],
            "rotate_left": lambda s: s[1:] + s[0] if s else s,
            "rotate_right": lambda s: s[-1] + s[:-1] if s else s,

            # Duplicate
            "duplicate": lambda s: s + s,
            "duplicate_first": lambda s: s[0] + s if s else s,
            "duplicate_last": lambda s: s + s[-1] if s else s,
            "duplicate_all": lambda s: "".join(c + c for c in s),

            # Remove
            "remove_first": lambda s: s[1:] if s else s,
            "remove_last": lambda s: s[:-1] if s else s,

            # Leetspeak
            "leetspeak": self._leetspeak,
            "leetspeak_full": self._leetspeak_full,

            # Append common suffixes
            "append_1": lambda s: s + "1",
            "append_123": lambda s: s + "123",
            "append_2024": lambda s: s + "2024",
            "append_2025": lambda s: s + "2025",
            "append_!": lambda s: s + "!",
            "append_@": lambda s: s + "@",

            # Prepend common prefixes
            "prepend_1": lambda s: "1" + s,
            "prepend_@": lambda s: "@" + s,
            "prepend_the": lambda s: "the" + s,

            # Truncate
            "truncate_3": lambda s: s[:3],
            "truncate_4": lambda s: s[:4],
            "truncate_5": lambda s: s[:5],
            "truncate_6": lambda s: s[:6],
            "truncate_8": lambda s: s[:8],
        }

    def _random_choice(self, seq: list):
        """Random choice helper."""
        if self._use_secure:
            return secrets.choice(seq)
        return self._rng.choice(seq)

    def _toggle_case(self, s: str) -> str:
        """Toggle case of first character."""
        if not s:
            return s
        first = s[0].upper() if s[0].islower() else s[0].lower()
        return first + s[1:]

    def _leetspeak(self, s: str) -> str:
        """Convert to basic leetspeak."""
        leet_map = {
            'a': '4', 'A': '4',
            'e': '3', 'E': '3',
            'i': '1', 'I': '1',
            'o': '0', 'O': '0',
            's': '$', 'S': '$',
        }
        return "".join(leet_map.get(c, c) for c in s)

    def _leetspeak_full(self, s: str) -> str:
        """Convert to full leetspeak."""
        leet_map = {
            'a': '4', 'A': '4',
            'b': '8', 'B': '8',
            'e': '3', 'E': '3',
            'g': '9', 'G': '9',
            'i': '1', 'I': '1',
            'l': '1', 'L': '1',
            'o': '0', 'O': '0',
            's': '$', 'S': '$',
            't': '7', 'T': '7',
            'z': '2', 'Z': '2',
        }
        return "".join(leet_map.get(c, c) for c in s)

    def list_rules(self) -> List[str]:
        """Get list of available rule names."""
        return sorted(self._rules.keys())

    def add_rule(self, name: str, func: Callable[[str], str]) -> None:
        """
        Add a custom rule.

        Args:
            name: Rule name
            func: Function that takes a string and returns transformed string
        """
        self._rules[name] = func

    def apply_rule(self, word: str, rule: str) -> str:
        """
        Apply a single rule to a word.

        Args:
            word: Input string
            rule: Rule name

        Returns:
            Transformed string
        """
        if rule not in self._rules:
            raise ValueError(f"Unknown rule: {rule}")
        return self._rules[rule](word)

    def apply_rules(self, word: str, rules: List[str]) -> str:
        """
        Apply multiple rules in sequence.

        Args:
            word: Input string
            rules: List of rule names to apply in order

        Returns:
            Transformed string
        """
        result = word
        for rule in rules:
            result = self.apply_rule(result, rule)
        return result

    def mutate(
        self,
        word: str,
        rules: Optional[List[str]] = None,
        num_mutations: int = 1,
    ) -> str:
        """
        Apply random mutations to a word.

        Args:
            word: Input string
            rules: List of rules to choose from (None = all rules)
            num_mutations: Number of random mutations to apply

        Returns:
            Mutated string
        """
        available = rules or list(self._rules.keys())
        result = word

        for _ in range(num_mutations):
            rule = self._random_choice(available)
            result = self.apply_rule(result, rule)

        return result

    def mutate_many(
        self,
        words: List[str],
        rules: Optional[List[str]] = None,
        num_mutations: int = 1,
    ) -> List[str]:
        """
        Apply mutations to multiple words.

        Args:
            words: Input strings
            rules: List of rules to choose from
            num_mutations: Number of mutations per word

        Returns:
            List of mutated strings
        """
        return [self.mutate(w, rules, num_mutations) for w in words]

    def expand(
        self,
        word: str,
        rules: Optional[List[str]] = None,
    ) -> Iterator[str]:
        """
        Generate all single-rule mutations of a word.

        Args:
            word: Input string
            rules: Rules to apply (None = all rules)

        Yields:
            Mutated strings
        """
        available = rules or list(self._rules.keys())

        yield word  # Original

        for rule in available:
            mutated = self.apply_rule(word, rule)
            if mutated != word:
                yield mutated

    def expand_many(
        self,
        words: List[str],
        rules: Optional[List[str]] = None,
        include_original: bool = True,
    ) -> Iterator[str]:
        """
        Generate all mutations for multiple words.

        Args:
            words: Input strings
            rules: Rules to apply
            include_original: Include original words in output

        Yields:
            Mutated strings (deduplicated)
        """
        seen = set()

        for word in words:
            if include_original and word not in seen:
                seen.add(word)
                yield word

            for mutated in self.expand(word, rules):
                if mutated not in seen:
                    seen.add(mutated)
                    yield mutated


# Common rule presets
RULE_PRESETS = {
    "basic": [
        "lowercase",
        "uppercase",
        "capitalize",
        "append_1",
        "append_123",
    ],
    "case": [
        "lowercase",
        "uppercase",
        "capitalize",
        "toggle_case",
        "swapcase",
    ],
    "leet": [
        "leetspeak",
        "leetspeak_full",
    ],
    "append": [
        "append_1",
        "append_123",
        "append_2024",
        "append_2025",
        "append_!",
        "append_@",
    ],
    "common": [
        "lowercase",
        "uppercase",
        "capitalize",
        "leetspeak",
        "append_1",
        "append_123",
        "append_!",
        "reverse",
    ],
}
