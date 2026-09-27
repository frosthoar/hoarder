"""NZB password extraction plugin."""

import logging
import os
import pathlib
import re
import traceback
import xml.etree.ElementTree as ET
from typing import Callable, NamedTuple

from ..archives import RarArchiveError, RarPasswordError
from ..archives.rar_archive import RarArchive
from ..utils import pprint
from .password_plugin import PasswordPlugin
from .password_store import PasswordStore

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.passwords.nzb_password_plugin")


class ArchiveEntry(NamedTuple):
    title: str
    password: str | None


class SecureArchiveEntry(NamedTuple):
    title: str
    password: str


class DirectoryScanResult(NamedTuple):
    """Result of scanning one configured NZB directory.

    fully_scanned is False if nzb_directory or any subdirectory of it
    couldn't be listed (e.g. it no longer exists or isn't readable) - such a
    failure doesn't discard passwords already found elsewhere in the tree,
    since os.walk keeps walking whatever siblings it still can.
    """

    passwords: PasswordStore
    fully_scanned: bool


class NzbPasswordPlugin(PasswordPlugin):
    """Plugin to extract passwords from NZB filenames with {{password}} format."""

    # Maps each configured NZB directory to whether it was successfully
    # scanned on the most recent extract_passwords() call.
    _nzb_paths: dict[pathlib.Path, bool]

    @override
    def __init__(self, config: dict[str, list[str]]):
        """Initialize the NzbPasswordPlugin with configuration.

        Args:
            config (dict[str, list[str]]): Configuration dictionary

        Raises:
            KeyError: If 'nzb_paths' is not present in the config dictionary.
            TypeError: If 'nzb_paths' is not a list.
            ValueError: If 'nzb_paths' is empty.
            NotADirectoryError: If any path in 'nzb_paths' is not a valid directory.
        """
        if "nzb_paths" not in config:
            raise KeyError("nzb_paths not set")
        nzb_paths = config["nzb_paths"]
        if not isinstance(nzb_paths, list):
            raise TypeError("nzb_paths must be a list")
        if not nzb_paths:
            raise ValueError("nzb_paths must map to a non-empty list")
        paths = [pathlib.Path(p) for p in nzb_paths]
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
        self._nzb_paths = {p: False for p in paths}

    def __repr__(self) -> str:
        paths = [str(p) for p in self._nzb_paths]
        return f"{self.__class__.__name__}(nzb_paths={paths})"

    @staticmethod
    def _extract_pw_from_filename(
        file_path: pathlib.PurePath,
    ) -> ArchiveEntry:
        """Extract the password from a filename using the {{password}} pattern.

        Used for both NZB filenames and RAR filenames wrapping password-
        protected NZBs (e.g. "release{{secret}}.rar").

        Args:
            file_path (pathlib.PurePath): Path to the file.

        Returns:
            ArchiveEntry: title and password (password may be empty if extraction was unsuccesful)

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
            return ArchiveEntry(title=title, password=None)
        return ArchiveEntry(title=title, password=filename_passwords[0])

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
        return password

    @staticmethod
    def _process_file(
        p: pathlib.PurePath,
        read_file_content: Callable[[pathlib.PurePath], bytes | str],
    ) -> SecureArchiveEntry | None:
        """Process an NZB file to extract its title and password.

        Args:
            p (pathlib.PurePath): Path to the file to process.
            read_file_content (Callable[[pathlib.PurePath], bytes | str]): Function to read the file content.

        Returns:
            SecureArchiveEntry: contains title and password if both are found, otherwise None.
        """
        logger.debug(f"Read {p}... extracting passwords")
        title: str | None = None
        password: str | None = None
        if p.suffix == ".nzb":
            (
                title,
                password,
            ) = NzbPasswordPlugin._extract_pw_from_filename(p)
            if not password:
                content = read_file_content(p)
                password = NzbPasswordPlugin._extract_pw_from_nzb_file_content(content)
        if title and password:
            return SecureArchiveEntry(title=title, password=password)
        else:
            return None

    @staticmethod
    def _process_directory(
        nzb_directory: pathlib.Path,
    ) -> DirectoryScanResult:
        """Process all NZB and RAR files in a directory to extract passwords.

        Args:
            nzb_directory (pathlib.Path): Directory containing NZB and RAR files.

        Returns:
            DirectoryScanResult: passwords found, plus whether the whole
            tree was listed without error - see DirectoryScanResult.
        """
        dir_store = PasswordStore()
        walk_errors: list[OSError] = []
        for root, _, files in os.walk(nzb_directory, onerror=walk_errors.append):
            for file in files:
                full_path: pathlib.Path = pathlib.Path(root) / file
                if full_path.suffix == ".nzb":
                    try:
                        title_password = NzbPasswordPlugin._process_file(
                            full_path,
                            read_file_content=lambda fp: open(fp, "r").read(),
                        )
                    except (OSError, UnicodeDecodeError) as exc:
                        logger.warning("Skipping unreadable NZB %s: %s", full_path, exc)
                        continue
                    if title_password:
                        dir_store.add_password(*title_password)
                elif full_path.suffix == ".rar":
                    logger.debug(f"Processing RARed NZB(s) {full_path}")
                    relative_path = full_path.relative_to(nzb_directory)
                    try:
                        (
                            _,
                            filename_password,
                        ) = NzbPasswordPlugin._extract_pw_from_filename(full_path)
                    except ValueError:
                        # Ambiguous {{...}} groups in the filename - fall back
                        # to opening without a password rather than aborting.
                        filename_password = None
                    try:
                        rar_file: RarArchive = RarArchive.from_path(
                            nzb_directory, relative_path, password=filename_password
                        )
                    except RarPasswordError:
                        logger.warning(
                            "Skipping password-protected RAR %s: no working "
                            "password found",
                            full_path,
                        )
                        continue
                    except (RarArchiveError, OSError) as exc:
                        # OSError alongside RarArchiveError: RarArchive.from_path
                        # raises a bare FileNotFoundError if the RAR vanishes
                        # between os.walk's listing and this call - that must
                        # skip just this file, not fall through to the whole
                        # directory being treated as unreadable.
                        logger.warning("Skipping unreadable RAR %s: %s", full_path, exc)
                        continue
                    for file_entry in rar_file.files:
                        logger.debug(f"Read {file_entry.path}... extracting passwords")
                        try:
                            title_password = NzbPasswordPlugin._process_file(
                                file_entry.path,
                                read_file_content=lambda fp: rar_file.read_file(
                                    file_entry.path
                                ),
                            )
                        except (OSError, UnicodeDecodeError, RarArchiveError) as exc:
                            logger.warning(
                                "Skipping unreadable archive entry %s in %s: %s",
                                file_entry.path,
                                full_path,
                                exc,
                            )
                            continue
                        if title_password:
                            dir_store.add_password(*title_password)
        for walk_exc in walk_errors:
            logger.warning(
                "Failed to list part of NZB directory %s: %s", nzb_directory, walk_exc
            )
        return DirectoryScanResult(dir_store, not walk_errors)

    @override
    def extract_passwords(self) -> PasswordStore:
        """Extract passwords from all configured NZB directories.

        Returns:
            PasswordStore: A PasswordStore containing all extracted title-password pairs.
        """
        password_store = PasswordStore()
        for p in self._nzb_paths:
            logger.info("Reading NZB directory %s", p)
            dir_store, fully_scanned = NzbPasswordPlugin._process_directory(p)
            logger.info("Found %d entries in %s", len(dir_store), p)
            password_store |= dir_store
            self._nzb_paths[p] = fully_scanned
        logger.info(
            "Found %d entries across %d NZB directories",
            len(password_store),
            sum(self._nzb_paths.values()),
        )
        return password_store


if __name__ == "__main__":
    config = {"nzb_paths": [r"D:\nzbs"]}
    plug_instance = NzbPasswordPlugin(config)
    password_store = plug_instance.extract_passwords()
    pprint(password_store)
