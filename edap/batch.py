"""
Batch processing - process multiple wordlists at once.
"""

import os
from pathlib import Path
from typing import List, Optional, Iterator, Callable, Dict, Any
from dataclasses import dataclass, field

from edap.analyzer import PatternAnalyzer
from edap.models import AnalysisResult


@dataclass
class BatchResult:
    """Result from processing a single file in a batch."""
    filepath: Path
    success: bool
    analysis: Optional[AnalysisResult] = None
    error: Optional[str] = None
    generated: List[str] = field(default_factory=list)


class BatchProcessor:
    """
    Process multiple wordlist files in batch.

    Supports:
    - Processing multiple files with same settings
    - Merging analysis from multiple files
    - Progress callbacks for monitoring
    """

    def __init__(
        self,
        min_length: int = 1,
        max_length: int = 256,
        encoding: str = "utf-8",
    ):
        """
        Initialize the batch processor.

        Args:
            min_length: Minimum word length to analyze
            max_length: Maximum word length to analyze
            encoding: File encoding
        """
        self.min_length = min_length
        self.max_length = max_length
        self.encoding = encoding
        self._analyzer = PatternAnalyzer(
            min_length=min_length,
            max_length=max_length,
        )

    def process_files(
        self,
        filepaths: List[Path],
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> List[BatchResult]:
        """
        Process multiple files individually.

        Args:
            filepaths: List of file paths to process
            progress_callback: Called with (current, total, filepath) for progress

        Returns:
            List of BatchResult objects
        """
        results = []
        total = len(filepaths)

        for i, filepath in enumerate(filepaths):
            if progress_callback:
                progress_callback(i, total, filepath)

            result = self._process_single(filepath)
            results.append(result)

        if progress_callback:
            progress_callback(total, total, filepaths[-1] if filepaths else Path("."))

        return results

    def _process_single(self, filepath: Path) -> BatchResult:
        """Process a single file."""
        try:
            filepath = Path(filepath)
            if not filepath.exists():
                return BatchResult(
                    filepath=filepath,
                    success=False,
                    error=f"File not found: {filepath}",
                )

            analysis = self._analyzer.analyze_file(filepath, encoding=self.encoding)

            return BatchResult(
                filepath=filepath,
                success=True,
                analysis=analysis,
            )

        except Exception as e:
            return BatchResult(
                filepath=filepath,
                success=False,
                error=str(e),
            )

    def process_directory(
        self,
        directory: Path,
        pattern: str = "*.txt",
        recursive: bool = False,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> List[BatchResult]:
        """
        Process all matching files in a directory.

        Args:
            directory: Directory to search
            pattern: Glob pattern for files
            recursive: Search subdirectories
            progress_callback: Progress callback

        Returns:
            List of BatchResult objects
        """
        directory = Path(directory)

        if recursive:
            filepaths = list(directory.rglob(pattern))
        else:
            filepaths = list(directory.glob(pattern))

        return self.process_files(filepaths, progress_callback)

    def merge_analyses(
        self,
        results: List[BatchResult],
    ) -> Optional[AnalysisResult]:
        """
        Merge analysis results from multiple files.

        Args:
            results: List of batch results

        Returns:
            Merged AnalysisResult or None if no successful analyses
        """
        successful = [r for r in results if r.success and r.analysis]

        if not successful:
            return None

        if len(successful) == 1:
            return successful[0].analysis

        # Collect all words and re-analyze
        all_words: List[str] = []

        for result in successful:
            # We need to re-read the files to get the words
            try:
                with open(result.filepath, 'r', encoding=self.encoding, errors='ignore') as f:
                    for line in f:
                        word = line.strip()
                        if self.min_length <= len(word) <= self.max_length:
                            all_words.append(word)
            except Exception:
                continue

        if not all_words:
            return None

        return self._analyzer.analyze_words(all_words)

    def process_and_merge(
        self,
        filepaths: List[Path],
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> tuple[List[BatchResult], Optional[AnalysisResult]]:
        """
        Process files and return both individual and merged results.

        Args:
            filepaths: Files to process
            progress_callback: Progress callback

        Returns:
            Tuple of (individual results, merged analysis)
        """
        results = self.process_files(filepaths, progress_callback)
        merged = self.merge_analyses(results)
        return results, merged

    def iter_words(
        self,
        filepaths: List[Path],
    ) -> Iterator[str]:
        """
        Iterate over words from multiple files.

        Args:
            filepaths: Files to read

        Yields:
            Words from all files
        """
        for filepath in filepaths:
            try:
                with open(filepath, 'r', encoding=self.encoding, errors='ignore') as f:
                    for line in f:
                        word = line.strip()
                        if self.min_length <= len(word) <= self.max_length:
                            yield word
            except Exception:
                continue

    def summary(self, results: List[BatchResult]) -> Dict[str, Any]:
        """
        Generate summary of batch processing results.

        Args:
            results: Batch results

        Returns:
            Summary dictionary
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_words = sum(
            r.analysis.total_words for r in successful if r.analysis
        )
        total_unique = sum(
            r.analysis.unique_words for r in successful if r.analysis
        )

        return {
            "total_files": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_words": total_words,
            "total_unique_words": total_unique,
            "failed_files": [
                {"path": str(r.filepath), "error": r.error}
                for r in failed
            ],
        }
