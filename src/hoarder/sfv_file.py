"""This module contains the SfvFile class, which represents a SFV file."""

import logging
import os
import pathlib
import typing

import hoarder.hash_file as hash_file

logger = logging.getLogger("hoarder.sfv_file")

Self = typing.TypeVar("Self")

class SfvFile(hash_file.HashFile):
    """This class contains information about a SFV file."""

    @classmethod
    def from_path(cls, path: pathlib.Path) -> Self:
        """Create a SfvFile object by reading information from an SFV file given its path."""
        files = []
        with open(path, "rt", encoding="utf-8") as file:
            logger.debug("Reading %s", path)
            for line in file.readlines():
                line = line.strip()
                if not line or line.startswith(";"):
                    logger.debug("Skipping line: %s", line)
                    continue
                try:
                    entry_path, crc = line.rsplit(
                        " ", maxsplit=1
                    )  # split on the last space, in case the filename contains spaces
                except ValueError:
                    logger.error(
                        "Line is not in the expected format: %(line)s", {"line": line}
                    )
                    continue
                try:
                    file_size = None
                    if (path.parent / entry_path).exists():
                        # SFV files are placed in the same directory as the files they reference
                        # so we should be able to get the size of the file
                        file_size = os.path.getsize(path.parent / entry_path)
                    else:
                        logger.warning(
                            "File '%(entry_path)s' does not exist",
                            {"entry_path": entry_path},
                        )

                    files.append(
                        hash_file.FileEntry(
                            pathlib.Path(entry_path),
                            file_size,
                            False,
                            bytes.fromhex(crc),
                            hash_file.Algo.CRC32,
                        )
                    )
                except ValueError as e:
                    # we want to continue processing the file even if there's an error with one line
                    logger.error(
                        "Error converting '%(line)s' to FileEntry: %(error)s",
                        {"line": line, "error": e},
                    )
        return cls(path, files)
