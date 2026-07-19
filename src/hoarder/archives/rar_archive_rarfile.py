"""RAR archive implementation backed by the rarfile library."""

import logging
import pathlib
import typing
import zlib

import rarfile

from ..utils.path_utils import AnchoredPath
from .abstract_rar_archive import AbstractRarArchive, RarArchiveError, RarPasswordError
from .hash_archive import Algo, FileEntry
from .rar_path import locate_main_volume

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.archives.rar_archive_rarfile")

T = typing.TypeVar("T", bound="RarfileRarArchive")

_RAR5_MAGIC = b"Rar!\x1a\x07\x01\x00"
_RAR4_MAGIC = b"Rar!\x1a\x07\x00"


def _detect_version(path: pathlib.Path) -> str | None:
    with open(path, "rb") as f:
        magic = f.read(8)
    if magic == _RAR5_MAGIC:
        return "RAR5"
    if magic[:7] == _RAR4_MAGIC:
        return "RAR"
    return None


def _is_password_error(exc: rarfile.Error, pwd: bytes | None) -> bool:
    """Best-effort classification of a rarfile.Error as password-related.

    RAR5 has a real password-check hash and raises a dedicated exception
    on mismatch; rarfile also raises a dedicated exception when a file
    needs a password and none was set. RAR4 has no such check - a wrong
    password just corrupts header parsing, surfacing as a generic
    BadRarFile (whose own message hints "wrong password?"). Since that
    message text isn't part of the library's stable API, treat any
    BadRarFile as password-related when a password was actually supplied.
    """
    if isinstance(exc, (rarfile.PasswordRequired, rarfile.RarWrongPassword)):
        return True
    return isinstance(exc, rarfile.BadRarFile) and pwd is not None


class RarfileRarArchive(AbstractRarArchive):
    """RAR archive implementation using the rarfile library.

    Reads CRC32 directly from archive headers when available (avoiding
    full decompression), falling back to extraction only when the field
    is absent (possible in RAR5).
    """

    @classmethod
    @override
    def _from_path(
        cls: type[T],
        storage_path: pathlib.Path,
        relative_path: pathlib.PurePath,
        password: str | None = None,
    ) -> T:
        volumes = locate_main_volume(AnchoredPath(storage_path, relative_path))
        if volumes is None:
            raise ValueError(f"Path {relative_path} does not match any RAR pattern")

        version = _detect_version(volumes.main_volume)

        pwd = password.encode() if password else None
        files: set[FileEntry] = set()
        requires_password = False
        try:
            with rarfile.RarFile(str(volumes.main_volume), errors="stop") as rf:
                if pwd:
                    rf.setpassword(pwd)
                requires_password = rf.needs_password()
                if requires_password and not pwd:
                    raise RarPasswordError(f"{volumes.main_volume} requires a password")
                for ri in rf.infolist():
                    entry_path = pathlib.PurePath(ri.filename)
                    size = ri.file_size
                    is_dir = ri.is_dir()
                    hash_value = (
                        ri.CRC.to_bytes(4, "big") if ri.CRC is not None else None
                    )
                    algo = Algo.CRC32 if hash_value is not None else None
                    files.add(FileEntry(entry_path, size, is_dir, hash_value, algo))
        except rarfile.Error as exc:
            if _is_password_error(exc, pwd):
                raise RarPasswordError(
                    f"Wrong password for {volumes.main_volume}"
                ) from exc
            raise RarArchiveError(
                f"rarfile failed to list {volumes.main_volume}"
            ) from exc

        return cls(
            storage_path,
            pathlib.PurePath(volumes.main_volume_path),
            files,
            password,
            version,
            volumes.scheme,
            volumes.n_volumes,
            volumes.part_n_padding,
            requires_password,
        )

    @override
    def update_hash_values(self) -> None:
        logger.debug("Updating hash values for %s", self.full_path.name)
        pwd = self.password.encode() if self.password else None
        try:
            with rarfile.RarFile(str(self.full_path), errors="stop") as rf:
                if pwd:
                    rf.setpassword(pwd)
                if rf.needs_password() and not pwd:
                    raise RarPasswordError(f"{self.full_path} requires a password")
                for entry in self:
                    if entry.hash_value:
                        continue
                    if entry.is_dir:
                        entry.hash_value = b"\x00" * 4
                        entry.algo = Algo.CRC32
                        continue
                    try:
                        data = rf.read(str(entry.path))
                        crc = zlib.crc32(data) & 0xFFFFFFFF
                        entry.hash_value = crc.to_bytes(4, "big")
                        entry.algo = Algo.CRC32
                    except rarfile.Error as exc:
                        if _is_password_error(exc, pwd):
                            raise RarPasswordError(
                                f"Wrong password for {self.full_path}"
                            ) from exc
                        logger.error("Failed to get CRC32 for %s", entry.path)
        except rarfile.Error as exc:
            if _is_password_error(exc, pwd):
                raise RarPasswordError(f"Wrong password for {self.full_path}") from exc
            raise RarArchiveError(f"rarfile failed to open {self.full_path}") from exc

    @override
    def read_file(self, path: pathlib.PurePath) -> bytes:
        paths: set[pathlib.PurePath] = {file.path for file in self.files}
        if path not in paths:
            raise FileNotFoundError(f"Could not find {path}")

        pwd = self.password.encode() if self.password else None
        try:
            with rarfile.RarFile(str(self.full_path), errors="stop") as rf:
                if pwd:
                    rf.setpassword(pwd)
                return rf.read(str(path))
        except rarfile.Error as exc:
            if _is_password_error(exc, pwd):
                raise RarPasswordError(
                    f"Wrong password for {path} in {self.full_path}"
                ) from exc
            raise RarArchiveError(
                f"rarfile failed to extract {path} from {self.full_path}"
            ) from exc
