"""RAR archive implementation backed by the rarfile library."""

import logging
import pathlib
import typing
import zlib

import rarfile

from .hash_archive import Algo, FileEntry
from .rar_archive import RarArchive
from .rar_path import DOT_RNN_PAT, PART_N_PAT, RarScheme, find_rar_files

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


class RarfileRarArchive(RarArchive):
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
        path: pathlib.PurePath,
        password: str | None = None,
    ) -> T:
        full_path = storage_path / path

        if full_path.is_dir():
            logger.debug(
                "A directory %s was given, trying to find RAR files", full_path
            )
            rar_dict: dict[str, tuple[RarScheme, list[pathlib.Path]]] = find_rar_files(
                full_path
            )
            if len(rar_dict) != 1:
                raise ValueError(
                    f"Directory {full_path} contains multiple non-indexed RAR files"
                )
            _, (scheme, rar_volumes) = rar_dict.popitem()
            n_volumes = len(rar_volumes)
            main_volume = rar_volumes[0]
            try:
                main_volume_path = main_volume.relative_to(storage_path)
            except ValueError:
                raise ValueError(
                    f"Main volume {main_volume} is not under storage_path {storage_path}"
                )
            logger.debug("Found %d volumes in %s", n_volumes, full_path)
        elif full_path.is_file():
            logger.debug("A file %s was given, trying to find RAR files", full_path)
            if match := PART_N_PAT.match(str(path.name)):
                logger.debug("Path %s matches a PART_N_PAT pattern", path)
            elif match := DOT_RNN_PAT.match(str(path.name)):
                logger.debug("Path %s matches a DOT_RNN_PAT pattern", path)

            if match:
                seek_stem = match["stem"]
                search_dir = (
                    storage_path / path.parent
                    if path.parent != pathlib.PurePath(".")
                    else storage_path
                )
                rar_dict = find_rar_files(search_dir, seek_stem)
                if rar_dict:
                    scheme, rar_volumes = rar_dict[seek_stem]
                    n_volumes = len(rar_volumes)
                    main_volume = rar_dict[seek_stem][1][0]
                    try:
                        main_volume_path = main_volume.relative_to(storage_path)
                    except ValueError:
                        raise ValueError(
                            f"Main volume {main_volume} is not under storage_path {storage_path}"
                        )
                    logger.debug("Main volume is %s", main_volume)
                else:
                    raise ValueError(f"Path {full_path} does not match any RAR pattern")
            else:
                raise ValueError(f"Path {full_path} does not match any RAR pattern")
        else:
            logger.debug("Path %s is not a file or directory", full_path)
            raise FileNotFoundError(f"{full_path} could not be found")

        version = _detect_version(main_volume)

        pwd = password.encode() if password else None
        files: set[FileEntry] = set()
        with rarfile.RarFile(str(main_volume), errors="ignore") as rf:
            if pwd:
                rf.setpassword(pwd)
            for ri in rf.infolist():
                entry_path = pathlib.PurePath(ri.filename)
                size = ri.file_size
                is_dir = ri.is_dir()
                hash_value = ri.CRC.to_bytes(4, "big") if ri.CRC is not None else None
                algo = Algo.CRC32 if hash_value is not None else None
                files.add(FileEntry(entry_path, size, is_dir, hash_value, algo))

        return cls(
            storage_path,
            pathlib.PurePath(main_volume_path),
            files,
            password,
            version,
            scheme,
            n_volumes,
        )

    @override
    def update_hash_values(self) -> None:
        logger.debug("Updating hash values for %s", self.full_path.name)
        pwd = self.password.encode() if self.password else None
        with rarfile.RarFile(str(self.full_path), errors="ignore") as rf:
            if pwd:
                rf.setpassword(pwd)
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
                except Exception:
                    logger.error("Failed to get CRC32 for %s", entry.path)

    @override
    def read_file(self, path: pathlib.PurePath) -> bytes:
        paths: set[pathlib.PurePath] = {file.path for file in self.files}
        if path not in paths:
            raise FileNotFoundError(f"Could not find {path}")

        pwd = self.password.encode() if self.password else None
        with rarfile.RarFile(str(self.full_path), errors="ignore") as rf:
            if pwd:
                rf.setpassword(pwd)
            return rf.read(str(path))
