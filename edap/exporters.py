"""
Export functionality for EDAP.
Handles hashing, file output, and various export formats.
"""

import base64
import hashlib
import json
import csv
import io
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Union


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA224 = "sha224"
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    BASE64 = "base64"
    BASE64URL = "base64url"

    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List all available algorithms."""
        return [alg.value for alg in cls]


class Hasher:
    """
    Hash strings using various algorithms.

    Note: MD5 and SHA1 are cryptographically broken and should not be
    used for security purposes. They are included for compatibility
    with legacy systems only.
    """

    def __init__(self, algorithm: Union[HashAlgorithm, str]):
        """
        Initialize hasher with algorithm.

        Args:
            algorithm: Hash algorithm to use
        """
        if isinstance(algorithm, str):
            algorithm = HashAlgorithm(algorithm.lower())

        self.algorithm = algorithm
        self._hash_func = self._get_hash_function()

    def _get_hash_function(self) -> Callable[[bytes], str]:
        """Get the hash function for the algorithm."""
        alg = self.algorithm

        if alg == HashAlgorithm.MD5:
            return lambda b: hashlib.md5(b).hexdigest()
        elif alg == HashAlgorithm.SHA1:
            return lambda b: hashlib.sha1(b).hexdigest()
        elif alg == HashAlgorithm.SHA224:
            return lambda b: hashlib.sha224(b).hexdigest()
        elif alg == HashAlgorithm.SHA256:
            return lambda b: hashlib.sha256(b).hexdigest()
        elif alg == HashAlgorithm.SHA384:
            return lambda b: hashlib.sha384(b).hexdigest()
        elif alg == HashAlgorithm.SHA512:
            return lambda b: hashlib.sha512(b).hexdigest()
        elif alg == HashAlgorithm.SHA3_256:
            return lambda b: hashlib.sha3_256(b).hexdigest()
        elif alg == HashAlgorithm.SHA3_512:
            return lambda b: hashlib.sha3_512(b).hexdigest()
        elif alg == HashAlgorithm.BLAKE2B:
            return lambda b: hashlib.blake2b(b).hexdigest()
        elif alg == HashAlgorithm.BLAKE2S:
            return lambda b: hashlib.blake2s(b).hexdigest()
        elif alg == HashAlgorithm.BASE64:
            return lambda b: base64.b64encode(b).decode('ascii')
        elif alg == HashAlgorithm.BASE64URL:
            return lambda b: base64.urlsafe_b64encode(b).decode('ascii')
        else:
            raise ValueError(f"Unknown algorithm: {alg}")

    def hash(self, text: str, encoding: str = 'utf-8') -> str:
        """
        Hash a single string.

        Args:
            text: String to hash
            encoding: Text encoding

        Returns:
            Hash/encoded string
        """
        return self._hash_func(text.encode(encoding))

    def hash_many(
        self,
        texts: List[str],
        encoding: str = 'utf-8',
    ) -> List[str]:
        """
        Hash multiple strings.

        Args:
            texts: Strings to hash
            encoding: Text encoding

        Returns:
            List of hashed strings
        """
        return [self.hash(t, encoding) for t in texts]

    def hash_iter(
        self,
        texts: Iterator[str],
        encoding: str = 'utf-8',
    ) -> Iterator[str]:
        """
        Hash strings from an iterator.

        Args:
            texts: Iterator of strings
            encoding: Text encoding

        Yields:
            Hashed strings
        """
        for text in texts:
            yield self.hash(text, encoding)


class OutputFormat(Enum):
    """Output formats for export."""
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"  # JSON Lines


class Exporter(ABC):
    """Abstract base class for exporters."""

    @abstractmethod
    def export(self, data: List[str], **kwargs) -> str:
        """Export data to string."""
        pass

    @abstractmethod
    def export_to_file(
        self,
        data: List[str],
        filepath: Union[str, Path],
        **kwargs,
    ) -> None:
        """Export data to file."""
        pass


class TextExporter(Exporter):
    """Export as plain text (one item per line)."""

    def __init__(self, separator: str = '\n'):
        self.separator = separator

    def export(self, data: List[str], **kwargs) -> str:
        return self.separator.join(data)

    def export_to_file(
        self,
        data: List[str],
        filepath: Union[str, Path],
        encoding: str = 'utf-8',
        **kwargs,
    ) -> None:
        filepath = Path(filepath)
        with open(filepath, 'w', encoding=encoding) as f:
            for item in data:
                f.write(item + '\n')


class JsonExporter(Exporter):
    """Export as JSON."""

    def __init__(self, indent: int = 2):
        self.indent = indent

    def export(
        self,
        data: List[str],
        include_stats: bool = False,
        **kwargs,
    ) -> str:
        if include_stats:
            output = {
                'count': len(data),
                'items': data,
            }
            return json.dumps(output, indent=self.indent)
        return json.dumps(data, indent=self.indent)

    def export_to_file(
        self,
        data: List[str],
        filepath: Union[str, Path],
        encoding: str = 'utf-8',
        **kwargs,
    ) -> None:
        filepath = Path(filepath)
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(self.export(data, **kwargs))


class CsvExporter(Exporter):
    """Export as CSV."""

    def __init__(
        self,
        include_index: bool = False,
        include_hash: bool = False,
        hash_algorithm: Optional[str] = None,
    ):
        self.include_index = include_index
        self.include_hash = include_hash
        self.hash_algorithm = hash_algorithm

    def export(self, data: List[str], **kwargs) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        header = ['value']
        if self.include_index:
            header.insert(0, 'index')
        if self.include_hash and self.hash_algorithm:
            header.append(f'{self.hash_algorithm}_hash')

        writer.writerow(header)

        # Write data
        hasher = None
        if self.include_hash and self.hash_algorithm:
            hasher = Hasher(self.hash_algorithm)

        for i, item in enumerate(data):
            row = [item]
            if self.include_index:
                row.insert(0, i)
            if hasher:
                row.append(hasher.hash(item))
            writer.writerow(row)

        return output.getvalue()

    def export_to_file(
        self,
        data: List[str],
        filepath: Union[str, Path],
        encoding: str = 'utf-8',
        **kwargs,
    ) -> None:
        filepath = Path(filepath)
        with open(filepath, 'w', encoding=encoding, newline='') as f:
            f.write(self.export(data, **kwargs))


class JsonLinesExporter(Exporter):
    """Export as JSON Lines (one JSON object per line)."""

    def export(
        self,
        data: List[str],
        include_metadata: bool = False,
        **kwargs,
    ) -> str:
        lines = []
        for i, item in enumerate(data):
            if include_metadata:
                obj = {'index': i, 'value': item, 'length': len(item)}
            else:
                obj = {'value': item}
            lines.append(json.dumps(obj))
        return '\n'.join(lines)

    def export_to_file(
        self,
        data: List[str],
        filepath: Union[str, Path],
        encoding: str = 'utf-8',
        **kwargs,
    ) -> None:
        filepath = Path(filepath)
        with open(filepath, 'w', encoding=encoding) as f:
            for i, item in enumerate(data):
                if kwargs.get('include_metadata'):
                    obj = {'index': i, 'value': item, 'length': len(item)}
                else:
                    obj = {'value': item}
                f.write(json.dumps(obj) + '\n')


class ResultExporter:
    """
    High-level exporter for EDAP results.

    Combines generation results with optional hashing and formatting.
    """

    def __init__(
        self,
        format: Union[OutputFormat, str] = OutputFormat.TEXT,
        hash_algorithm: Optional[Union[HashAlgorithm, str]] = None,
    ):
        """
        Initialize result exporter.

        Args:
            format: Output format
            hash_algorithm: Optional hash algorithm to apply
        """
        if isinstance(format, str):
            format = OutputFormat(format.lower())

        self.format = format
        self.hasher = Hasher(hash_algorithm) if hash_algorithm else None

        # Create appropriate exporter
        if format == OutputFormat.TEXT:
            self._exporter = TextExporter()
        elif format == OutputFormat.JSON:
            self._exporter = JsonExporter()
        elif format == OutputFormat.CSV:
            self._exporter = CsvExporter(
                include_hash=hash_algorithm is not None,
                hash_algorithm=hash_algorithm.value if isinstance(hash_algorithm, HashAlgorithm) else hash_algorithm,
            )
        elif format == OutputFormat.JSONL:
            self._exporter = JsonLinesExporter()
        else:
            raise ValueError(f"Unknown format: {format}")

    def export(
        self,
        data: List[str],
        apply_hash: bool = True,
        **kwargs,
    ) -> str:
        """
        Export data to string.

        Args:
            data: List of generated strings
            apply_hash: Whether to apply hashing (if configured)
            **kwargs: Additional format-specific options
        """
        if apply_hash and self.hasher:
            data = self.hasher.hash_many(data)

        return self._exporter.export(data, **kwargs)

    def export_to_file(
        self,
        data: List[str],
        filepath: Union[str, Path],
        apply_hash: bool = True,
        **kwargs,
    ) -> None:
        """
        Export data to file.

        Args:
            data: List of generated strings
            filepath: Output file path
            apply_hash: Whether to apply hashing (if configured)
            **kwargs: Additional format-specific options
        """
        if apply_hash and self.hasher:
            data = self.hasher.hash_many(data)

        self._exporter.export_to_file(data, filepath, **kwargs)

    def export_with_original(
        self,
        original: List[str],
        generated: List[str],
        filepath: Union[str, Path],
    ) -> None:
        """
        Export both original and generated strings with hashes.

        Useful for comparison and analysis.
        """
        filepath = Path(filepath)

        with open(filepath, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)

            header = ['type', 'value']
            if self.hasher:
                header.append('hash')

            writer.writerow(header)

            for item in original:
                row = ['original', item]
                if self.hasher:
                    row.append(self.hasher.hash(item))
                writer.writerow(row)

            for item in generated:
                row = ['generated', item]
                if self.hasher:
                    row.append(self.hasher.hash(item))
                writer.writerow(row)
