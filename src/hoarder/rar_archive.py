"""This module contains the RarArchive class, which holds information about a RAR file"""

import logging
import os
import pathlib
import re
import subprocess
import typing

import hoarder.hash_archive as hash_archive
import hoarder.rar_path as rar_path
from hoarder.shared import SEVENZIP

logger = logging.getLogger("hoarder.rar_file")

T = typing.TypeVar("T", bound="RarArchive")


class RarArchive(hash_archive.HashArchive):
    """This class contains information about a RAR file."""

    password: str | None
    scheme: rar_path.RarScheme | None
    version: str | None
    n_volumes: int | None

    def __init__(
        self,
        path: pathlib.Path,
        files: set[hash_archive.FileEntry] | None = None,
        password: str | None = None,
        version: str | None = None,
        scheme: rar_path.RarScheme | None = None,
        n_volumes: int | None = None,
    ) -> None:
        super().__init__(path, files)
        self.password = password
        self.scheme = scheme
        self.n_volumes = n_volumes
        self.version = None

    def get_volumes(self) -> list[pathlib.Path]:
        """Get a list of all volumes of the same RAR archive."""
        if self.n_volumes is None:
            raise ValueError(f"Volumes not set for {self.path}")
        if self.n_volumes == 0:
            raise ValueError(f"Invalid number of volumes for {self.path}")
        if self.n_volumes == 1:
            return [self.path]
        if self.scheme == rar_path.RarScheme.DOT_RNN:
            return [self.path.parent / f"{self.path.stem}.rar"] + [
                self.path.parent / f"{self.path.stem}.r{index:02d}"
                for index in range(0, self.n_volumes - 1)
            ]
        if self.scheme == rar_path.RarScheme.PART_N:
            stem = self.path.stem.split(".part")[0]
            volume_list = [
                self.path.parent / f"{stem}.part{index}.rar"
                for index in range(1, self.n_volumes + 1)
            ]
            for p in volume_list:
                if not p.exists():
                    raise FileNotFoundError(f"Volume {p} not found")
            return volume_list
        raise ValueError(
            f"Ambiguous RAR file {self.path} with {self.n_volumes} volumes"
        )

    @classmethod
    @typing.override
    def from_path(
        cls: type[T], path: pathlib.Path, password: str | None = None
    ) -> T:
        """Create a RarArchive object by reading information from a (main) RAR file given its path."""

        if path.is_dir():
            logger.debug("A directory %s was given, trying to find RAR files", path)
            rar_dict: dict[
                str, tuple[rar_path.RarScheme, list[pathlib.Path]]
            ] = rar_path.find_rar_files(path)
            if len(rar_dict) != 1:
                raise ValueError(
                    f"Directory {path} contains multiple non-indexed RAR files"
                )
            _, (scheme, rar_volumes) = rar_dict.popitem()
            n_volumes = len(rar_volumes)
            main_volume = rar_volumes[0]
            logger.debug("Found %d volumes in %s", n_volumes, path)
        elif path.is_file():
            logger.debug("A file %s was given, trying to find RAR files", path)
            if match := (
                rar_path.DOT_RNN_PAT.match(str(path.name))
                or rar_path.PART_N_PAT.match(str(path.name))
            ):
                seek_stem = match["stem"]
                logger.debug("Path %s matches a RAR pattern", path)
                logger.debug(
                    "Finding RAR files with stem %s in directory %s",
                    seek_stem,
                    path.parent,
                )
                rar_dict = rar_path.find_rar_files(path.parent, seek_stem)
                if rar_dict:
                    logger.info(rar_dict)
                    scheme, rar_volumes = rar_dict[seek_stem]
                    n_volumes = len(rar_volumes)
                    logger.debug("Found %d volumes in %s", n_volumes, path.parent)
                    main_volume = rar_dict[seek_stem][1][0]
                    logger.debug("Main volume is %s", main_volume)
                else:
                    raise ValueError(f"Path {path} does not match any RAR pattern")
            else:
                raise ValueError(f"Path {path} does not match any RAR pattern")
        else:
            logger.debug("Path %s is not a file or directory", path)
            raise FileNotFoundError(f"{path} could not be found")

        infos = RarArchive.list_rar(main_volume, password)
        type_entries = [entry for entry in infos if "Type" in entry]

        if not type_entries or len(type_entries) > 1:
            version = None
            logger.warning(f"No 'Type' entries found in {path}")
        else:
            version = type_entries[0]["Type"]

        files: set[hash_archive.FileEntry] = set()
        for entry in infos:
            if "Path" in entry and "Type" not in entry:
                entry_path = pathlib.Path(entry["Path"])
                size = int(entry["Size"])
                is_dir = entry["Folder"] == "+"
                hash_value = None
                algo = None
                if version and version.upper() in ("RAR", "RAR3"):
                    # RAR5 hashes the file contents again with their respective mtimes,
                    # so the CRCs in the header are not useful for verification.
                    hash_value = bytes.fromhex(entry["CRC"]) if "CRC" in entry else None
                    algo = hash_archive.Algo.CRC32 if hash_value else None
                files.add(
                    hash_archive.FileEntry(entry_path, size, is_dir, hash_value, algo)
                )
        logger.info(scheme)
        return cls(main_volume, files, password, version, scheme, n_volumes)

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
            SEVENZIP,
            "l",
            "-slt",
            "-scsUTF-8",
            "-sccUTF-8",
            "-p" + (password if password else ""),
            path,
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
            SEVENZIP,
            "t",
            "-scrc",
            "-scsUTF-8",
            "-sccUTF-8",
            "-p" + (self.password or ""),
            self.path,
            entry_path,
        ]
        logger.debug(
            "Processing archive %(name)s with path %(entry_path)s using password %(password)s",
            {
                "name": self.path.name,
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
                {"name": self.path.name, "entry_path": entry_path},
            )
            return None
        logger.debug(
            "Got CRC %(crc_match)s for %(name)s: %(entry_path)s",
            {"crc_match": crc_match, "name": self.path.name, "entry_path": entry_path},
        )
        return bytes.fromhex(crc_match)

    @property
    def hash_values_exist(self) -> bool:
        """Check if *all* files already have hash values."""
        return all(file.hash_value for file in self if not file.is_dir)

    def update_hash_values(self):
        """Update the hash values of all files in the archive.
        This will always use the slow method."""
        logger.debug("Updating hash values for %(name)s", {"name": self.path.name})
        for entry in self:
            if not entry.hash_value:
                try:
                    if entry.is_dir:
                        crc = b"\x00" * 4
                    else:
                        crc = self.get_crc32_slow(entry.path)  # used for PART_N, slow

                    entry.hash_value = crc
                    entry.algo = hash_archive.Algo.CRC32
                except subprocess.CalledProcessError:
                    logger.error(
                        "Failed to get CRC32 for %(entry_path)s",
                        {"entry_path": entry.path},
                    )
