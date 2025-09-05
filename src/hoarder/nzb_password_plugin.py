"""NZB password extraction plugin."""

import logging
import os
import pathlib
import re
import traceback
import xml.etree.ElementTree as ET
from typing import Callable

import hoarder
from hoarder.password_plugin import PasswordPlugin

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.nzb_password_plugin")


class NzbPasswordPlugin(PasswordPlugin):
    """Plugin to extract passwords from NZB filenames with {{password}} format."""

    _nzb_paths: list[pathlib.Path]

    @override
    def __init__(self, config: dict[str, list[str]]):
        """Initialize the NzbPasswordPlugin with configuration.

        Args:
            config (dict[str, list[str]]): Configuration dictionary

        Raises:
            KeyError: If 'nzb_paths' is not present in the config dictionary.
            ValueError: If 'nzb_paths' is empty.
            NotADirectoryError: If any path in 'nzb_paths' is not a valid directory.
        """
        if "nzb_paths" not in config:
            raise KeyError("nzb_paths not set")
        if not config["nzb_paths"]:
            raise ValueError("nzb_paths must map to a list")
        paths = [pathlib.Path(p) for p in config["nzb_paths"]]
        invalid_paths = [p for p in paths if not p.is_dir()]
        if invalid_paths:
            raise NotADirectoryError(
                f"No directory at {invalid_paths[0]}"
                + (
                    f" and {len(invalid_paths) - 1} other invalid paths"
                    if len(invalid_paths) > 1
                    else ""
                )
            )
        self._nzb_paths = paths

    @staticmethod
    def _extract_pw_from_nzb_filename(
        file_path: pathlib.PurePath,
    ) -> tuple[str, str | None]:
        """Extract the password from an NZB filename using the {{password}} pattern.

        Args:
            file_path (pathlib.PurePath): Path to the NZB file.

        Returns:
            tuple[str, str | None]: A tuple containing the cleaned title and the extracted password, or None if no password is found.

        Raises:
            ValueError: If multiple passwords are found in the filename, indicating ambiguity.
        """
        filename = file_path.stem
        filename_passwords = re.findall(r"\{\{(.+?)\}\}", filename)
        title = re.sub(r"\{\{.+?\}\}", "", filename).strip()
        if len(filename_passwords) >= 2:
            logger.error(f"Error when extracting password from {file_path}")
            raise ValueError("Ambiguous passwords")
        if len(filename_passwords) == 0:
            return (title, None)
        return (title, filename_passwords[0])

    @staticmethod
    def _extract_pw_from_nzb_file_content(content: bytes | str) -> str | None:
        """Extract password from NZB file content within <header><meta type="password">password</meta></header>.

        Args:
            content (bytes | str): The content of the NZB file.

        Returns:
            str | None: The extracted password, or None if no password is found or extraction fails.
        """
        password: str | None = None
        try:
            logger.debug("Extracting password from file content")

            root = ET.fromstring(content)
            ns = {"nzb": "http://www.newzbin.com/DTD/2003/nzb"}

            for meta in root.findall('.//nzb:meta[@type="password"]', ns):
                if meta.text:
                    password = meta.text.strip()
                    break
        except (ET.ParseError, OSError, UnicodeDecodeError):
            logger.debug("Failure extracting password from content")
            print(traceback.format_exc())
            pass
        return password

    @staticmethod
    def _process_file(
        p: pathlib.PurePath,
        read_file_content: Callable[[pathlib.PurePath], bytes | str],
    ) -> tuple[str, str] | None:
        """Process an NZB file to extract its title and password.

        Args:
            p (pathlib.PurePath): Path to the file to process.
            read_file_content (Callable[[pathlib.PurePath], bytes | str]): Function to read the file content.

        Returns:
            tuple[str, str] | None: A tuple of title and password if both are found, otherwise None.
        """
        logger.debug(f"Read {p}... extracting passwords")
        title: str | None = None
        password: str | None = None
        if p.suffix == ".nzb":
            (
                title,
                password,
            ) = NzbPasswordPlugin._extract_pw_from_nzb_filename(p)
            if not password:
                content = read_file_content(p)
                password = NzbPasswordPlugin._extract_pw_from_nzb_file_content(content)
        if title and password:
            return title, password

    @staticmethod
    def _process_directory(
        nzb_directory: pathlib.Path,
    ) -> hoarder.password_store.PasswordStore:
        """Process all NZB and RAR files in a directory to extract passwords.

        Args:
            nzb_directory (pathlib.Path): Directory containing NZB and RAR files.

        Returns:
            hoarder.password_store.PasswordStore: A PasswordStore containing extracted title-password pairs.
        """
        dir_store = hoarder.password_store.PasswordStore()
        for root, _, files in os.walk(nzb_directory):
            for file in files:
                full_path: pathlib.Path = nzb_directory / root / file
                if full_path.suffix == ".nzb":
                    title_password = NzbPasswordPlugin._process_file(
                        full_path, read_file_content=lambda fp: open(fp, "r").read()
                    )
                    if title_password:
                        dir_store.add_password(*title_password)
                elif full_path.suffix == ".rar":
                    logger.debug(f"Processing RARed NZB(s) {full_path}")
                    rar_file: hoarder.RarArchive = hoarder.RarArchive.from_path(
                        full_path
                    )
                    for file_entry in rar_file.files:
                        logger.debug(f"Read {file_entry.path}... extracting passwords")
                        title_password = NzbPasswordPlugin._process_file(
                            file_entry.path,
                            read_file_content=lambda fp: rar_file.read_file(
                                file_entry.path
                            ),
                        )
                        if title_password:
                            dir_store.add_password(*title_password)
        return dir_store

    @override
    def extract_passwords(self) -> hoarder.password_store.PasswordStore:
        """Extract passwords from all configured NZB directories.

        Returns:
            hoarder.password_store.PasswordStore: A PasswordStore containing all extracted title-password pairs.
        """
        password_store = hoarder.password_store.PasswordStore()
        for p in self._nzb_paths:
            password_store = password_store | NzbPasswordPlugin._process_directory(p)
        return password_store


if __name__ == "__main__":
    config = {"nzb_paths": [r"D:\nzbs"]}
    plug_instance = NzbPasswordPlugin(config)
    password_store = plug_instance.extract_passwords()
    print(password_store.pretty_print())
