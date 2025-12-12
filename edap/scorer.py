"""
Password/string strength scoring.
"""

import math
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from edap.models import CharType


@dataclass
class StrengthScore:
    """Result of strength analysis."""
    score: float  # 0-100
    entropy: float  # bits
    length: int
    has_upper: bool
    has_lower: bool
    has_digit: bool
    has_symbol: bool
    char_types: int  # number of character types used
    repeated_chars: int
    sequential_chars: int
    common_pattern: Optional[str]
    feedback: List[str]

    @property
    def rating(self) -> str:
        """Get human-readable rating."""
        if self.score >= 80:
            return "Very Strong"
        elif self.score >= 60:
            return "Strong"
        elif self.score >= 40:
            return "Moderate"
        elif self.score >= 20:
            return "Weak"
        else:
            return "Very Weak"


class Scorer:
    """
    Score password/string strength.

    Considers:
    - Length
    - Character diversity (upper, lower, digit, symbol)
    - Entropy
    - Common patterns
    - Repeated/sequential characters
    """

    # Common weak patterns
    WEAK_PATTERNS = [
        (r'^[a-z]+$', "lowercase only"),
        (r'^[A-Z]+$', "uppercase only"),
        (r'^[0-9]+$', "digits only"),
        (r'^(.)\1+$', "repeated single character"),
        (r'^(12|123|1234|12345|123456)', "starts with sequential digits"),
        (r'(password|passwd|pwd)', "contains 'password'"),
        (r'(qwerty|asdf|zxcv)', "keyboard pattern"),
        (r'(abc|xyz)', "alphabetic sequence"),
        (r'^[a-z]+[0-9]+$', "simple word+numbers"),
        (r'^[A-Z][a-z]+[0-9]+$', "capitalized word+numbers"),
    ]

    # Sequential characters to detect
    SEQUENCES = "abcdefghijklmnopqrstuvwxyz0123456789"

    def __init__(self):
        """Initialize the scorer."""
        self._compiled_patterns = [
            (re.compile(p, re.IGNORECASE), desc)
            for p, desc in self.WEAK_PATTERNS
        ]

    def score(self, password: str) -> StrengthScore:
        """
        Score a password's strength.

        Args:
            password: The string to score

        Returns:
            StrengthScore with detailed analysis
        """
        if not password:
            return StrengthScore(
                score=0,
                entropy=0,
                length=0,
                has_upper=False,
                has_lower=False,
                has_digit=False,
                has_symbol=False,
                char_types=0,
                repeated_chars=0,
                sequential_chars=0,
                common_pattern="empty",
                feedback=["Password is empty"],
            )

        # Character analysis
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(not c.isalnum() for c in password)

        char_types = sum([has_upper, has_lower, has_digit, has_symbol])

        # Count repeated characters
        repeated = self._count_repeated(password)

        # Count sequential characters
        sequential = self._count_sequential(password)

        # Check for common patterns
        common_pattern = self._check_patterns(password)

        # Calculate entropy
        entropy = self._calculate_entropy(password)

        # Calculate base score
        score = self._calculate_score(
            length=len(password),
            char_types=char_types,
            entropy=entropy,
            repeated=repeated,
            sequential=sequential,
            common_pattern=common_pattern,
        )

        # Generate feedback
        feedback = self._generate_feedback(
            length=len(password),
            char_types=char_types,
            has_upper=has_upper,
            has_lower=has_lower,
            has_digit=has_digit,
            has_symbol=has_symbol,
            repeated=repeated,
            sequential=sequential,
            common_pattern=common_pattern,
            entropy=entropy,
        )

        return StrengthScore(
            score=score,
            entropy=entropy,
            length=len(password),
            has_upper=has_upper,
            has_lower=has_lower,
            has_digit=has_digit,
            has_symbol=has_symbol,
            char_types=char_types,
            repeated_chars=repeated,
            sequential_chars=sequential,
            common_pattern=common_pattern,
            feedback=feedback,
        )

    def _count_repeated(self, s: str) -> int:
        """Count repeated consecutive characters."""
        if len(s) < 2:
            return 0

        count = 0
        for i in range(1, len(s)):
            if s[i] == s[i - 1]:
                count += 1
        return count

    def _count_sequential(self, s: str) -> int:
        """Count sequential characters (abc, 123, etc.)."""
        if len(s) < 3:
            return 0

        count = 0
        lower = s.lower()

        for i in range(len(lower) - 2):
            substr = lower[i:i + 3]
            if substr in self.SEQUENCES or substr in self.SEQUENCES[::-1]:
                count += 1

        return count

    def _check_patterns(self, s: str) -> Optional[str]:
        """Check for common weak patterns."""
        for pattern, desc in self._compiled_patterns:
            if pattern.search(s):
                return desc
        return None

    def _calculate_entropy(self, s: str) -> float:
        """
        Calculate Shannon entropy in bits.

        Higher entropy = more randomness = stronger.
        """
        if not s:
            return 0

        # Calculate charset size based on character types present
        charset_size = 0
        if any(c.islower() for c in s):
            charset_size += 26
        if any(c.isupper() for c in s):
            charset_size += 26
        if any(c.isdigit() for c in s):
            charset_size += 10
        if any(not c.isalnum() for c in s):
            charset_size += 32  # Approximate symbol count

        if charset_size == 0:
            return 0

        # Entropy = length * log2(charset_size)
        return len(s) * math.log2(charset_size)

    def _calculate_score(
        self,
        length: int,
        char_types: int,
        entropy: float,
        repeated: int,
        sequential: int,
        common_pattern: Optional[str],
    ) -> float:
        """Calculate overall score (0-100)."""
        score = 0.0

        # Length contribution (max 30 points)
        # 8 chars = 15 points, 12 chars = 25 points, 16+ = 30 points
        length_score = min(30, length * 2)
        score += length_score

        # Character diversity (max 25 points)
        score += char_types * 6.25

        # Entropy contribution (max 25 points)
        # 40 bits = 10 points, 60 bits = 18 points, 80+ bits = 25 points
        entropy_score = min(25, entropy / 3.2)
        score += entropy_score

        # Uniqueness bonus (max 20 points)
        unique_ratio = len(set(s for s in str(length))) / max(1, length) if length > 0 else 0
        score += unique_ratio * 10

        # Penalties
        if common_pattern:
            score -= 20

        score -= repeated * 2
        score -= sequential * 3

        # Clamp to 0-100
        return max(0, min(100, score))

    def _generate_feedback(
        self,
        length: int,
        char_types: int,
        has_upper: bool,
        has_lower: bool,
        has_digit: bool,
        has_symbol: bool,
        repeated: int,
        sequential: int,
        common_pattern: Optional[str],
        entropy: float,
    ) -> List[str]:
        """Generate improvement suggestions."""
        feedback = []

        if length < 8:
            feedback.append("Use at least 8 characters")
        elif length < 12:
            feedback.append("Consider using 12+ characters for better security")

        if not has_upper:
            feedback.append("Add uppercase letters")
        if not has_lower:
            feedback.append("Add lowercase letters")
        if not has_digit:
            feedback.append("Add numbers")
        if not has_symbol:
            feedback.append("Add symbols (!@#$%^&*)")

        if repeated > 2:
            feedback.append("Avoid repeated characters")
        if sequential > 1:
            feedback.append("Avoid sequential characters (abc, 123)")

        if common_pattern:
            feedback.append(f"Avoid common pattern: {common_pattern}")

        if entropy < 40:
            feedback.append("Increase randomness/complexity")

        if not feedback:
            feedback.append("Good password strength!")

        return feedback

    def score_many(self, passwords: List[str]) -> List[StrengthScore]:
        """
        Score multiple passwords.

        Args:
            passwords: List of strings to score

        Returns:
            List of StrengthScore objects
        """
        return [self.score(p) for p in passwords]

    def average_score(self, passwords: List[str]) -> float:
        """
        Calculate average score for a list of passwords.

        Args:
            passwords: List of strings

        Returns:
            Average score (0-100)
        """
        if not passwords:
            return 0

        scores = self.score_many(passwords)
        return sum(s.score for s in scores) / len(scores)

    def filter_by_strength(
        self,
        passwords: List[str],
        min_score: float = 0,
        max_score: float = 100,
    ) -> List[str]:
        """
        Filter passwords by strength score.

        Args:
            passwords: Input passwords
            min_score: Minimum score (inclusive)
            max_score: Maximum score (inclusive)

        Returns:
            Filtered list
        """
        return [
            p for p in passwords
            if min_score <= self.score(p).score <= max_score
        ]
