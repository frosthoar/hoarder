"""This module contains the HashNameFile class, which represents a file with a hash in its name."""

import enum
import logging
import os
import pathlib
import re
import typing

import hoarder.hash_file as hash_file

logger = logging.getLogger("hoarder.hash_name_file")

T = typing.TypeVar("T", bound="HashNameFile")

# CRC32 regex in filenames

class HashEnclosure(enum.Enum):
    """Enumeration of how a hash is stored in a file name."""
    SQUARE = "[]"
    PAREN = "()"

class HashNameFile(hash_file.HashFile):
    """This class contains information about a file that has a hash in its name."""

    _regexes: dict[HashEnclosure, re.Pattern[str]] = {
            enc: re.compile(
                    rf"""(?x)
                    ^(?P<stem>.+)
                    {re.escape(enc.value[0])}
                    (?P<crc>[0-9A-F]{{8}})
                    {re.escape(enc.value[1])}
                    (?P<suffix>\..+)$
                    """,
                    re.IGNORECASE
                )
            for enc in HashEnclosure
        }

    enc: HashEnclosure

    def __init__(
        self,
        path: pathlib.Path,
        files: set[hash_file.FileEntry] | None = None,
        enc: HashEnclosure = HashEnclosure.SQUARE
    ) -> None:
        super().__init__(path, files)
        self.enc = enc


    @classmethod
    def from_path(cls: typing.Type[T], path: pathlib.Path) -> T:
        """Create a HashNameFile object by reading information from a file name given its path."""
        files = []
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        logger.debug("Reading %s", path)
        crc = None
        algo = None
        for enc in HashEnclosure:
            match = cls._regexes[enc].match(path.name)
            if match:
                crc = bytes.fromhex(match.group("crc"))
                algo = hash_file.Algo.CRC32
                break
        if not crc:
            raise ValueError(f"No hash found in {path}")
        file_size = os.path.getsize(path)

        files.append(
            hash_file.FileEntry(
                pathlib.PurePath(path.name),
                file_size,
                False,
                crc,
                algo,
            )
        )

        return cls(path, files, enc)
