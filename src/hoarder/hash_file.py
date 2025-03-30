"""This module contains classes and functions to handle files (e.g. SFV, RAR, ...) containing hash information."""

import abc
import dataclasses
import datetime
import enum
import pathlib
import typing


class Algo(enum.IntEnum):
    """This class contains the possible hash algorithms."""

    CRC32 = 1
    MD5 = 2
    SHA1 = 3
    SHA256 = 4
    SHA512 = 5


@dataclasses.dataclass(slots=True)
class FileEntry:
    """This class contains information about a file, either on disk or as part of an archive."""

    path: pathlib.PurePath
    size: int | None
    is_dir: bool
    hash_value: bytes | None = None
    algo: Algo | None = None

    def __lt__(self, other: typing.Self) -> bool:
        return self.path < other.path


class HashFile(abc.ABC):
    """This class contains information about an hash file."""

    path: pathlib.Path
    files: typing.Sequence[FileEntry]

    def __init__(
        self, path: pathlib.Path, files: typing.Sequence[FileEntry] | None = None
    ) -> None:
        """Create a HashFile object by reading information from an hash file given its path."""
        self.files: typing.Sequence[FileEntry] = files or []
        self.path: pathlib.Path = path

    @classmethod
    @abc.abstractmethod
    def from_path(cls, path: pathlib.Path) -> HashFile:
        """Create a HashFile object by reading information from an hash file given its path."""

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, key: int) -> FileEntry:
        return self.files[key]

    def __iter__(self) -> typing.Iterator[FileEntry]:
        return iter(self.files)

    def __str__(self) -> str:
        placeholder = "-"
        maxlen_path = max(len(str(file.path)) for file in self)
        maxlen_size = max(len(str(file.size or placeholder)) for file in self)
        maxlen_hash = 8 if any(file.hash_value for file in self) else 0
        maxlen_algo = 5 if any(file.algo for file in self) else 0
        class_name = self.__class__.__name__
        ret = f"{class_name}: {self.path}\n"
        printable_attributes = [
            a
            for a in dir(self)
            if not a.startswith("_")
            and not callable(getattr(self, a))
            and a not in ["files", "path"]
        ]
        for attr in printable_attributes:
            ret += f"  {attr}: {getattr(self, attr)}\n"
        for file in self:
            hash_str = file.hash_value.hex() if file.hash_value else placeholder
            algo_str = file.algo.name if file.algo else placeholder
            ret += (
                f"  {str(file.path):<{maxlen_path}}  {'D' if file.is_dir else 'F':1} "
                f"{file.size or placeholder:>{maxlen_size}} {hash_str:<{maxlen_hash}} {algo_str:<{maxlen_algo}}\n"
            )
        return ret
