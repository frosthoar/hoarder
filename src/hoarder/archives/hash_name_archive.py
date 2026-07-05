"""This module contains the HashNameArchive class, which represents a file with a hash in its name."""

import enum
import logging
import os
import pathlib
import re
import typing

from ..utils.path_utils import AnchoredPath
from .hash_archive import Algo, FileEntry, HashArchive

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override


logger = logging.getLogger("hoarder.archives.hash_name_file")

T = typing.TypeVar("T", bound="HashNameArchive")

# CRC32 regex in filenames


class HashEnclosure(enum.Enum):
    """Enumeration of how a hash is stored in a file name."""

    SQUARE = "[]"
    PAREN = "()"


class HashNameArchive(HashArchive):
    """This class contains information about a file that has a hash in its name."""

    # Regular expressions to match hash in file names
    # are now precompiled with re.IGNORECASE
    _regexes: dict[HashEnclosure, re.Pattern[str]] = {
        enc: re.compile(
            rf"""(?x)
                    ^(?P<stem>.+)
                    {re.escape(enc.value[0])}
                    (?P<crc>[0-9A-F]{{8}})
                    {re.escape(enc.value[1])}
                    (?P<suffix>\..+)$
                    """,
            re.IGNORECASE,
        )
        for enc in HashEnclosure
    }

    enc: HashEnclosure

    DELETABLE: typing.ClassVar[bool] = False

    def __init__(
        self,
        storage_path: pathlib.Path,
        relative_path: pathlib.PurePath,
        files: set[FileEntry] | None = None,
        enc: HashEnclosure = HashEnclosure.SQUARE,
    ) -> None:
        if files is not None:
            if len(files) != 1:
                raise ValueError("HashNameArchive must have exactly one file entry.")
            if next(iter(files)).is_dir:
                raise ValueError("HashNameArchive cannot have a directory entry.")
            if next(iter(files)).path.name != relative_path.name:
                raise ValueError(
                    f"HashNameArchive path {relative_path} does not match file entry {next(iter(files)).path}"
                )
        super().__init__(storage_path, relative_path, files)
        self.enc = enc

    @classmethod
    def _match_hash_in_name(cls, name: str) -> tuple[bytes, Algo, HashEnclosure] | None:
        """Check whether name contains a hash-in-name pattern.

        Returns (crc, algo, enclosure) if it matches, else None.
        """
        for enc in HashEnclosure:
            match = cls._regexes[enc].match(name)
            if match:
                return bytes.fromhex(match.group("crc")), Algo.CRC32, enc
        return None

    @classmethod
    @override
    def _from_path(
        cls: type[T],
        storage_path: pathlib.Path,
        relative_path: pathlib.PurePath,
    ) -> T:
        """Create a HashNameArchive object by reading information from a
        file name given its storage_path and relative_path.

        Args:
            storage_path: The storage directory path (explicitly set, not inferred)
            relative_path: The relative path from storage_path (as PurePath)
        """
        full_path = storage_path / relative_path
        if not full_path.is_file():
            raise FileNotFoundError(f"File not found: {full_path}")
        logger.debug("Reading %s", full_path)
        match = cls._match_hash_in_name(relative_path.name)
        if match is None:
            raise ValueError(f"Could not extract hash from {relative_path}")
        crc, algo, enc = match

        file_size = os.path.getsize(full_path)

        files = {
            FileEntry(
                pathlib.PurePath(relative_path.name),
                file_size,
                False,
                crc,
                algo,
            )
        }

        return cls(storage_path, relative_path, files, enc)

    @classmethod
    @override
    def discover(cls: type[T], scope: AnchoredPath) -> list[T]:
        """Find files with a hash-in-name pattern within scope."""
        search_path = scope.full_path
        candidates = (
            [search_path] if search_path.is_file() else list(search_path.iterdir())
        )
        results = []
        for p in candidates:
            if p.is_file() and cls._match_hash_in_name(p.name) is not None:
                relative = p.relative_to(scope.storage_path)
                results.append(cls.from_path(scope.storage_path, relative))
        return results
