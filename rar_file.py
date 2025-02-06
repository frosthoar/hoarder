"""This module contains the RarFile class, which hoolds information about a RAR file"""

import logging
import os
import pathlib
import re
import subprocess
import typing

import rar_path
from shared import SEVENZIP
import hash_file
logger = logging.getLogger("hoarder.rar_file")


class RarFile(hash_file.HashFile):
    """This class contains information about a RAR file."""

    password: str | None
    volumes: int | None
    version: rar_path.RarVersion | None

    def __init__(
        self,
        path: pathlib.Path,
        files: list[hash_file.FileEntry] | None = None,
        password: str | None = None,
    ) -> None:
        super().__init__(path, files)
        self.password = password
        self.version: rar_path.RarVersion | None = None
        self.volumes: list[rar_path.RARPath] | None = None

    def get_volumes(self) -> list[pathlib.Path]:
        """Get a list of all volumes of the same RAR archive."""
        if self.volumes is None:
            raise ValueError(f"Volumes not set for {self.path}")
        if self.volumes == 0:
            raise ValueError(f"Invalid number of volumes for {self.path}")
        if self.volumes == 1:
            return [self.path]
        if self.version == rar_path.RarVersion.V3:
            return [self.path.parent / f"{self.path.stem}.rar"] + [
                self.path.parent / f"{self.path.stem}.r{index:02d}"
                for index in range(0, self.volumes - 1)
            ]
        if self.version == rar_path.RarVersion.V5:
            stem = self.path.stem.split(".part")[0]
            volume_list = [
                self.path.parent / f"{stem}.part{index}.rar"
                for index in range(1, self.volumes + 1)
            ]
            for p in volume_list:
                if not p.exists():
                    raise FileNotFoundError(f"Volume {p} not found")
            return volume_list
        raise ValueError(f"Ambiguous RAR file {self.path} with {self.volumes} volumes")

    @classmethod
    def from_path(cls, path: pathlib.Path, password: str | None = None) -> typing.Self:
        """Create a RarFile object by reading information from a (main) RAR file given its path."""

        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
        if path.is_dir():
            rar_dict: dict[str, list[pathlib.Path]] = rar_path.find_rar_files(path)
            if len(rar_dict) != 1:
                raise ValueError(
                    f"Directory {path} contains multiple non-indexed RAR files"
                )
            _, rar_volumes = rar_dict.popitem()
            rar_file = cls(rar_volumes[0], password=password)
            rar_file.volumes = len(rar_volumes)
        else:
            if match := (
                rar_path.V5_PAT.match(str(path.name))
                or rar_path.V3_PAT.match(str(path.name))
            ):
                print(match["stem"])
                rar_dict = rar_path.find_rar_files(path.parent)
                print(rar_dict)
                if match["stem"] in rar_dict:
                    rar_file = cls(rar_dict[match["stem"]][0], password=password)
                    rar_file.volumes = len(rar_dict[match["stem"]])
                else:
                    raise ValueError(f"Path {path} does not match any RAR pattern")
            else:
                raise ValueError(f"Path {path} does not match any RAR pattern")

        infos = rar_file.list_rar()
        type_entries = [entry for entry in infos if "Type" in entry]
        if not type_entries or len(type_entries) > 1:
            raise ValueError(f"No 'Type' entries found in {path}")
        if type_entries[0]["Type"] == "Rar3":
            version = rar_path.RarVersion.V3
        elif type_entries[0]["Type"] == "Rar5":
            version = rar_path.RarVersion.V5
        else:
            raise ValueError(f"Unknown RAR version {type_entries[0]['Type']} in {path}")

        for entry in infos:
            if "Path" in entry and "Type" not in entry:
                entry_path = pathlib.Path(entry["Path"])
                size = int(entry["Size"])
                is_dir = entry["Folder"] == "+"
                hash_value = None
                algo = None
                if version == rar_path.RarVersion.V3:
                    # RAR5 hashes the file contents again with their respective mtimes,
                    # so the CRCs in the header are not useful for verification.
                    hash_value = bytes.fromhex(entry["CRC"]) if "CRC" in entry else None
                    algo = hash_file.Algo.CRC32 if hash_value else None
                rar_file.files.append(
                    hash_file.FileEntry(entry_path, size, is_dir, hash_value, algo)
                )
        rar_file.version = version
        return rar_file

    def list_rar(self) -> list[dict[str, str]]:
        """Get an info list about this archive and its contents."""
        logger.debug("Listing %(name)s, using password %(password)s", {"name": self.path.name, "password": self.password})

        command_line = [
            str(SEVENZIP),
            "l",
            "-slt",
            "-p" + (self.password if self.password else ""),
            str(self.path),
        ]

        sub = subprocess.run(command_line, capture_output=True, check=True)

        encoding = os.device_encoding(0)
        if encoding:
            entries = sub.stdout.decode(encoding, errors="ignore").split(2 * os.linesep)
        else:
            raise RuntimeError("Coud not get encoding")
        ret = []

        for entry in entries:
            lines = entry.splitlines()
            kv_pairs = [line.split("=", 1) for line in lines if "=" in line]
            entry_dict = {k.strip(): v.strip() for k, v in kv_pairs if k.strip()}
            if entry_dict:
                ret.append(entry_dict)

        logger.debug("Found %(count)d files in %(name)s", {"count": len(ret), "name": self.path.name})
        return ret

    def get_crc32_slow(
        self,
        entry_path: pathlib.Path | str,
    ) -> bytes | None:
        """The slow method to get the CRC32 of a file in a RAR archive.
        7z extracts files internally - this is necessary for RAR5 archives,
        where we can't use the CRCs in the header."""
        command_line = [
            SEVENZIP,
            "t",
            "-scrc",
            "-p" + (self.password or ""),
            self.path,
            entry_path,
        ]
        logger.debug("Processing archive %(name)s with path %(entry_path)s using password %(password)s", {"name": self.path.name, "entry_path": entry_path, "password": self.password})

        sub = subprocess.run(command_line, capture_output=True, check=True)

        encoding = os.device_encoding(0)
        if encoding:
            lines = sub.stdout.decode(encoding, errors="ignore").splitlines()
        else:
            raise RuntimeError("Coud not get encoding")

        crc_match = next(
            (
                m.group(1)
                for line in lines
                if (m := re.match(r".*CRC32.*data.*([A-F0-9]{8}).*", line))
            ),
            None,
        )

        if not crc_match:
            logger.error("Failed to get CRC for %(name)s: %(entry_path)s", {"name": self.path.name, "entry_path": entry_path})
            return None
        logger.debug("Got CRC %(crc_match)s for %(name)s: %(entry_path)s", {"crc_match": crc_match, "name": self.path.name, "entry_path": entry_path})
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
            if not entry.hash_value and not entry.is_dir:
                try:
                    crc = self.get_crc32_slow(entry.path)  # used for V5, slow
                    entry.hash_value = crc
                except subprocess.CalledProcessError:
                    logger.error("Failed to get CRC32 for %(entry_path)s", {"entry_path": entry.path})
