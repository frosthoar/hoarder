"""RAR archive implementation backed by 7-zip."""

import logging
import os
import pathlib
import re
import subprocess
import typing

from ..utils import SEVENZIP
from .hash_archive import Algo, FileEntry
from .rar_archive import RarArchive
from .rar_path import DOT_RNN_PAT, PART_N_PAT, RarScheme, find_rar_files

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.archives.rar_archive_7z")

T = typing.TypeVar("T", bound="Rar7zArchive")


class Rar7zArchive(RarArchive):
    """RAR archive implementation that uses 7-zip for all operations."""

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
                logger.debug("Path %s matches a RAR pattern", path)
                search_dir = (
                    storage_path / path.parent
                    if path.parent != pathlib.PurePath(".")
                    else storage_path
                )
                logger.debug(
                    "Finding RAR files with stem %s in directory %s",
                    seek_stem,
                    search_dir,
                )
                rar_dict = find_rar_files(search_dir, seek_stem)
                if rar_dict:
                    logger.info(rar_dict)
                    scheme, rar_volumes = rar_dict[seek_stem]
                    n_volumes = len(rar_volumes)
                    logger.debug("Found %d volumes in %s", n_volumes, search_dir)
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

        infos = Rar7zArchive.list_rar(main_volume, password)
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
                    # RAR5 CRC field is optional and may be absent; read it directly
                    # from the header only for RAR3/4 where it is always present.
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
        """Extract a file internally via 7z to compute its CRC32.
        Necessary for RAR5 archives where the header CRC may be absent."""
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

    @override
    def update_hash_values(self) -> None:
        logger.debug("Updating hash values for %(name)s", {"name": self.full_path.name})
        for entry in self:
            if not entry.hash_value:
                try:
                    if entry.is_dir:
                        crc = b"\x00" * 4
                    else:
                        crc = self.get_crc32_slow(entry.path)

                    entry.hash_value = crc
                    entry.algo = Algo.CRC32
                except subprocess.CalledProcessError:
                    logger.error(
                        "Failed to get CRC32 for %(entry_path)s",
                        {"entry_path": entry.path},
                    )

    @override
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
