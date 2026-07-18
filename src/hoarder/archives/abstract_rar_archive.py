"""Abstract base class for RAR archive implementations."""

import abc
import logging
import pathlib
import typing
from abc import abstractmethod

from ..utils.path_utils import AnchoredPath
from .hash_archive import FileEntry, HashArchive
from .rar_path import PART_N_PAT, RarScheme, find_rar_files, locate_main_volume

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.archives.abstract_rar_archive")

T = typing.TypeVar("T", bound="AbstractRarArchive")


class RarArchiveError(Exception):
    """Raised on RAR processing failures, regardless of backend.

    Backend implementations must catch their own library-specific
    exceptions (subprocess errors, rarfile.Error, ...) and re-raise as
    this type, so callers never need to know which backend is in use.
    """


class RarPasswordError(RarArchiveError):
    """Raised when an archive requires a password and the one supplied
    (including none at all) does not work.

    Callers driving a "try candidate passwords" loop should catch this
    specifically and move on to the next candidate; a plain
    RarArchiveError means the archive itself is broken and retrying with
    a different password will not help.
    """


class AbstractRarArchive(HashArchive, abc.ABC):
    """Abstract base class for RAR archive implementations.

    Backend implementations (Rar7zArchive, RarfileRarArchive) must be
    behaviorally interchangeable. Code outside this package should not
    reference them directly - use RarArchive (rar_archive.py) instead,
    which names the currently preferred backend.
    """

    password: str | None
    scheme: RarScheme | None
    version: str | None
    n_volumes: int | None
    part_n_padding: int | None
    requires_password: bool

    def __init__(
        self,
        storage_path: pathlib.Path,
        relative_path: pathlib.PurePath,
        files: set[FileEntry] | None = None,
        password: str | None = None,
        version: str | None = None,
        scheme: RarScheme | None = None,
        n_volumes: int | None = None,
        part_n_padding: int | None = None,
        requires_password: bool = False,
    ) -> None:
        if (
            scheme == RarScheme.PART_N
            and n_volumes is not None
            and part_n_padding is not None
            and n_volumes >= 10**part_n_padding
        ):
            raise ValueError(
                f"part_n_padding={part_n_padding} cannot represent "
                f"n_volumes={n_volumes}"
            )
        super().__init__(storage_path, relative_path, files)
        self.password = password
        self.scheme = scheme
        self.n_volumes = n_volumes
        self.version = version
        self.part_n_padding = part_n_padding
        self.requires_password = requires_password

    def get_volumes(self) -> list[pathlib.Path]:
        """Get a list of all volumes of the same RAR archive."""
        if self.n_volumes is None:
            raise ValueError(f"Volumes not set for {self.full_path}")
        if self.n_volumes == 0:
            raise ValueError(f"Invalid number of volumes for {self.full_path}")
        if self.n_volumes == 1:
            return [self.full_path]
        volume_dir = self.full_path.parent
        if self.scheme == RarScheme.DOT_RNN:
            stem = self.anchor.relative_path.stem
            return [volume_dir / f"{stem}.rar"] + [
                volume_dir / f"{stem}.r{index:02d}"
                for index in range(0, self.n_volumes - 1)
            ]
        if self.scheme == RarScheme.PART_N:
            if self.part_n_padding is None:
                raise ValueError(f"part_n_padding not set for {self.full_path}")
            match = PART_N_PAT.match(self.anchor.relative_path.name)
            if match is None:
                raise ValueError(
                    f"{self.anchor.relative_path.name} does not match the "
                    "PART_N naming pattern"
                )
            stem = match["stem"]
            volume_list = [
                volume_dir / f"{stem}.part{index:0{self.part_n_padding}d}.rar"
                for index in range(1, self.n_volumes + 1)
            ]
            for p in volume_list:
                if not p.exists():
                    raise FileNotFoundError(f"Volume {p} not found")
            return volume_list
        raise ValueError(
            f"Ambiguous RAR file {self.full_path} with {self.n_volumes} volumes"
        )

    @classmethod
    @override
    def discover(cls: typing.Type[T], scope: AnchoredPath) -> list[T]:
        """Find RAR archives within scope."""
        search_path = scope.full_path
        if search_path.is_file():
            if locate_main_volume(scope) is None:
                # Doesn't match any RAR naming pattern - not an error, just
                # not a match for this archive type. Checked directly instead
                # of via from_path so a common non-match doesn't cost a 7z/
                # rarfile invocation just to be discarded.
                return []
            try:
                return [cls.from_path(scope.storage_path, scope.relative_path)]
            except RarPasswordError:
                return [
                    cls._password_required_stub(
                        scope.storage_path, scope.relative_path
                    )
                ]
        results = []
        for _scheme, volumes in find_rar_files(search_path).values():
            first_volume = volumes[0]
            relative = first_volume.relative_to(scope.storage_path)
            try:
                results.append(cls.from_path(scope.storage_path, relative))
            except RarPasswordError:
                # Expected when scanning a whole directory blindly without
                # knowing passwords upfront. Record it anyway (instead of
                # skipping) so it shows up as "encrypted, no working
                # password" rather than silently vanishing from results.
                logger.warning(
                    "Archive %s requires a password; recording without contents",
                    first_volume,
                )
                results.append(
                    cls._password_required_stub(scope.storage_path, relative)
                )
            except RarArchiveError as exc:
                # e.g. corrupt archive - expected when scanning a whole
                # directory blindly; skip it, don't abort discovering others.
                logger.warning(
                    "Skipping unreadable RAR archive %s: %s", first_volume, exc
                )
        return results

    @classmethod
    def _password_required_stub(
        cls: typing.Type[T],
        storage_path: pathlib.Path,
        relative_path: pathlib.PurePath,
    ) -> T:
        """Build a placeholder for an archive known to require a password
        we don't have. Its metadata (scheme, volume count, padding) comes
        purely from the on-disk file layout, so no password is needed to
        build it."""
        volumes = locate_main_volume(AnchoredPath(storage_path, relative_path))
        # Only called after a RarPasswordError from a successful naming-pattern
        # match, so the path is already known to be a RAR archive.
        assert volumes is not None, f"{relative_path} does not match any RAR pattern"
        return cls(
            storage_path,
            volumes.main_volume_path,
            files=set(),
            scheme=volumes.scheme,
            n_volumes=volumes.n_volumes,
            part_n_padding=volumes.part_n_padding,
            requires_password=True,
        )

    @override
    def get_occupied_paths(self) -> list[pathlib.Path]:
        return self.get_volumes()

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
