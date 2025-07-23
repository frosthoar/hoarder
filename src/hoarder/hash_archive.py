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
    info: str | None = None

    def __lt__(self: Self, other: Self) -> bool:
        return self.path < other.path

    def __hash__(self: Self) -> int:
        return hash(self.path)


T = typing.TypeVar("T", bound="HashArchive")


class HashArchive(abc.ABC):
    """This class contains information about an hash file."""

    path: pathlib.Path
    files: set[FileEntry]
    is_deleted: bool
    info: str | None = None

    # Indicates whether the archive file itself (e.g., .sfv, .rar) can safely be deleted after processing.
    # Most archives are deletable without consequence, except for special cases like HashNameArchive,
    # where the archive is essentially the file itself and must not be deleted.
    DELETABLE: typing.ClassVar[bool] = True

    def __init__(self, path: pathlib.Path, files: set[FileEntry] | None = None) -> None:
        """Create a HashArchive object by reading information from an hash file given its path."""
        self.files: set[FileEntry] = files or set()
        self.path: pathlib.Path = path
        self.is_deleted: bool = True

    @classmethod
    @abc.abstractmethod
    def from_path(cls: typing.Type[T], path: pathlib.Path) -> T:
        """Create a HashArchive object by reading information from an hash file given its path."""

    def __len__(self) -> int:
        return len(self.files)

    def __iter__(self) -> typing.Iterator[FileEntry]:
        return iter(self.files)

    def _printable_attributes(self):
        return [
            a
            for a in dir(self)
            if not a.startswith("_")
            and not callable(getattr(self, a))
            and not hasattr(type(self), a)
        ]

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        d: dict[str, str | list[str]] = {}
        d["class_name"] = class_name
        for attr in self._printable_attributes():
            d[attr] = getattr(self, attr)
        d["files"] = sorted([repr(f) for f in self.files])
        return str(dict(sorted(d.items())))

    def pretty_print(self) -> str:
        placeholder = "-"
        maxlen_path = max([0] + [len(str(file.path)) for file in self])
        maxlen_size = max([0] + [len(str(file.size or placeholder)) for file in self])
        maxlen_hash = 8 if any(file.hash_value for file in self) else 0
        maxlen_algo = 5 if any(file.algo for file in self) else 0
        class_name = self.__class__.__name__
        ret = f"{class_name}: {self.path}\n"

        cols = 0
        header_fields = self._printable_attributes()
        header_fields.remove("files")
        header_fields.remove("path")

        for attr in header_fields:
            line = f"  {attr}: {getattr(self, attr)}"
            ret += line + "\n"
            cols = max(cols, len(line))

        ret += "=" * cols + "\n"
        for file in sorted(self):
            hash_str = file.hash_value.hex() if file.hash_value else placeholder
            algo_str = file.algo.name if file.algo else placeholder
            ret += (
                f"  {str(file.path):<{maxlen_path}}  {'D' if file.is_dir else 'F':1} "
                f"{file.size or placeholder:>{maxlen_size}} {hash_str:<{maxlen_hash}} {algo_str:<{maxlen_algo}}\n"
            )
        return ret
