"""Tests for EDAP exporters."""

import json
import pytest
import tempfile
from pathlib import Path

from edap.exporters import (
    HashAlgorithm,
    Hasher,
    OutputFormat,
    TextExporter,
    JsonExporter,
    CsvExporter,
    ResultExporter,
)


class TestHasher:
    """Tests for Hasher class."""

    def test_md5_hash(self):
        hasher = Hasher(HashAlgorithm.MD5)
        result = hasher.hash('test')

        assert result == '098f6bcd4621d373cade4e832627b4f6'

    def test_sha256_hash(self):
        hasher = Hasher(HashAlgorithm.SHA256)
        result = hasher.hash('test')

        assert result == '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'

    def test_sha512_hash(self):
        hasher = Hasher(HashAlgorithm.SHA512)
        result = hasher.hash('test')

        assert len(result) == 128  # SHA512 produces 128 hex chars

    def test_base64_encode(self):
        hasher = Hasher(HashAlgorithm.BASE64)
        result = hasher.hash('test')

        assert result == 'dGVzdA=='

    def test_base64url_encode(self):
        hasher = Hasher(HashAlgorithm.BASE64URL)
        result = hasher.hash('test+/')

        # URL-safe base64 uses - and _ instead of + and /
        assert '+' not in result
        assert '/' not in result

    def test_hash_many(self):
        hasher = Hasher(HashAlgorithm.MD5)
        results = hasher.hash_many(['a', 'b', 'c'])

        assert len(results) == 3
        assert results[0] == '0cc175b9c0f1b6a831c399e269772661'

    def test_hash_iter(self):
        hasher = Hasher(HashAlgorithm.MD5)
        results = list(hasher.hash_iter(iter(['a', 'b', 'c'])))

        assert len(results) == 3

    def test_algorithm_from_string(self):
        hasher = Hasher('sha256')
        result = hasher.hash('test')

        assert len(result) == 64

    def test_blake2b_hash(self):
        hasher = Hasher(HashAlgorithm.BLAKE2B)
        result = hasher.hash('test')

        assert len(result) == 128  # BLAKE2b default is 64 bytes = 128 hex

    def test_sha3_256_hash(self):
        hasher = Hasher(HashAlgorithm.SHA3_256)
        result = hasher.hash('test')

        assert len(result) == 64


class TestTextExporter:
    """Tests for TextExporter."""

    def test_export_basic(self):
        exporter = TextExporter()
        result = exporter.export(['a', 'b', 'c'])

        assert result == 'a\nb\nc'

    def test_export_custom_separator(self):
        exporter = TextExporter(separator=', ')
        result = exporter.export(['a', 'b', 'c'])

        assert result == 'a, b, c'

    def test_export_to_file(self):
        exporter = TextExporter()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            filepath = Path(f.name)

        try:
            exporter.export_to_file(['a', 'b', 'c'], filepath)

            content = filepath.read_text()
            assert content == 'a\nb\nc\n'
        finally:
            filepath.unlink()


class TestJsonExporter:
    """Tests for JsonExporter."""

    def test_export_basic(self):
        exporter = JsonExporter()
        result = exporter.export(['a', 'b', 'c'])

        parsed = json.loads(result)
        assert parsed == ['a', 'b', 'c']

    def test_export_with_stats(self):
        exporter = JsonExporter()
        result = exporter.export(['a', 'b', 'c'], include_stats=True)

        parsed = json.loads(result)
        assert parsed['count'] == 3
        assert parsed['items'] == ['a', 'b', 'c']

    def test_export_custom_indent(self):
        exporter = JsonExporter(indent=4)
        result = exporter.export(['a'])

        # With indent=4, there should be 4 spaces
        assert '    ' in result


class TestCsvExporter:
    """Tests for CsvExporter."""

    def test_export_basic(self):
        exporter = CsvExporter()
        result = exporter.export(['a', 'b', 'c'])

        lines = [l.strip() for l in result.strip().split('\n')]
        assert lines[0] == 'value'
        assert lines[1] == 'a'
        assert lines[2] == 'b'
        assert lines[3] == 'c'

    def test_export_with_index(self):
        exporter = CsvExporter(include_index=True)
        result = exporter.export(['a', 'b'])

        lines = [l.strip() for l in result.strip().split('\n')]
        assert lines[0] == 'index,value'
        assert lines[1] == '0,a'
        assert lines[2] == '1,b'

    def test_export_with_hash(self):
        exporter = CsvExporter(include_hash=True, hash_algorithm='md5')
        result = exporter.export(['test'])

        lines = result.strip().split('\n')
        assert 'md5_hash' in lines[0]
        assert '098f6bcd4621d373cade4e832627b4f6' in lines[1]


class TestResultExporter:
    """Tests for ResultExporter."""

    def test_export_text(self):
        exporter = ResultExporter(format=OutputFormat.TEXT)
        result = exporter.export(['a', 'b', 'c'])

        assert result == 'a\nb\nc'

    def test_export_json(self):
        exporter = ResultExporter(format=OutputFormat.JSON)
        result = exporter.export(['a', 'b', 'c'])

        parsed = json.loads(result)
        assert parsed == ['a', 'b', 'c']

    def test_export_with_hash(self):
        exporter = ResultExporter(
            format=OutputFormat.TEXT,
            hash_algorithm=HashAlgorithm.MD5,
        )
        result = exporter.export(['test'])

        assert result == '098f6bcd4621d373cade4e832627b4f6'

    def test_export_format_from_string(self):
        exporter = ResultExporter(format='json')
        result = exporter.export(['a'])

        parsed = json.loads(result)
        assert parsed == ['a']

    def test_export_to_file(self):
        exporter = ResultExporter(format=OutputFormat.TEXT)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            filepath = Path(f.name)

        try:
            exporter.export_to_file(['a', 'b'], filepath)

            content = filepath.read_text()
            assert 'a\n' in content
            assert 'b\n' in content
        finally:
            filepath.unlink()


class TestHashAlgorithm:
    """Tests for HashAlgorithm enum."""

    def test_list_algorithms(self):
        algorithms = HashAlgorithm.list_algorithms()

        assert 'md5' in algorithms
        assert 'sha256' in algorithms
        assert 'base64' in algorithms
        assert len(algorithms) == 12
