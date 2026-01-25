"""This module contains the RarArchive class, which holds information about a RAR file"""

import glob
import logging
import os
import pathlib
import re
import subprocess
import typing

from ..utils import SEVENZIP, AnchoredPath
from .hash_archive import Algo, FileEntry, HashArchive, HashArchiveSelf
from .rar_path import DOT_RNN_PAT, PART_N_PAT, RarScheme, RarPath, RarArchiveSet

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.archives.rar_file")

T = typing.TypeVar("T", bound="RarArchive")


class RarArchive(HashArchive):
    """This class contains information about a RAR file."""

    password: str | None
    scheme: RarScheme | None
    version: str | None
    n_volumes: int | None

    def __init__(
        self,
        storage_path: pathlib.Path,
        relative_path: pathlib.PurePath,
        files: set[FileEntry] | None = None,
        password: str | None = None,
        version: str | None = None,
        scheme: RarScheme | None = None,
        n_volumes: int | None = None,
    ) -> None:
        super().__init__(storage_path, relative_path, files)
        self.password = password
        self.scheme = scheme
        self.n_volumes = n_volumes
        self.version = None

    def get_volumes(self) -> list[pathlib.Path]:
        """Get a list of all volumes of the same RAR archive."""
        if self.n_volumes is None:
            raise ValueError(f"Volumes not set for {self.full_path}")
        if self.n_volumes == 0:
            raise ValueError(f"Invalid number of volumes for {self.full_path}")
        if self.n_volumes == 1:
            return [self.full_path]
        if self.scheme == RarScheme.DOT_RNN:
            return [self.storage_path / f"{self.relative_path.stem}.rar"] + [
                self.storage_path / f"{self.relative_path.stem}.r{index:02d}"
                for index in range(0, self.n_volumes - 1)
            ]
        if self.scheme == RarScheme.PART_N:
            stem = self.relative_path.stem.split(".part")[0]
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

    @classmethod
    @override
    def _from_path(
        cls: type[T],
        storage_path: pathlib.Path,
        relative_path: pathlib.PurePath,
        password: str | None = None,
    ) -> T:
        """Create a RarArchive object by reading information from a (main) RAR file.

        Args:
            storage_path: The storage directory path
            relative_path: The relative path from storage_path
            password: Optional password for encrypted archives
        """
        full_path = storage_path / relative_path

        if full_path.is_dir():
            logger.debug(
                "A directory %s was given, trying to find RAR files", full_path
            )
            rar_dict = RarArchiveSet.find_rar_files(full_path)
            if len(rar_dict) != 1:
                raise ValueError(
                    f"Directory {full_path} contains multiple non-indexed RAR files"
                )
            _, archive_set = rar_dict.popitem()
            scheme = archive_set.scheme
            n_volumes = len(archive_set.volumes)
            main_volume = archive_set.sorted_volume_paths[0]
            # Calculate relative path from storage_path
            try:
                main_volume_path = main_volume.relative_to(storage_path)
            except ValueError:
                raise ValueError(
                    f"Main volume {main_volume} is not under storage_path {storage_path}"
                )
            logger.debug("Found %d volumes in %s", n_volumes, full_path)
        elif full_path.is_file():
            logger.debug("A file %s was given, trying to find RAR files", full_path)
            if match := PART_N_PAT.match(str(relative_path.name)):
                logger.debug("Path %s matches a PART_N_PAT pattern", relative_path)
            elif match := DOT_RNN_PAT.match(str(relative_path.name)):
                logger.debug("Path %s matches a DOT_RNN_PAT pattern", relative_path)

            if match:
                seek_stem = match["stem"]
                logger.debug("Path %s matches a RAR pattern", relative_path)
                # Search in the directory containing the file (storage_path / relative_path.parent)
                search_dir = (
                    storage_path / relative_path.parent
                    if relative_path.parent != pathlib.PurePath(".")
                    else storage_path
                )
                logger.debug(
                    "Finding RAR files with stem %s in directory %s",
                    seek_stem,
                    search_dir,
                )
                rar_dict = RarArchiveSet.find_rar_files(search_dir, seek_stem)
                if rar_dict:
                    logger.info(rar_dict)
                    archive_set = rar_dict[seek_stem]
                    scheme = archive_set.scheme
                    n_volumes = len(archive_set.volumes)
                    logger.debug("Found %d volumes in %s", n_volumes, search_dir)
                    main_volume = pathlib.Path(archive_set.sorted_volume_paths[0])
                    # Calculate relative path from storage_path
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

        infos = RarArchive.list_rar(main_volume, password)
        type_entries = [entry for entry in infos if "Type" in entry]

        if not type_entries or len(type_entries) > 1:
            version = None
            logger.warning(f"No 'Type' entries found in {full_path}")
        else:
            version = type_entries[0]["Type"]

        files: set[FileEntry] = set()
        for entry in infos:
            if "Path" in entry and "Type" not in entry:
                entry_path = pathlib.PurePath(entry["Path"])
                size = int(entry["Size"])
                is_dir = entry["Folder"] == "+"
                hash_value = None
                algo = None
                if version and version.upper() in ("RAR", "RAR3"):
                    # RAR5 hashes the file contents again with their respective mtimes,
                    # so the CRCs in the header are not useful for verification.
                    hash_value = bytes.fromhex(entry["CRC"]) if "CRC" in entry else None
                    algo = Algo.CRC32 if hash_value else None
                files.add(FileEntry(entry_path, size, is_dir, hash_value, algo))
        logger.info(scheme)
        return cls(
            storage_path,
            pathlib.PurePath(main_volume_path),
            files,
            password,
            version,
            scheme,
            n_volumes,
        )

    @classmethod
    def list_rar(
        cls, path: pathlib.Path, password: str | None = None
    ) -> list[dict[str, str]]:
        """Get an info list about this archive and its contents."""
        logger.debug(
            "Listing %(name)s, using password %(password)s",
            {"name": path.name, "password": password},
        )

        command_line = [
            str(SEVENZIP),
            "l",
            "-slt",
            "-scsUTF-8",
            "-sccUTF-8",
            "-p" + (password if password else ""),
            str(path),
        ]

        sub = subprocess.run(command_line, capture_output=True, check=True)

        entries = sub.stdout.decode(errors="ignore", encoding="utf-8").split(
            2 * os.linesep
        )
        ret: list[dict[str, str]] = []

        for entry in entries:
            lines = entry.splitlines()
            kv_pairs = [line.split("=", 1) for line in lines if "=" in line]
            entry_dict = {k.strip(): v.strip() for k, v in kv_pairs if k.strip()}
            if entry_dict:
                ret.append(entry_dict)

        logger.debug(
            "Found %(count)d files in %(name)s",
            {"count": len(ret), "name": path.name},
        )
        return ret

    def get_crc32_slow(
        self,
        entry_path: pathlib.PurePath | str,
    ) -> bytes | None:
        """The slow method to get the CRC32 of a file in a RAR archive.
        7z extracts files internally - this is necessary for RAR5 archives,
        where we can't use the CRCs in the header."""
        command_line = [
            str(SEVENZIP),
            "t",
            "-scrc",
            "-scsUTF-8",
            "-sccUTF-8",
            "-p" + (self.password or ""),
            str(self.full_path),
            str(entry_path),
        ]
        logger.debug(
            "Processing archive %(name)s with path %(entry_path)s using password %(password)s",
            {
                "name": self.relative_path.name,
                "entry_path": entry_path,
                "password": self.password,
            },
        )

        sub = subprocess.run(command_line, capture_output=True, check=True)

        lines = sub.stdout.decode(errors="ignore", encoding="utf-8").splitlines()

        crc_match = next(
            (
                m.group(1)
                for line in lines
                if (m := re.match(r".*CRC32.*data.*([A-F0-9]{8}).*", line))
            ),
            None,
        )

        if not crc_match:
            logger.error(
                "Failed to get CRC for %(name)s: %(entry_path)s",
                {"name": self.relative_path.name, "entry_path": entry_path},
            )
            return None
        logger.debug(
            "Got CRC %(crc_match)s for %(name)s: %(entry_path)s",
            {"crc_match": crc_match, "name": self.relative_path.name, "entry_path": entry_path},
        )
        return bytes.fromhex(crc_match)

    @property
    def hash_values_exist(self) -> bool:
        """Check if *all* files already have hash values."""
        return all(file.hash_value for file in self if not file.is_dir)

    def update_hash_values(self):
        """Update the hash values of all files in the archive.
        This will always use the slow method."""
        logger.debug("Updating hash values for %(name)s", {"name": self.full_path.name})
        for entry in self:
            if not entry.hash_value:
                try:
                    if entry.is_dir:
                        crc = b"\x00" * 4
                    else:
                        crc = self.get_crc32_slow(entry.path)  # used for PART_N, slow

                    entry.hash_value = crc
                    entry.algo = Algo.CRC32
                except subprocess.CalledProcessError:
                    logger.error(
                        "Failed to get CRC32 for %(entry_path)s",
                        {"entry_path": entry.path},
                    )

    def read_file(self, path: pathlib.PurePath) -> bytes:
        paths: set[pathlib.PurePath] = set([file.path for file in self.files])
        if path not in paths:
            raise FileNotFoundError(f"Could not find {path}")

        command_line: list[str] = [
            str(SEVENZIP),
            "x",
            "-so",
            "-scsUTF-8",
            "-sccUTF-8",
            "-p" + (self.password if self.password else ""),
            str(self.full_path),
            str(path),
        ]

        sub = subprocess.run(command_line, capture_output=True, check=True)
        return sub.stdout

    @classmethod
    @override
    def discover(cls: typing.Type[HashArchiveSelf], scope: AnchoredPath) -> list[HashArchiveSelf]:
        rar_path_list: list[RarPath] = []
        if not scope.full_path.is_dir():
            raise NotADirectoryError(f'Given scope "{scope.full_path}" is a directory')
        return []


