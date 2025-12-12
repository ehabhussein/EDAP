"""
EDAP - Empirical Distribution Analysis for Patterns
A pattern analysis and string generation tool.

Author: Ehab Hussein
"""

__version__ = "2.1.0"
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
    MarkovGenerator,
    HybridGenerator,
    create_hybrid_generator,
)
from edap.regex_builder import RegexBuilder
from edap.exporters import (
    HashAlgorithm,
    OutputFormat,
    Hasher,
    ResultExporter,
)
from edap.mutator import Mutator, RULE_PRESETS
from edap.scorer import Scorer, StrengthScore
from edap.filters import Filter, FilterConfig, create_filter, FILTER_PRESETS
from edap.stats_exporter import StatsExporter
from edap.batch import BatchProcessor, BatchResult
from edap.progress import ProgressBar, progress, Spinner

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
    "MarkovGenerator",
    "HybridGenerator",
    "create_hybrid_generator",
    # Regex
    "RegexBuilder",
    # Exporters
    "HashAlgorithm",
    "OutputFormat",
    "Hasher",
    "ResultExporter",
    "StatsExporter",
    # Mutator
    "Mutator",
    "RULE_PRESETS",
    # Scorer
    "Scorer",
    "StrengthScore",
    # Filters
    "Filter",
    "FilterConfig",
    "create_filter",
    "FILTER_PRESETS",
    # Batch
    "BatchProcessor",
    "BatchResult",
    # Progress
    "ProgressBar",
    "progress",
    "Spinner",
]
