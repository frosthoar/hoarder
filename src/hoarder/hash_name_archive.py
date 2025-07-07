"""This module contains the HashNameArchive class, which represents a file with a hash in its name."""

import enum
import logging
import os
import pathlib
import re
import typing

import hoarder.hash_archive as hash_archive

logger = logging.getLogger("hoarder.hash_name_file")

T = typing.TypeVar("T", bound="HashNameArchive")

# CRC32 regex in filenames


class HashEnclosure(enum.Enum):
    """Enumeration of how a hash is stored in a file name."""

    SQUARE = "[]"
    PAREN = "()"


class HashNameArchive(hash_archive.HashArchive):
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
        path: pathlib.Path,
        files: set[hash_archive.FileEntry] | None = None,
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
        super().__init__(path, files)
        self.enc = enc

    @classmethod
    def from_path(cls: type[T], path: pathlib.Path) -> T:
        """Create a HashNameArchive object by reading information from a file name given its path."""
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        logger.debug("Reading %s", path)
        crc = None
        algo = None
        for enc in HashEnclosure:
            match = cls._regexes[enc].match(path.name)
            if match:
                crc = bytes.fromhex(match.group("crc"))
                algo = hash_archive.Algo.CRC32
                break
        else:
            raise ValueError(f"Could not extract hash from {path}")

        file_size = os.path.getsize(path)

        files = {
            hash_archive.FileEntry(
                pathlib.PurePath(path.name),
                file_size,
                False,
                crc,
                algo,
            )
        }

        return cls(path, files, enc)
