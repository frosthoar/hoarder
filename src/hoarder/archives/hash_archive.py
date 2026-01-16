"""This module contains classes and functions to handle files (e.g. SFV, RAR, ...) containing hash information."""

import abc
import collections.abc
import dataclasses
import enum
import pathlib
import typing
from abc import abstractmethod

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

from hoarder.utils.presentation import PresentationSpec, ScalarValue


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

    @override
    def __hash__(self) -> int:
        return hash(self.path)


T = typing.TypeVar("T", bound="HashArchive")


class HashArchive(abc.ABC):
    """This class contains information about an hash file."""

    storage_path: pathlib.Path
    path: pathlib.PurePath
    files: set[FileEntry]
    is_deleted: bool
    info: str | None = None

    # Indicates whether the archive file itself (e.g., .sfv, .rar) can safely be deleted after processing.
    # Most archives are deletable without consequence, except for special cases like HashNameArchive,
    # where the archive is essentially the file itself and must not be deleted.
    DELETABLE: typing.ClassVar[bool] = True

    def __init__(
        self,
        storage_path: pathlib.Path,
        path: pathlib.PurePath,
        files: set[FileEntry] | None = None,
    ) -> None:
        """Create a HashArchive object.

        Args:
            storage_path: The storage directory path (explicitly set, not inferred)
            path: The relative path from storage_path (as PurePath)
            files: Optional set of FileEntry objects
        """
        self.files = files or set()
        self.storage_path = storage_path.resolve()
        self.path = path
        self.is_deleted = True

    @property
    def full_path(self) -> pathlib.Path:
        """Calculate the full path by combining storage_path and path."""
        return self.storage_path / self.path

    @classmethod
    def from_path(
        cls: typing.Type[T],
        storage_path: str | pathlib.Path,
        path: str | pathlib.PurePath,
        **kwargs,
    ) -> T:
        """Create a HashArchive object by reading information from an hash file given its storage_path and path.

        Args:
            storage_path: The storage directory path (explicitly set, not inferred)
            path: The relative path from storage_path
        """
        _storage_path: pathlib.Path = pathlib.Path(storage_path)
        _path: pathlib.PurePath = pathlib.PurePath(path)

        full_path = _storage_path / _path
        if not full_path.is_file():
            raise FileNotFoundError(f"{full_path} does not exist")

        return cls._from_path(_storage_path, _path, **kwargs)

    @classmethod
    @abstractmethod
    def _from_path(
        cls: typing.Type[T], storage_path: pathlib.Path, path: pathlib.PurePath
    ) -> T:
        """Create a HashArchive object by reading information from an hash file given its storage_path and path.

        Args:
            storage_path: The storage directory path (explicitly set, not inferred)
            path: The relative path from storage_path (as PurePath)
        """

    def __len__(self) -> int:
        return len(self.files)

    def __iter__(self) -> collections.abc.Iterator[FileEntry]:
        return iter(self.files)

    def _printable_attributes(self):
        return [
            a
            for a in dir(self)
            if not a.startswith("_")
            and not callable(getattr(self, a))
            and not hasattr(type(self), a)
        ]

    @override
    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        d: dict[str, str | list[str]] = {}
        d["class_name"] = class_name
        for attr in self._printable_attributes():
            d[attr] = getattr(self, attr)
        d["files"] = sorted([repr(f) for f in self.files])
        return str(dict(sorted(d.items())))

    def to_presentation(self) -> PresentationSpec:
        """Convert this archive to a presentation specification.

        Returns:
            A PresentationSpec with archive metadata as scalars and files as collection rows.
        """
        # Build scalar metadata
        scalar: dict[str, ScalarValue] = {
            "type": self.__class__.__name__,
            "path": str(self.full_path),
        }
        header_fields = self._printable_attributes()
        excluded_fields = {"files", "path", "storage_path"}
        for attr in filter(lambda a: a not in excluded_fields, header_fields):
            scalar[attr] = getattr(self, attr)

        # Build collection rows for files
        collection: list[dict[str, ScalarValue]] = []
        for file in sorted(self):
            row: dict[str, ScalarValue] = {
                "path": str(file.path),
                "type": "D" if file.is_dir else "F",
                "size": file.size,
                "hash": file.hash_value.hex() if file.hash_value else None,
                "algo": file.algo.name if file.algo else None,
            }
            collection.append(row)

        return PresentationSpec(scalar=scalar, collection=collection)
