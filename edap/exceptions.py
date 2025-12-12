"""
Custom exceptions for EDAP.
"""


class EdapError(Exception):
    """Base exception for all EDAP errors."""
    pass


class AnalysisError(EdapError):
    """Error during pattern analysis."""
    pass


class EmptyInputError(AnalysisError):
    """Input file or wordlist is empty."""

    def __init__(self, source: str = "input"):
        self.source = source
        super().__init__(f"No valid words found in {source}")


class InvalidWordError(AnalysisError):
    """Word does not meet criteria for analysis."""

    def __init__(self, word: str, reason: str):
        self.word = word
        self.reason = reason
        super().__init__(f"Invalid word '{word}': {reason}")


class GenerationError(EdapError):
    """Error during string generation."""
    pass


class InsufficientDataError(GenerationError):
    """Not enough data to generate strings."""

    def __init__(self, required: str, available: str = None):
        self.required = required
        self.available = available
        msg = f"Insufficient data for generation: {required}"
        if available:
            msg += f" (available: {available})"
        super().__init__(msg)


class PatternMismatchError(GenerationError):
    """Generated string does not match expected pattern."""

    def __init__(self, generated: str, pattern: str):
        self.generated = generated
        self.pattern = pattern
        super().__init__(
            f"Generated string '{generated}' does not match pattern '{pattern}'"
        )


class RegexError(EdapError):
    """Error with regex pattern."""
    pass


class InvalidRegexError(RegexError):
    """Provided regex pattern is invalid."""

    def __init__(self, pattern: str, error: str):
        self.pattern = pattern
        self.error = error
        super().__init__(f"Invalid regex pattern '{pattern}': {error}")


class UnsupportedRegexError(RegexError):
    """Regex contains unsupported features."""

    def __init__(self, pattern: str, feature: str):
        self.pattern = pattern
        self.feature = feature
        super().__init__(
            f"Regex pattern '{pattern}' contains unsupported feature: {feature}"
        )


class ExportError(EdapError):
    """Error during export."""
    pass


class UnsupportedFormatError(ExportError):
    """Export format is not supported."""

    def __init__(self, format: str, supported: list):
        self.format = format
        self.supported = supported
        super().__init__(
            f"Unsupported format '{format}'. Supported: {', '.join(supported)}"
        )


class UnsupportedHashError(ExportError):
    """Hash algorithm is not supported."""

    def __init__(self, algorithm: str, supported: list):
        self.algorithm = algorithm
        self.supported = supported
        super().__init__(
            f"Unsupported hash algorithm '{algorithm}'. Supported: {', '.join(supported)}"
        )
