"""
Regex-based generator - generates strings matching a user-provided regex pattern.
"""

import re
import string
from typing import Optional, List, Set, Dict

from edap.generators.base import BaseGenerator
from edap.models import AnalysisResult, CharType


class RegexGenerator(BaseGenerator):
    """
    Generates strings that match a user-provided regular expression.

    Supports common regex patterns and generates strings that:
    1. Match the provided regex
    2. Optionally follow the learned character distributions
    """

    # Character class mappings
    CHAR_CLASSES = {
        r'\d': string.digits,
        r'\w': string.ascii_letters + string.digits + '_',
        r'\s': ' \t\n\r',
        r'\W': string.punctuation + ' ',
        r'\D': string.ascii_letters + string.punctuation + ' ',
        r'\S': string.ascii_letters + string.digits + string.punctuation,
        '.': string.printable.replace('\n', '').replace('\r', ''),
    }

    def __init__(
        self,
        analysis: AnalysisResult,
        pattern: str,
        seed: Optional[int] = None,
        exclude_original: bool = True,
        use_learned_charset: bool = True,
    ):
        """
        Initialize the regex generator.

        Args:
            analysis: Analysis result from PatternAnalyzer
            pattern: Regular expression pattern to match
            seed: Random seed for reproducibility
            exclude_original: If True, don't generate words from original set
            use_learned_charset: If True, prefer chars from learned charset
        """
        super().__init__(analysis, seed, exclude_original)
        self.pattern = pattern
        self.use_learned_charset = use_learned_charset
        self._compiled = re.compile(pattern)
        self._parsed = self._parse_pattern(pattern)

    def _parse_pattern(self, pattern: str) -> List[dict]:
        """
        Parse regex pattern into generation instructions.

        This is a simplified parser that handles common patterns.
        For complex regexes, falls back to random generation + validation.
        """
        instructions = []
        i = 0

        while i < len(pattern):
            char = pattern[i]

            if char == '^':
                # Start anchor - ignore for generation
                i += 1
                continue
            elif char == '$':
                # End anchor - ignore for generation
                i += 1
                continue
            elif char == '\\':
                # Escaped character or character class
                if i + 1 < len(pattern):
                    next_char = pattern[i + 1]
                    escape_seq = '\\' + next_char

                    if escape_seq in self.CHAR_CLASSES:
                        instructions.append({
                            'type': 'class',
                            'chars': self.CHAR_CLASSES[escape_seq],
                            'quantifier': self._get_quantifier(pattern, i + 2),
                        })
                        i += 2 + len(instructions[-1]['quantifier'].get('raw', ''))
                    else:
                        # Literal escaped character
                        instructions.append({
                            'type': 'literal',
                            'char': next_char,
                        })
                        i += 2
                else:
                    i += 1
            elif char == '[':
                # Character class
                end = pattern.find(']', i)
                if end == -1:
                    raise ValueError(f"Unclosed character class at position {i}")

                class_content = pattern[i + 1:end]
                chars = self._expand_char_class(class_content)
                instructions.append({
                    'type': 'class',
                    'chars': chars,
                    'quantifier': self._get_quantifier(pattern, end + 1),
                })
                i = end + 1 + len(instructions[-1]['quantifier'].get('raw', ''))
            elif char == '.':
                instructions.append({
                    'type': 'class',
                    'chars': self.CHAR_CLASSES['.'],
                    'quantifier': self._get_quantifier(pattern, i + 1),
                })
                i += 1 + len(instructions[-1]['quantifier'].get('raw', ''))
            elif char in '?*+{':
                # Quantifier without preceding element - skip
                i += 1
            elif char == '(':
                # Group - handle alternation inside groups
                depth = 1
                end = i + 1
                while end < len(pattern) and depth > 0:
                    if pattern[end] == '(' and (end == 0 or pattern[end-1] != '\\'):
                        depth += 1
                    elif pattern[end] == ')' and (end == 0 or pattern[end-1] != '\\'):
                        depth -= 1
                    end += 1

                group_content = pattern[i + 1:end - 1]

                # Check for alternation in group
                if '|' in group_content:
                    instructions.append({
                        'type': 'alternation',
                        'options': group_content.split('|'),
                        'quantifier': self._get_quantifier(pattern, end),
                    })
                else:
                    instructions.append({
                        'type': 'group',
                        'pattern': group_content,
                        'quantifier': self._get_quantifier(pattern, end),
                    })
                i = end + len(instructions[-1]['quantifier'].get('raw', ''))
            elif char == '|':
                # Top-level alternation - split and handle
                # This handles patterns like "abc|def" without parentheses
                left_part = pattern[:i]
                right_part = pattern[i+1:]
                instructions = [{
                    'type': 'alternation',
                    'options': [left_part, right_part],
                    'quantifier': {'min': 1, 'max': 1, 'raw': ''},
                }]
                break  # We've restructured, stop parsing
            else:
                # Literal character
                instructions.append({
                    'type': 'literal',
                    'char': char,
                    'quantifier': self._get_quantifier(pattern, i + 1),
                })
                i += 1 + len(instructions[-1].get('quantifier', {}).get('raw', ''))

        return instructions

    def _get_quantifier(self, pattern: str, pos: int) -> dict:
        """Extract quantifier from pattern at position."""
        if pos >= len(pattern):
            return {'min': 1, 'max': 1, 'raw': ''}

        char = pattern[pos]

        if char == '?':
            return {'min': 0, 'max': 1, 'raw': '?'}
        elif char == '*':
            return {'min': 0, 'max': 10, 'raw': '*'}  # Limit for generation
        elif char == '+':
            return {'min': 1, 'max': 10, 'raw': '+'}  # Limit for generation
        elif char == '{':
            end = pattern.find('}', pos)
            if end == -1:
                return {'min': 1, 'max': 1, 'raw': ''}

            quantifier_str = pattern[pos + 1:end]
            raw = pattern[pos:end + 1]

            if ',' in quantifier_str:
                parts = quantifier_str.split(',')
                min_val = int(parts[0]) if parts[0] else 0
                max_val = int(parts[1]) if parts[1] else min_val + 10
            else:
                min_val = max_val = int(quantifier_str)

            return {'min': min_val, 'max': max_val, 'raw': raw}

        return {'min': 1, 'max': 1, 'raw': ''}

    def _expand_char_class(self, class_content: str) -> str:
        """Expand a character class like 'a-z0-9' into individual characters."""
        chars = []
        negated = class_content.startswith('^')
        if negated:
            class_content = class_content[1:]

        i = 0
        while i < len(class_content):
            if i + 2 < len(class_content) and class_content[i + 1] == '-':
                # Range
                start = class_content[i]
                end = class_content[i + 2]
                for c in range(ord(start), ord(end) + 1):
                    chars.append(chr(c))
                i += 3
            elif class_content[i] == '\\' and i + 1 < len(class_content):
                # Escaped char or class
                escape_seq = class_content[i:i + 2]
                if escape_seq in self.CHAR_CLASSES:
                    chars.extend(self.CHAR_CLASSES[escape_seq])
                else:
                    chars.append(class_content[i + 1])
                i += 2
            else:
                chars.append(class_content[i])
                i += 1

        result = ''.join(chars)

        if negated:
            all_chars = string.printable
            result = ''.join(c for c in all_chars if c not in result)

        return result

    def _filter_by_learned(self, chars: str) -> str:
        """Filter characters to prefer those in learned charset."""
        if not self.use_learned_charset:
            return chars

        learned = set(self.analysis.charset)
        filtered = ''.join(c for c in chars if c in learned)

        return filtered if filtered else chars

    def generate_one(self) -> Optional[str]:
        """Generate a string matching the regex pattern."""
        result = []

        for instruction in self._parsed:
            inst_type = instruction['type']
            quantifier = instruction.get('quantifier', {'min': 1, 'max': 1})

            # Determine repetition count
            if quantifier['min'] == quantifier['max']:
                count = quantifier['min']
            else:
                count = self._random_choice(
                    list(range(quantifier['min'], quantifier['max'] + 1))
                )

            for _ in range(count):
                if inst_type == 'literal':
                    result.append(instruction['char'])
                elif inst_type == 'class':
                    chars = self._filter_by_learned(instruction['chars'])
                    if chars:
                        result.append(self._random_choice(list(chars)))
                elif inst_type == 'alternation':
                    # Pick one of the alternatives randomly
                    chosen = self._random_choice(instruction['options'])
                    # Recursively generate from chosen alternative
                    sub_gen = RegexGenerator(
                        self.analysis,
                        chosen,
                        exclude_original=False,
                        use_learned_charset=self.use_learned_charset,
                    )
                    if self._rng:
                        sub_gen._rng = self._rng
                        sub_gen._use_secure_random = False
                    sub_result = sub_gen.generate_one()
                    if sub_result:
                        result.append(sub_result)
                    else:
                        # If sub-generation failed, use the literal
                        result.append(chosen)
                elif inst_type == 'group':
                    # Recursively handle group
                    sub_gen = RegexGenerator(
                        self.analysis,
                        instruction['pattern'],
                        exclude_original=False,
                        use_learned_charset=self.use_learned_charset,
                    )
                    if self._rng:
                        sub_gen._rng = self._rng
                        sub_gen._use_secure_random = False
                    sub_result = sub_gen.generate_one()
                    if sub_result:
                        result.append(sub_result)

        generated = ''.join(result)

        # Validate against original regex
        if self._compiled.fullmatch(generated):
            return generated

        return None

    def generate_validated(
        self,
        count: int,
        max_attempts: int = 0,
    ) -> List[str]:
        """
        Generate strings with strict regex validation.

        Falls back to random generation + validation if parsing fails.
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

            # Double-check regex match
            if not self._compiled.fullmatch(word):
                continue

            if not self.is_duplicate(word):
                results.append(word)
                self._generated.add(word)

        return results


class RegexInferenceGenerator(BaseGenerator):
    """
    Infers regex patterns from the analysis and generates matching strings.

    This is the inverse of RegexGenerator - it learns patterns from data
    and can output the inferred regex.
    """

    def __init__(
        self,
        analysis: AnalysisResult,
        seed: Optional[int] = None,
        exclude_original: bool = True,
    ):
        super().__init__(analysis, seed, exclude_original)
        self._inferred_patterns: Dict[int, List[str]] = {}
        self._infer_patterns()

    def _infer_patterns(self) -> None:
        """Infer regex patterns from analysis data."""
        for length, length_stats in self.analysis.length_stats.items():
            patterns = []

            for pattern, count in length_stats.patterns.most_common():
                regex = self._pattern_to_regex(pattern, length_stats)
                patterns.append(regex)

            self._inferred_patterns[length] = patterns

    def _pattern_to_regex(self, pattern: str, length_stats) -> str:
        """Convert a CharType pattern to a regex string."""
        regex_parts = []

        for i, char_type in enumerate(pattern):
            pos_stats = length_stats.positions.get(i)

            if pos_stats:
                # Get specific characters seen at this position for this type
                ct = CharType(char_type)
                chars = pos_stats.get_chars_by_type(ct)

                if chars:
                    if len(chars) == 1:
                        char = chars[0]
                        # Escape special regex chars
                        if char in r'\.^$*+?{}[]|()':
                            regex_parts.append(f'\\{char}')
                        else:
                            regex_parts.append(char)
                    else:
                        # Create character class
                        escaped = ''.join(
                            f'\\{c}' if c in r'\.^$*+?{}[]|()-' else c
                            for c in sorted(chars)
                        )
                        regex_parts.append(f'[{escaped}]')
                else:
                    regex_parts.append(self._type_to_regex_class(ct))
            else:
                regex_parts.append(self._type_to_regex_class(CharType(char_type)))

        return ''.join(regex_parts)

    def _type_to_regex_class(self, char_type: CharType) -> str:
        """Convert CharType to regex character class."""
        if char_type == CharType.UPPER:
            return '[A-Z]'
        elif char_type == CharType.LOWER:
            return '[a-z]'
        elif char_type == CharType.DIGIT:
            return r'\d'
        else:
            return r'[^a-zA-Z0-9]'

    def get_inferred_regexes(self, length: Optional[int] = None) -> List[str]:
        """Get the inferred regex patterns."""
        if length is not None:
            return self._inferred_patterns.get(length, [])

        all_patterns = []
        for patterns in self._inferred_patterns.values():
            all_patterns.extend(patterns)
        return all_patterns

    def generate_one(self) -> Optional[str]:
        """Generate using one of the inferred patterns."""
        length = self._choose_length()

        if length not in self._inferred_patterns:
            return None

        patterns = self._inferred_patterns[length]
        if not patterns:
            return None

        # Use the most common pattern (first in list)
        pattern = patterns[0]

        gen = RegexGenerator(
            self.analysis,
            f'^{pattern}$',
            exclude_original=self.exclude_original,
            use_learned_charset=True,
        )

        return gen.generate_one()
