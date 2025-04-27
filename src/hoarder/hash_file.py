"""This module contains classes and functions to handle files (e.g. SFV, RAR, ...) containing hash information."""

import abc
import dataclasses
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


Self = typing.TypeVar("Self", bound="FileEntry")


@dataclasses.dataclass(slots=True, eq=True)
class FileEntry:
    """
    Represents a file in a hash-based collection (SFV, RAR, etc.).

    Identity and hashing are based on the file's relative path.
    DO NOT mix FileEntry instances from different containers unless
    their paths are guaranteed to be unique.

    This class is mutable to allow gradual enrichment (e.g. adding hashes).
    """

    path: pathlib.PurePath
    size: int | None
    is_dir: bool
    hash_value: bytes | None = None
    algo: Algo | None = None

    def __lt__(self: Self, other: Self) -> bool:
        return self.path < other.path

    def __hash__(self: Self) -> int:
        return hash(self.path)


T = typing.TypeVar("T", bound="HashFile")


class HashFile(abc.ABC):
    """This class contains information about an hash file."""

    path: pathlib.Path
    files: set[FileEntry]
    present: bool

    DELETABLE: ClassVar[bool] = True

    def __init__(self, path: pathlib.Path, files: set[FileEntry] | None = None) -> None:
        """Create a HashFile object by reading information from an hash file given its path."""
        self.files: set[FileEntry] = files or set()
        self.path: pathlib.Path = path
        self.present: bool = True

    @classmethod
    @abc.abstractmethod
    def from_path(cls: typing.Type[T], path: pathlib.Path) -> T:
        """Create a HashFile object by reading information from an hash file given its path."""

    def __len__(self) -> int:
        return len(self.files)

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
