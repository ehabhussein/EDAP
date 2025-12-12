#!/usr/bin/env python3
"""
EDAP Command Line Interface.

Efficient Dynamic Algorithms for Probability
A password/string pattern analysis and generation tool.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from edap import __version__, __author__
from edap.analyzer import PatternAnalyzer
from edap.generators import (
    RandomGenerator,
    SmartGenerator,
    PatternGenerator,
    RegexGenerator,
)
from edap.regex_builder import RegexBuilder
from edap.exporters import (
    HashAlgorithm,
    OutputFormat,
    ResultExporter,
)

# ASCII art banner
BANNER = r"""
 ______           _           _     _ _  _
(_____ \         | |         | |   (_) |(_)  _
 _____) )___ ___ | |__  _____| |__  _| | _ _| |_ _   _
|  ____/ ___) _ \|  _ \(____ |  _ \| | || (_   _) | | |
| |   | |  | |_| | |_) ) ___ | |_) ) | || | | |_| |_| |
|_|   |_|   \___/|____/\_____|____/|_|\_)_|  \__)\__  |
           Efficient Dynamic Algorithms         (____/
                    Ehab Hussein
"""


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging based on verbosity."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='edap',
        description='EDAP - Efficient Dynamic Algorithms for Probability',
        epilog='Example: edap wordlist.txt -n 100 -m smart -o output.txt',
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    # UI mode
    parser.add_argument(
        '--ui',
        action='store_true',
        help='Launch the web UI (requires: pip install edap[ui])',
    )

    # Input
    parser.add_argument(
        'input',
        type=Path,
        nargs='?',  # Make optional when --ui is used
        help='Input wordlist file',
    )

    # Generation options
    parser.add_argument(
        '-n', '--count',
        type=int,
        default=10,
        help='Number of strings to generate (default: 10)',
    )

    parser.add_argument(
        '-m', '--mode',
        choices=['random', 'smart', 'pattern', 'regex'],
        default='smart',
        help='Generation mode (default: smart)',
    )

    parser.add_argument(
        '--regex',
        type=str,
        help='Regex pattern for regex mode',
    )

    parser.add_argument(
        '--pattern',
        type=str,
        help='Explicit type pattern (e.g., "UllnnU") for pattern mode',
    )

    # Output options
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file (default: stdout)',
    )

    parser.add_argument(
        '-f', '--format',
        choices=['text', 'json', 'csv', 'jsonl'],
        default='text',
        help='Output format (default: text)',
    )

    parser.add_argument(
        '--hash',
        type=str,
        choices=HashAlgorithm.list_algorithms(),
        help='Apply hash algorithm to output',
    )

    # Analysis options
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze input, do not generate',
    )

    parser.add_argument(
        '--show-stats',
        action='store_true',
        help='Show detailed statistics',
    )

    parser.add_argument(
        '--show-patterns',
        action='store_true',
        help='Show inferred regex patterns',
    )

    # Length filtering
    parser.add_argument(
        '--min-length',
        type=int,
        default=1,
        help='Minimum word length to analyze (default: 1)',
    )

    parser.add_argument(
        '--max-length',
        type=int,
        default=256,
        help='Maximum word length to analyze (default: 256)',
    )

    parser.add_argument(
        '--length',
        type=int,
        help='Generate only strings of this exact length',
    )

    # Other options
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility',
    )

    parser.add_argument(
        '--allow-duplicates',
        action='store_true',
        help='Allow generating duplicates of input words',
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output',
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress informational output',
    )

    parser.add_argument(
        '--no-banner',
        action='store_true',
        help='Suppress banner',
    )

    return parser


def analyze_input(
    filepath: Path,
    min_length: int,
    max_length: int,
    show_stats: bool,
) -> 'AnalysisResult':
    """Analyze the input file."""
    analyzer = PatternAnalyzer(min_length=min_length, max_length=max_length)
    result = analyzer.analyze_file(filepath)

    if show_stats:
        analyzer.print_detailed_stats(result)

    return result, analyzer


def generate_strings(
    result,
    mode: str,
    count: int,
    seed: Optional[int],
    allow_duplicates: bool,
    regex_pattern: Optional[str] = None,
    type_pattern: Optional[str] = None,
    target_length: Optional[int] = None,
) -> List[str]:
    """Generate strings using the specified mode."""
    # Select generator
    if mode == 'random':
        generator = RandomGenerator(
            result,
            seed=seed,
            exclude_original=not allow_duplicates,
        )
    elif mode == 'smart':
        generator = SmartGenerator(
            result,
            seed=seed,
            exclude_original=not allow_duplicates,
        )
    elif mode == 'pattern':
        generator = PatternGenerator(
            result,
            seed=seed,
            exclude_original=not allow_duplicates,
        )
    elif mode == 'regex':
        if not regex_pattern:
            logging.error("Regex mode requires --regex pattern")
            sys.exit(1)
        generator = RegexGenerator(
            result,
            pattern=regex_pattern,
            seed=seed,
            exclude_original=not allow_duplicates,
        )
    else:
        logging.error(f"Unknown mode: {mode}")
        sys.exit(1)

    # Handle explicit pattern for pattern mode
    if mode == 'pattern' and type_pattern:
        generated = []
        for _ in range(count):
            word = generator.generate_from_explicit_pattern(type_pattern)
            if word:
                generated.append(word)
        return generated

    # Generate
    generated = generator.generate(count)

    # Calculate and display weights
    if logging.getLogger().level <= logging.INFO:
        for word in generated:
            weight = generator.calculate_weight(word)
            logging.debug(f"Generated: {word} (weight={weight})")

    return generated


def show_regex_patterns(result, specificity: str = 'specific') -> None:
    """Display inferred regex patterns."""
    builder = RegexBuilder(result)
    patterns = builder.build_all_patterns(specificity=specificity)

    print("\n" + "=" * 50)
    print("Inferred Regex Patterns")
    print("=" * 50)
    print(builder.get_coverage_report(patterns))


def launch_ui() -> int:
    """Launch the Streamlit web UI."""
    try:
        import streamlit
    except ImportError:
        print("Error: Streamlit is not installed.")
        print("Install with: pip install edap[ui]")
        return 1

    import subprocess
    from pathlib import Path

    ui_path = Path(__file__).parent / "ui.py"

    print("Launching EDAP Web UI...")
    print("Press Ctrl+C to stop the server.\n")

    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(ui_path),
            "--server.headless", "false",
        ])
    except KeyboardInterrupt:
        print("\nUI stopped.")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle --ui flag first
    if args.ui:
        return launch_ui()

    setup_logging(args.verbose, args.quiet)

    # Show banner
    if not args.no_banner and not args.quiet:
        print(BANNER)

    # Validate input (required when not using --ui)
    if not args.input:
        parser.print_help()
        print("\nError: input file is required (or use --ui for web interface)")
        return 1

    if not args.input.exists():
        logging.error(f"Input file not found: {args.input}")
        return 1

    # Analyze
    logging.info(f"Analyzing: {args.input}")
    result, analyzer = analyze_input(
        args.input,
        args.min_length,
        args.max_length,
        args.show_stats,
    )

    logging.info(f"Analyzed {result.total_words} words ({result.unique_words} unique)")
    logging.info(f"Length range: {result.min_length} - {result.max_length}")

    # Show patterns if requested
    if args.show_patterns:
        show_regex_patterns(result)

    # Exit if analyze-only
    if args.analyze_only:
        return 0

    # Generate
    logging.info(f"Generating {args.count} strings using {args.mode} mode...")

    generated = generate_strings(
        result,
        args.mode,
        args.count,
        args.seed,
        args.allow_duplicates,
        args.regex,
        args.pattern,
        args.length,
    )

    logging.info(f"Generated {len(generated)} strings")

    # Export
    exporter = ResultExporter(
        format=args.format,
        hash_algorithm=args.hash,
    )

    if args.output:
        exporter.export_to_file(generated, args.output)
        logging.info(f"Output written to: {args.output}")
    else:
        output = exporter.export(generated)
        print(output)

    return 0


def entry_point() -> None:
    """Console script entry point."""
    sys.exit(main())


if __name__ == '__main__':
    entry_point()
