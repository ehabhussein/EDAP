"""
Regex pattern builder for EDAP.
Generates regex patterns from analysis results.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from edap.models import AnalysisResult, CharType, LengthStats


class RegexBuilder:
    """
    Builds regex patterns from analysis results.

    Can generate patterns at different levels of specificity:
    - Generic: [A-Z][a-z]+[0-9]{2}
    - Specific: [ABCD][aeiou][lmn]+[0-9]{2}
    - Exact: Based on actual character sets observed
    """

    def __init__(self, analysis: AnalysisResult):
        """
        Initialize regex builder.

        Args:
            analysis: Analysis result from PatternAnalyzer
        """
        self.analysis = analysis

    def build_generic_pattern(self, length: int) -> Optional[str]:
        """
        Build a generic regex pattern for a given length.

        Uses standard character classes like [A-Z], [a-z], [0-9].
        """
        if length not in self.analysis.length_stats:
            return None

        length_stats = self.analysis.length_stats[length]

        # Get most common type pattern
        patterns = length_stats.get_common_patterns(1)
        if not patterns:
            return None

        type_pattern = patterns[0][0]  # e.g., "UllnnU"
        return self._type_pattern_to_generic_regex(type_pattern)

    def _type_pattern_to_generic_regex(self, type_pattern: str) -> str:
        """Convert type pattern to generic regex."""
        regex_parts = []
        i = 0

        while i < len(type_pattern):
            char_type = type_pattern[i]
            count = 1

            # Count consecutive same types
            while i + count < len(type_pattern) and type_pattern[i + count] == char_type:
                count += 1

            # Convert to regex
            class_str = self._type_to_generic_class(char_type)

            if count == 1:
                regex_parts.append(class_str)
            else:
                regex_parts.append(f'{class_str}{{{count}}}')

            i += count

        return ''.join(regex_parts)

    def _type_to_generic_class(self, char_type: str) -> str:
        """Convert single char type to generic regex class."""
        type_map = {
            'U': '[A-Z]',
            'l': '[a-z]',
            'n': '[0-9]',
            '@': r'[^a-zA-Z0-9]',
        }
        return type_map.get(char_type, '.')

    def build_specific_pattern(
        self,
        length: int,
        min_char_frequency: int = 2,
    ) -> Optional[str]:
        """
        Build a specific regex pattern using observed characters.

        Args:
            length: Word length
            min_char_frequency: Minimum times a char must appear to be included
        """
        if length not in self.analysis.length_stats:
            return None

        length_stats = self.analysis.length_stats[length]
        regex_parts = []

        for pos in range(length):
            if pos not in length_stats.positions:
                regex_parts.append('.')
                continue

            pos_stats = length_stats.positions[pos]

            # Get chars that meet frequency threshold
            chars = [
                c for c, count in pos_stats.char_counts.items()
                if count >= min_char_frequency
            ]

            if not chars:
                # Fall back to all chars at position
                chars = list(pos_stats.char_counts.keys())

            regex_parts.append(self._chars_to_class(chars))

        return ''.join(regex_parts)

    def _chars_to_class(self, chars: List[str]) -> str:
        """Convert list of characters to regex character class."""
        if not chars:
            return '.'

        if len(chars) == 1:
            char = chars[0]
            if char in r'\.^$*+?{}[]|()':
                return f'\\{char}'
            return char

        # Sort and escape special chars
        escaped = []
        for c in sorted(set(chars)):
            if c in r'\.^$*+?{}[]|()-':
                escaped.append(f'\\{c}')
            else:
                escaped.append(c)

        # Try to create ranges for efficiency
        class_content = self._optimize_char_class(''.join(escaped))
        return f'[{class_content}]'

    def _optimize_char_class(self, chars: str) -> str:
        """Optimize character class by finding ranges."""
        # This is a simplified version - could be more sophisticated
        # For now, just return the chars as-is
        return chars

    def build_all_patterns(
        self,
        specificity: str = 'specific',
        min_frequency: int = 1,
    ) -> Dict[int, List[str]]:
        """
        Build patterns for all observed lengths.

        Args:
            specificity: 'generic', 'specific', or 'exact'
            min_frequency: Minimum pattern frequency to include

        Returns:
            Dict mapping length to list of regex patterns
        """
        patterns: Dict[int, List[str]] = {}

        for length, length_stats in self.analysis.length_stats.items():
            length_patterns = []

            for type_pattern, count in length_stats.patterns.items():
                if count < min_frequency:
                    continue

                if specificity == 'generic':
                    regex = self._type_pattern_to_generic_regex(type_pattern)
                elif specificity == 'exact':
                    regex = self._build_exact_pattern(type_pattern, length_stats)
                else:  # specific
                    regex = self._build_specific_from_type(type_pattern, length_stats)

                if regex:
                    length_patterns.append(regex)

            if length_patterns:
                patterns[length] = length_patterns

        return patterns

    def _build_specific_from_type(
        self,
        type_pattern: str,
        length_stats: LengthStats,
    ) -> str:
        """Build specific pattern following type pattern."""
        regex_parts = []

        for pos, char_type in enumerate(type_pattern):
            ct = CharType(char_type)

            if pos in length_stats.positions:
                pos_stats = length_stats.positions[pos]
                chars = pos_stats.get_chars_by_type(ct)

                if chars:
                    regex_parts.append(self._chars_to_class(chars))
                else:
                    regex_parts.append(self._type_to_generic_class(char_type))
            else:
                regex_parts.append(self._type_to_generic_class(char_type))

        return ''.join(regex_parts)

    def _build_exact_pattern(
        self,
        type_pattern: str,
        length_stats: LengthStats,
    ) -> str:
        """Build exact pattern with all observed chars at each position."""
        regex_parts = []

        for pos, char_type in enumerate(type_pattern):
            if pos in length_stats.positions:
                pos_stats = length_stats.positions[pos]
                # Use only chars of this type that were actually observed
                ct = CharType(char_type)
                chars = pos_stats.get_chars_by_type(ct)

                if chars:
                    regex_parts.append(self._chars_to_class(chars))
                else:
                    # Use all chars at position
                    all_chars = list(pos_stats.char_counts.keys())
                    regex_parts.append(self._chars_to_class(all_chars))
            else:
                regex_parts.append('.')

        return ''.join(regex_parts)

    def validate_pattern(self, pattern: str, sample_size: int = 100) -> Tuple[int, int]:
        """
        Validate a pattern against original words.

        Args:
            pattern: Regex pattern to validate
            sample_size: Number of original words to test

        Returns:
            Tuple of (matches, total_tested)
        """
        try:
            compiled = re.compile(f'^{pattern}$')
        except re.error:
            return 0, 0

        matches = 0
        tested = 0

        for length_stats in self.analysis.length_stats.values():
            for pattern_str in length_stats.patterns.keys():
                if tested >= sample_size:
                    break

                # We don't have original words stored, so this is approximate
                tested += 1

        # This is a placeholder - in practice you'd test against actual words
        return matches, tested

    def get_coverage_report(self, patterns: Dict[int, List[str]]) -> str:
        """Generate a report on pattern coverage."""
        lines = ["Pattern Coverage Report", "=" * 50, ""]

        for length in sorted(patterns.keys()):
            length_patterns = patterns[length]
            length_stats = self.analysis.length_stats[length]

            lines.append(f"Length {length}: {length_stats.count} words")
            lines.append(f"  Patterns generated: {len(length_patterns)}")

            for i, pattern in enumerate(length_patterns[:5]):  # Show top 5
                lines.append(f"    {i + 1}. {pattern}")

            if len(length_patterns) > 5:
                lines.append(f"    ... and {len(length_patterns) - 5} more")

            lines.append("")

        return '\n'.join(lines)

    def export_patterns(
        self,
        patterns: Dict[int, List[str]],
        format: str = 'text',
    ) -> str:
        """
        Export patterns in various formats.

        Args:
            patterns: Dict of patterns from build_all_patterns
            format: 'text', 'json', or 'grep'
        """
        if format == 'json':
            import json
            return json.dumps(patterns, indent=2)

        elif format == 'grep':
            # Format suitable for grep -E
            all_patterns = []
            for length_patterns in patterns.values():
                all_patterns.extend(length_patterns)
            return '|'.join(f'({p})' for p in all_patterns)

        else:  # text
            lines = []
            for length in sorted(patterns.keys()):
                lines.append(f"# Length {length}")
                for pattern in patterns[length]:
                    lines.append(pattern)
                lines.append("")
            return '\n'.join(lines)
