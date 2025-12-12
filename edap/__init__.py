"""
EDAP - Empirical Distribution Analysis for Patterns
A pattern analysis and string generation tool.

Author: Ehab Hussein
"""

__version__ = "2.0.0"
__author__ = "Ehab Hussein"

from edap.models import (
    CharType,
    WordAnalysis,
    PositionStats,
    LengthStats,
    AnalysisResult,
)
from edap.analyzer import PatternAnalyzer
from edap.generators import (
    RandomGenerator,
    SmartGenerator,
    PatternGenerator,
    RegexGenerator,
    RegexInferenceGenerator,
)
from edap.regex_builder import RegexBuilder
from edap.exporters import (
    HashAlgorithm,
    OutputFormat,
    Hasher,
    ResultExporter,
)

__all__ = [
    # Models
    "CharType",
    "WordAnalysis",
    "PositionStats",
    "LengthStats",
    "AnalysisResult",
    # Analyzer
    "PatternAnalyzer",
    # Generators
    "RandomGenerator",
    "SmartGenerator",
    "PatternGenerator",
    "RegexGenerator",
    "RegexInferenceGenerator",
    # Regex
    "RegexBuilder",
    # Exporters
    "HashAlgorithm",
    "OutputFormat",
    "Hasher",
    "ResultExporter",
]
