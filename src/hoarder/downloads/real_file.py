from __future__ import annotations

import dataclasses
import datetime as dt
import enum
from pathlib import Path, PurePath
from typing import ClassVar, Type

from ..archives import Algo
from ..utils import AnchoredPath
from .contents_hasher import ContentsHasher, CRC32Hasher

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override


class VerificationSource(enum.IntEnum):
    """Identifies where the verification information originated."""

    ARCHIVE = 1
    FILENAME = 2
    ONLINE = 3
    MANUAL = 4
    SELF_HASH = 5


@dataclasses.dataclass(slots=True, eq=True)
class RealFile:
    """Represents a file or directory we encountered in storage.

    Identity and hashing are based on full_path (anchor.storage_path resolved
    against anchor.relative_path), independent of storage root layout. DO NOT
    reassign `anchor` on an instance that is live in a dict/set keyed by it —
    like `FileEntry`, this class is mutable, and mutating the field the hash
    depends on after insertion corrupts the containing collection. Replace
    the instance (e.g. via `dataclasses.replace`) instead of mutating `anchor`
    in place.
    """

    anchor: AnchoredPath
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
        return self.anchor.full_path

    @override
    def __hash__(self) -> int:
        return hash(self.full_path)

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

    @classmethod
    def from_path(
        cls,
        storage_path: Path | str,
        relative_path: PurePath | str,
        *,
        include_hash: bool = False,
        algo: Algo = Algo.CRC32,
    ) -> RealFile:
        """Create a RealFile instance by inspecting the filesystem."""
        anchor = AnchoredPath(Path(storage_path), PurePath(relative_path))
        full_path = anchor.full_path
        if not full_path.exists():
            raise FileNotFoundError(full_path)

        stat = full_path.stat()
        real_file = cls(
            anchor=anchor,
            size=stat.st_size,
            is_dir=full_path.is_dir(),
        )

        if include_hash and not real_file.is_dir:
            real_file.calculate_hash(algo=algo)
        return real_file


@dataclasses.dataclass(slots=True)
class Verification:
    """Metadata describing how a `RealFile` was verified."""

    real_file: RealFile
    source_type: VerificationSource
    source: AnchoredPath
    hash_value: bytes
    algo: Algo
    comment: str | None = None

    @property
    def verified(self) -> bool:
        """Return True when the real file hash matches the stored verification hash."""
        if self.real_file.hash_value is None:
            return False
        if self.real_file.algo != self.algo:
            return False
        return self.real_file.hash_value == self.hash_value

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
