"""Abstract base class for RAR archive implementations."""

import abc
import pathlib
import typing
from abc import abstractmethod

from .hash_archive import FileEntry, HashArchive
from .rar_path import RarScheme

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

T = typing.TypeVar("T", bound="RarArchive")


class RarArchive(HashArchive, abc.ABC):
    """Abstract base class for RAR archive implementations."""

    password: str | None
    scheme: RarScheme | None
    version: str | None
    n_volumes: int | None

    def __init__(
        self,
        storage_path: pathlib.Path,
        path: pathlib.PurePath,
        files: set[FileEntry] | None = None,
        password: str | None = None,
        version: str | None = None,
        scheme: RarScheme | None = None,
        n_volumes: int | None = None,
    ) -> None:
        super().__init__(storage_path, path, files)
        self.password = password
        self.scheme = scheme
        self.n_volumes = n_volumes
        self.version = version

    def get_volumes(self) -> list[pathlib.Path]:
        """Get a list of all volumes of the same RAR archive."""
        if self.n_volumes is None:
            raise ValueError(f"Volumes not set for {self.full_path}")
        if self.n_volumes == 0:
            raise ValueError(f"Invalid number of volumes for {self.full_path}")
        if self.n_volumes == 1:
            return [self.full_path]
        if self.scheme == RarScheme.DOT_RNN:
            return [self.storage_path / f"{self.path.stem}.rar"] + [
                self.storage_path / f"{self.path.stem}.r{index:02d}"
                for index in range(0, self.n_volumes - 1)
            ]
        if self.scheme == RarScheme.PART_N:
            stem = self.path.stem.split(".part")[0]
            volume_list = [
                self.storage_path / f"{stem}.part{index}.rar"
                for index in range(1, self.n_volumes + 1)
            ]
            for p in volume_list:
                if not p.exists():
                    raise FileNotFoundError(f"Volume {p} not found")
            return volume_list
        raise ValueError(
            f"Ambiguous RAR file {self.full_path} with {self.n_volumes} volumes"
        )

    @property
    def hash_values_exist(self) -> bool:
        """Check if *all* files already have hash values."""
        return all(file.hash_value for file in self if not file.is_dir)

    @abstractmethod
    def update_hash_values(self) -> None:
        """Update the hash values of all files in the archive."""

    @abstractmethod
    def read_file(self, path: pathlib.PurePath) -> bytes:
        """Extract and return the raw bytes of a file within the archive."""
