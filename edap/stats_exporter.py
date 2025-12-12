"""
Statistics exporter - export analysis results in various formats.
"""

import json
import csv
import io
from typing import Dict, Any, Optional
from pathlib import Path

from edap.models import AnalysisResult, CharType


class StatsExporter:
    """
    Export analysis statistics in various formats.

    Supports JSON, CSV, and summary text output.
    """

    def __init__(self, result: AnalysisResult):
        """
        Initialize the exporter.

        Args:
            result: Analysis result to export
        """
        self.result = result

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert analysis result to a dictionary.

        Returns:
            Dictionary representation of the analysis
        """
        return {
            "summary": {
                "total_words": self.result.total_words,
                "unique_words": self.result.unique_words,
                "min_length": self.result.min_length,
                "max_length": self.result.max_length,
                "charset_size": len(self.result.charset),
            },
            "charset": sorted(list(self.result.charset)),
            "charset_by_type": {
                ct.name: sorted(list(self.result.get_charset_by_type(ct)))
                for ct in CharType
            },
            "length_distribution": {
                str(length): {
                    "count": ls.count,
                    "percentage": round(ls.count / self.result.total_words * 100, 2)
                    if self.result.total_words > 0 else 0,
                    "patterns": dict(ls.patterns.most_common(10)),
                }
                for length, ls in sorted(self.result.length_stats.items())
            },
            "position_stats": self._export_position_stats(),
            "type_frequency": self._export_type_frequency(),
        }

    def _export_position_stats(self) -> Dict[str, Any]:
        """Export position-level statistics."""
        stats = {}

        for length, ls in sorted(self.result.length_stats.items()):
            length_key = str(length)
            stats[length_key] = {}

            for pos, ps in sorted(ls.positions.items()):
                pos_key = str(pos)
                # Convert CharType enum keys to strings for JSON serialization
                type_dist = {
                    str(k) if hasattr(k, 'name') else k: v
                    for k, v in ps.type_counts.items()
                }
                stats[length_key][pos_key] = {
                    "total_chars": ps.total_chars,
                    "unique_chars": len(ps.char_counts),
                    "top_chars": dict(ps.char_counts.most_common(10)),
                    "type_distribution": type_dist,
                }

        return stats

    def _export_type_frequency(self) -> Dict[str, int]:
        """Export character type frequency."""
        type_counts: Dict[str, int] = {ct.name: 0 for ct in CharType}

        for length, ls in self.result.length_stats.items():
            for pos, ps in ls.positions.items():
                for ct_key, count in ps.type_counts.items():
                    # Convert CharType enum to string if needed
                    ct_name = ct_key.name if hasattr(ct_key, 'name') else str(ct_key)
                    type_counts[ct_name] = type_counts.get(ct_name, 0) + count

        return type_counts

    def to_json(self, indent: int = 2) -> str:
        """
        Export as JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_json_file(self, filepath: Path, indent: int = 2) -> None:
        """
        Export to JSON file.

        Args:
            filepath: Output file path
            indent: JSON indentation level
        """
        filepath = Path(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=indent)

    def to_csv(self) -> str:
        """
        Export length distribution as CSV.

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Length",
            "Count",
            "Percentage",
            "Top_Pattern",
            "Pattern_Count",
        ])

        # Data
        for length, ls in sorted(self.result.length_stats.items()):
            percentage = round(ls.count / self.result.total_words * 100, 2) \
                if self.result.total_words > 0 else 0

            top_pattern = ""
            pattern_count = 0
            if ls.patterns:
                top = ls.patterns.most_common(1)
                if top:
                    top_pattern, pattern_count = top[0]

            writer.writerow([
                length,
                ls.count,
                percentage,
                top_pattern,
                pattern_count,
            ])

        return output.getvalue()

    def to_csv_file(self, filepath: Path) -> None:
        """
        Export to CSV file.

        Args:
            filepath: Output file path
        """
        filepath = Path(filepath)
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            f.write(self.to_csv())

    def to_position_csv(self) -> str:
        """
        Export position statistics as CSV.

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Length",
            "Position",
            "Total_Chars",
            "Unique_Chars",
            "Top_Char",
            "Top_Char_Count",
            "Upper_Count",
            "Lower_Count",
            "Digit_Count",
            "Symbol_Count",
        ])

        # Data
        for length, ls in sorted(self.result.length_stats.items()):
            for pos, ps in sorted(ls.positions.items()):
                top_char = ""
                top_count = 0
                if ps.char_counts:
                    top = ps.char_counts.most_common(1)
                    if top:
                        top_char, top_count = top[0]

                writer.writerow([
                    length,
                    pos,
                    ps.total_chars,
                    len(ps.char_counts),
                    top_char,
                    top_count,
                    ps.type_counts.get("U", 0),
                    ps.type_counts.get("l", 0),
                    ps.type_counts.get("n", 0),
                    ps.type_counts.get("@", 0),
                ])

        return output.getvalue()

    def to_summary(self) -> str:
        """
        Export as human-readable summary.

        Returns:
            Summary text
        """
        lines = [
            "=" * 60,
            "EDAP Analysis Summary",
            "=" * 60,
            "",
            f"Total words analyzed: {self.result.total_words}",
            f"Unique words: {self.result.unique_words}",
            f"Length range: {self.result.min_length} - {self.result.max_length}",
            f"Charset size: {len(self.result.charset)}",
            "",
            "Length Distribution:",
            "-" * 40,
        ]

        for length, ls in sorted(self.result.length_stats.items()):
            pct = ls.count / self.result.total_words * 100 if self.result.total_words > 0 else 0
            bar = "#" * int(pct / 2)
            lines.append(f"  {length:3d}: {bar:25s} ({ls.count:5d} words, {pct:5.1f}%)")

        lines.extend([
            "",
            "Character Type Frequency:",
            "-" * 40,
        ])

        type_counts = self._export_type_frequency()
        total_chars = sum(type_counts.values())

        for ct in CharType:
            count = type_counts.get(ct.name, 0)
            pct = count / total_chars * 100 if total_chars > 0 else 0
            lines.append(f"  {ct.name:8s}: {count:8d} ({pct:5.1f}%)")

        lines.extend([
            "",
            "Top 10 Patterns:",
            "-" * 40,
        ])

        all_patterns: Dict[str, int] = {}
        for ls in self.result.length_stats.values():
            for pattern, count in ls.patterns.items():
                all_patterns[pattern] = all_patterns.get(pattern, 0) + count

        sorted_patterns = sorted(all_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
        for pattern, count in sorted_patterns:
            lines.append(f"  {pattern:20s}: {count:5d}")

        lines.append("=" * 60)

        return "\n".join(lines)
