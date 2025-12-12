"""Tests for EDAP CLI."""

import pytest
import tempfile
from pathlib import Path

from edap.cli import create_parser, main


@pytest.fixture
def sample_wordlist():
    """Create a temporary wordlist file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('abc\n')
        f.write('def\n')
        f.write('ghi\n')
        f.write('ABC\n')
        f.write('DEF\n')
        f.write('123\n')
        filepath = Path(f.name)

    yield filepath

    filepath.unlink()


class TestCLIParser:
    """Tests for CLI argument parser."""

    def test_parser_creation(self):
        parser = create_parser()
        assert parser is not None

    def test_parser_no_input_no_ui(self, capsys):
        """Test that missing input without --ui shows help."""
        result = main([])

        assert result == 1
        captured = capsys.readouterr()
        assert "input file is required" in captured.out or "Error" in captured.out

    def test_parser_defaults(self, sample_wordlist):
        parser = create_parser()
        args = parser.parse_args([str(sample_wordlist)])

        assert args.count == 10
        assert args.mode == 'smart'
        assert args.format == 'text'
        assert args.output is None

    def test_parser_count(self, sample_wordlist):
        parser = create_parser()
        args = parser.parse_args([str(sample_wordlist), '-n', '50'])

        assert args.count == 50

    def test_parser_mode(self, sample_wordlist):
        parser = create_parser()

        for mode in ['random', 'smart', 'pattern', 'regex']:
            args = parser.parse_args([str(sample_wordlist), '-m', mode])
            assert args.mode == mode

    def test_parser_output(self, sample_wordlist):
        parser = create_parser()
        args = parser.parse_args([str(sample_wordlist), '-o', 'output.txt'])

        assert args.output == Path('output.txt')

    def test_parser_format(self, sample_wordlist):
        parser = create_parser()

        for fmt in ['text', 'json', 'csv', 'jsonl']:
            args = parser.parse_args([str(sample_wordlist), '-f', fmt])
            assert args.format == fmt

    def test_parser_hash(self, sample_wordlist):
        parser = create_parser()
        args = parser.parse_args([str(sample_wordlist), '--hash', 'sha256'])

        assert args.hash == 'sha256'

    def test_parser_analyze_only(self, sample_wordlist):
        parser = create_parser()
        args = parser.parse_args([str(sample_wordlist), '--analyze-only'])

        assert args.analyze_only is True

    def test_parser_length_filters(self, sample_wordlist):
        parser = create_parser()
        args = parser.parse_args([
            str(sample_wordlist),
            '--min-length', '2',
            '--max-length', '10',
        ])

        assert args.min_length == 2
        assert args.max_length == 10

    def test_parser_seed(self, sample_wordlist):
        parser = create_parser()
        args = parser.parse_args([str(sample_wordlist), '--seed', '42'])

        assert args.seed == 42


class TestCLIMain:
    """Tests for CLI main function."""

    def test_main_basic(self, sample_wordlist, capsys):
        result = main([
            str(sample_wordlist),
            '-n', '5',
            '--no-banner',
            '-q',
        ])

        assert result == 0

        captured = capsys.readouterr()
        lines = [l for l in captured.out.strip().split('\n') if l]
        assert len(lines) == 5

    def test_main_analyze_only(self, sample_wordlist, capsys):
        result = main([
            str(sample_wordlist),
            '--analyze-only',
            '--no-banner',
        ])

        assert result == 0

    def test_main_file_not_found(self, capsys):
        result = main([
            '/nonexistent/file.txt',
            '--no-banner',
            '-q',
        ])

        assert result == 1

    def test_main_with_output_file(self, sample_wordlist):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_path = Path(f.name)

        try:
            result = main([
                str(sample_wordlist),
                '-n', '5',
                '-o', str(output_path),
                '--no-banner',
                '-q',
            ])

            assert result == 0
            assert output_path.exists()

            content = output_path.read_text()
            lines = [l for l in content.strip().split('\n') if l]
            assert len(lines) == 5
        finally:
            output_path.unlink()

    def test_main_json_format(self, sample_wordlist, capsys):
        result = main([
            str(sample_wordlist),
            '-n', '3',
            '-f', 'json',
            '--no-banner',
            '-q',
        ])

        assert result == 0

        captured = capsys.readouterr()
        import json
        parsed = json.loads(captured.out)
        assert isinstance(parsed, list)
        assert len(parsed) == 3

    def test_main_with_hash(self, sample_wordlist, capsys):
        result = main([
            str(sample_wordlist),
            '-n', '1',
            '--hash', 'md5',
            '--no-banner',
            '-q',
            '--seed', '42',
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = captured.out.strip()
        # MD5 hashes are 32 hex characters
        assert len(output) == 32

    def test_main_random_mode(self, sample_wordlist, capsys):
        result = main([
            str(sample_wordlist),
            '-n', '5',
            '-m', 'random',
            '--no-banner',
            '-q',
            '--seed', '42',
        ])

        assert result == 0

    def test_main_pattern_mode(self, sample_wordlist, capsys):
        result = main([
            str(sample_wordlist),
            '-n', '5',
            '-m', 'pattern',
            '--no-banner',
            '-q',
            '--seed', '42',
        ])

        assert result == 0

    def test_main_show_stats(self, sample_wordlist, capsys):
        result = main([
            str(sample_wordlist),
            '--analyze-only',
            '--show-stats',
            '--no-banner',
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert 'Total words' in captured.out or 'Length' in captured.out

    def test_main_seed_reproducibility(self, sample_wordlist, capsys):
        # First run
        main([
            str(sample_wordlist),
            '-n', '5',
            '--seed', '12345',
            '--no-banner',
            '-q',
        ])
        captured1 = capsys.readouterr()

        # Second run with same seed
        main([
            str(sample_wordlist),
            '-n', '5',
            '--seed', '12345',
            '--no-banner',
            '-q',
        ])
        captured2 = capsys.readouterr()

        assert captured1.out == captured2.out
