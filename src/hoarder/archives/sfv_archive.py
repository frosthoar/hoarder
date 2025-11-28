"""This module contains the SfvArchive class, which represents a SFV file."""

import logging
import os
import pathlib
import typing

from ..utils import PathType, determine_path_type
from .hash_archive import Algo, FileEntry, HashArchive

logger = logging.getLogger("hoarder.archives.sfv_file")

T = typing.TypeVar("T", bound="SfvArchive")


class SfvArchive(HashArchive):
    """This class contains information about a SFV file."""

    @classmethod
    def _from_path(
        cls: typing.Type[T], storage_path: pathlib.Path, path: pathlib.PurePath
    ) -> T:
        """Create a SfvArchive object by reading information from an SFV file given its storage_path and path.

        Args:
            storage_path: The storage directory path (explicitly set, not inferred)
            path: The relative path from storage_path (as PurePath)
        """
        full_path = storage_path / path
        files = []
        with open(full_path, "rt", encoding="utf-8") as file:
            logger.debug("Reading %s", full_path)
            for line in file.readlines():
                line = line.strip()
                if not line or line.startswith(";"):
                    logger.debug("Skipping line: %s", line)
                    continue
                try:
                    entry_path_str, crc = line.rsplit(
                        " ", maxsplit=1
                    )  # split on the last space, in case the filename contains spaces
                except ValueError:
                    logger.error(
                        "Line is not in the expected format: %(line)s", {"line": line}
                    )
                    continue
                try:
                    file_size = None
                    if (storage_path / entry_path_str).exists():
                        # SFV files are placed in the same directory as the files they reference
                        # so we should be able to get the size of the file
                        file_size = os.path.getsize(storage_path / entry_path_str)
                    else:
                        logger.warning(
                            "File '%(entry_path_str)s' does not exist",
                            {"entry_path_str": entry_path_str},
                        )

                    entry_path: pathlib.PurePath
                    if determine_path_type(entry_path_str) == PathType.WINDOWS:
                        entry_path = pathlib.PurePath(
                            pathlib.PureWindowsPath(entry_path_str).as_posix()
                        )
                    elif determine_path_type(entry_path_str) == PathType.UNRESOLVABLE:
                        raise ValueError(
                            f"Could not determine path type of {entry_path_str}"
                        )
                    else:
                        entry_path = pathlib.PurePosixPath(entry_path_str)

                    files.append(
                        FileEntry(
                            pathlib.PurePath(entry_path),
                            file_size,
                            False,
                            bytes.fromhex(crc),
                            Algo.CRC32,
                        )
                    )
                except ValueError as e:
                    # we want to continue processing the file even if there's an error with one line
                    logger.error(
                        "Error converting '%(line)s' to FileEntry: %(error)s",
                        {"line": line, "error": e},
                    )
        return cls(storage_path, path, set(files))
