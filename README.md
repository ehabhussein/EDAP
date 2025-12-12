# EDAP - Empirical Distribution Analysis for Patterns

A password/string pattern analysis and generation tool for security research.

**Author:** Ehab Hussein

## What is EDAP?

EDAP analyzes wordlists to learn character patterns, frequencies, and positional relationships, then generates new strings that statistically match the learned patterns. This is useful for:

- Security research and password analysis
- Generating targeted wordlists for penetration testing
- Understanding password composition patterns
- Creating test data that matches specific formats

## Features

- **Variable-length support** - Handles mixed-length wordlists correctly
- **4 generation modes** - Random, Smart, Pattern, and Regex-based
- **Pattern inference** - Automatically learns and outputs regex patterns
- **Multiple output formats** - Text, JSON, CSV, JSONL
- **12 hash algorithms** - MD5, SHA family, SHA-3, BLAKE2, Base64
- **Reproducible output** - Seed support for deterministic generation
- **Comprehensive statistics** - Character frequency, position analysis, type distribution

## Installation

```bash
# Clone the repository
git clone https://github.com/ehabhussein/EDAP.git
cd EDAP

# Install (CLI only)
pip install -e .

# Install with Web UI
pip install -e ".[ui]"

# Install everything (dev + ui)
pip install -e ".[all]"
```

### Requirements

- Python 3.9+
- No external dependencies for CLI (stdlib only)
- Streamlit + Pandas for Web UI (optional)

## Quick Start

### Web UI

```bash
# Launch the web interface from CLI
edap --ui

# Or use the dedicated command
edap-ui

# Or run directly with streamlit
streamlit run edap/ui.py
```

The web UI provides:
- File upload or paste input
- Interactive analysis with charts
- All generation modes with live preview
- Export to multiple formats
- Regex pattern inference

### Command Line

```bash
# After pip install -e . the 'edap' command is available
edap wordlist.txt

# Or run as a Python module (no install needed)
python -m edap wordlist.txt

# Generate 100 strings using random mode
edap wordlist.txt -n 100 -m random

# Generate with SHA-256 hashing
edap wordlist.txt -n 50 --hash sha256

# Output as JSON
edap wordlist.txt -n 20 -f json -o output.json

# Analyze only (no generation)
edap wordlist.txt --analyze-only --show-stats
```

### Python API

```python
from edap import PatternAnalyzer, SmartGenerator, Hasher

# Analyze a wordlist
analyzer = PatternAnalyzer()
result = analyzer.analyze_file("wordlist.txt")
print(result.summary())

# Generate new strings
gen = SmartGenerator(result, seed=42)
words = gen.generate(100)

for word in words:
    weight = gen.calculate_weight(word)
    print(f"{word} (weight={weight})")

# Hash the output
hasher = Hasher("sha256")
hashed = hasher.hash_many(words)
```

## Generation Modes

### Random Mode (`-m random`)
Generates strings using characters observed at each position, with random selection. Fastest but least strict.

```bash
edap wordlist.txt -n 100 -m random
```

### Smart Mode (`-m smart`) - Default
Uses character co-occurrence patterns to generate strings where characters that appeared together in training data are more likely to appear together in output.

```bash
edap wordlist.txt -n 100 -m smart
```

### Pattern Mode (`-m pattern`)
Follows observed character type patterns (Uppercase, lowercase, digit, symbol). Most strict mode.

```bash
# Auto-select patterns from training data
edap wordlist.txt -n 100 -m pattern

# Use explicit pattern (U=upper, l=lower, n=digit, @=symbol)
edap wordlist.txt -n 100 -m pattern --pattern "Ullnn@"
```

### Regex Mode (`-m regex`)
Generate strings matching a user-provided regular expression.

```bash
edap wordlist.txt -n 100 -m regex --regex "[A-Z][a-z]{3}[0-9]{2}"
```

## CLI Options

```
usage: edap [-h] [--version] [-n COUNT] [-m {random,smart,pattern,regex}]
            [--regex REGEX] [--pattern PATTERN] [-o OUTPUT]
            [-f {text,json,csv,jsonl}] [--hash ALGORITHM]
            [--analyze-only] [--show-stats] [--show-patterns]
            [--min-length N] [--max-length N] [--length N]
            [--seed SEED] [--allow-duplicates] [-v] [-q] [--no-banner]
            input

Arguments:
  input                 Input wordlist file

Options:
  -n, --count N         Number of strings to generate (default: 10)
  -m, --mode MODE       Generation mode: random, smart, pattern, regex
  --regex PATTERN       Regex pattern for regex mode
  --pattern PATTERN     Type pattern for pattern mode (e.g., "UllnnU")
  -o, --output FILE     Output file (default: stdout)
  -f, --format FORMAT   Output format: text, json, csv, jsonl
  --hash ALGORITHM      Apply hash: md5, sha1, sha256, sha512, sha3_256,
                        sha3_512, blake2b, blake2s, base64, base64url
  --analyze-only        Only analyze, don't generate
  --show-stats          Show detailed statistics
  --show-patterns       Show inferred regex patterns
  --min-length N        Minimum word length to analyze
  --max-length N        Maximum word length to analyze
  --seed N              Random seed for reproducibility
  --allow-duplicates    Allow generating duplicates of input words
  -v, --verbose         Verbose output
  -q, --quiet           Quiet mode
```

## Examples

### Analyze Password Patterns

```bash
$ edap passwords.txt --analyze-only --show-stats

============================================================
EDAP Pattern Analysis Results
============================================================
Total words analyzed: 1000
Unique words: 987
Length range: 6 - 16
Charset size: 72

Length distribution:
    8: ######################### (312 words, 31.2%)
   10: ################## (223 words, 22.3%)
   12: ############# (156 words, 15.6%)

Character type frequency:
  UPPER   :   1245 (12.4%)
  LOWER   :   5678 (56.8%)
  DIGIT   :   2345 (23.5%)
  SYMBOL  :    732 (7.3%)
```

### Generate Hashed Wordlist

```bash
$ edap wordlist.txt -n 1000 -m smart --hash sha256 -o hashes.txt
```

### Export as JSON with Metadata

```bash
$ edap wordlist.txt -n 10 -f json

[
  "Password1!",
  "Admin2023",
  "User@1234",
  ...
]
```

### Reproducible Generation

```bash
# Same seed = same output
$ edap wordlist.txt -n 5 --seed 42
abc123
Def456
ghi789

$ edap wordlist.txt -n 5 --seed 42
abc123
Def456
ghi789
```

## How It Works

1. **Analysis Phase**: EDAP reads the input wordlist and builds statistical models:
   - Character frequency at each position (per word length)
   - Character type patterns (e.g., "Uppercase-lowercase-digit")
   - Co-occurrence relationships between characters

2. **Generation Phase**: Based on the learned models:
   - **Random**: Picks characters seen at each position randomly
   - **Smart**: Uses co-occurrence to pick compatible characters
   - **Pattern**: Ensures output matches observed type patterns
   - **Regex**: Generates strings matching the provided regex

3. **Output Phase**: Results can be hashed and exported in various formats

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy edap/

# Linting
ruff check edap/
```

## Project Structure

```
edap/
├── __init__.py          # Package exports
├── __main__.py          # Enables: python -m edap
├── models.py            # Data classes (CharType, PositionStats, etc.)
├── analyzer.py          # PatternAnalyzer
├── generators/
│   ├── __init__.py      # Generator exports
│   ├── base.py          # BaseGenerator abstract class
│   ├── random_gen.py    # RandomGenerator
│   ├── smart.py         # SmartGenerator
│   ├── pattern.py       # PatternGenerator
│   └── regex_gen.py     # RegexGenerator
├── regex_builder.py     # Regex pattern inference
├── exporters.py         # Output formatting and hashing
├── exceptions.py        # Custom exceptions
├── cli.py               # Command-line interface
├── ui.py                # Streamlit web UI
└── ui_runner.py         # UI launcher script
tests/
├── test_analyzer.py
├── test_generators.py
├── test_exporters.py
├── test_models.py
└── test_cli.py
```

## License

MIT License - see [LICENSE](license) file.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
