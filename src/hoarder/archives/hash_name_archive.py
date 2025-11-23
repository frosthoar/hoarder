"""This module contains the HashNameArchive class, which represents a file with a hash in its name."""

import enum
import logging
import os
import pathlib
import re
import typing

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
        root: pathlib.Path,
        path: pathlib.PurePath,
        files: set[FileEntry] | None = None,
        enc: HashEnclosure = HashEnclosure.SQUARE,
    ) -> None:
        if files is not None:
            if len(files) != 1:
                raise ValueError("HashNameArchive must have exactly one file entry.")
            if next(iter(files)).is_dir:
                raise ValueError("HashNameArchive cannot have a directory entry.")
            if next(iter(files)).path.name != path.name:
                raise ValueError(
                    f"HashNameArchive path {path} does not match file entry {next(iter(files)).path}"
                )
        super().__init__(root, path, files)
        self.enc = enc

    @classmethod
    @override
    def from_path(cls: type[T], root: pathlib.Path, path: pathlib.PurePath) -> T:
        """Create a HashNameArchive object by reading information from a file name given its root and path.
        
        Args:
            root: The root directory path (explicitly set, not inferred)
            path: The relative path from root (as PurePath)
        """
        full_path = root / path
        if not full_path.is_file():
            raise FileNotFoundError(f"File not found: {full_path}")
        logger.debug("Reading %s", full_path)
        crc = None
        algo = None
        for enc in HashEnclosure:
            match = cls._regexes[enc].match(path.name)
            if match:
                crc = bytes.fromhex(match.group("crc"))
                algo = Algo.CRC32
                break
        else:
            raise ValueError(f"Could not extract hash from {path}")

        file_size = os.path.getsize(full_path)

        files = {
            FileEntry(
                pathlib.PurePath(path.name),
                file_size,
                False,
                crc,
                algo,
            )
        }

        return cls(root, path, files, enc)
