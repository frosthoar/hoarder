from __future__ import annotations

import dataclasses
import datetime as dt
import enum
from pathlib import Path, PurePath
from typing import ClassVar, Type

from hoarder.archives.hash_archive import Algo, HashArchive

from .contents_hasher import CRC32Hasher, ContentsHasher


class VerificationSource(enum.IntEnum):
    """Identifies where the verification information originated."""

    ARCHIVE = 1
    FILENAME = 2
    ONLINE = 3
    MANUAL = 4
    SELF_HASH = 5


@dataclasses.dataclass(slots=True, eq=True)
class RealFile:
    """Represents a file or directory we encountered in storage."""

    storage_path: Path
    path: PurePath
    size: int
    is_dir: bool
    algo: Algo | None = None
    hash_value: bytes | None = None
    verification: list[Verification] = dataclasses.field(default_factory=list)
    first_seen: dt.datetime | None = dataclasses.field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    last_seen: dt.datetime | None = dataclasses.field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    comment: str | None = None

    _HASHERS: ClassVar[dict[Algo, Type[ContentsHasher]]] = {
        Algo.CRC32: CRC32Hasher,
    }

    @property
    def full_path(self) -> Path:
        """Return the resolved path on disk."""
        return self.storage_path / self.path

    def calculate_hash(self, algo: Algo = Algo.CRC32) -> bytes:
        """Calculate and assign hash/algo for this real file."""
        hasher_cls = self._HASHERS.get(algo)
        if hasher_cls is None:
            raise NotImplementedError(
                f"Hash calculation for algo {algo.name} is not implemented"
            )

        hasher = hasher_cls(self.full_path)
        hash_value = hasher.hash_contents()
        self.hash_value = hash_value
        self.algo = algo
        return hash_value


@dataclasses.dataclass(slots=True)
class Verification:
    """Metadata describing how a `RealFile` was verified."""

    real_file: RealFile
    source_type: VerificationSource
    hash_archive: HashArchive | None
    verified: bool
    hash_value: bytes
    algo: Algo
    verified_at: dt.datetime
    comment: str | None = None

    @property
    def is_trusted(self) -> bool:
        """
        Whether the verification can be relied upon.

        Self-hashes are not considered trusted because they do not provide an
        independent validation source.
        """
        if self.source_type is VerificationSource.SELF_HASH:
            return False
        return self.verified

