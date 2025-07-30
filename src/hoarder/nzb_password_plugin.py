"""NZB password extraction plugin."""

import logging
import os
import pathlib
import re
import traceback
import xml.etree.ElementTree as ET

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
        if "nzb_paths" in config:
            paths = [pathlib.Path(p) for p in config["nzb_paths"]]
            invalid_paths = [p for p in paths if not p.is_dir()]
            if len(invalid_paths) > 0:
                raise FileNotFoundError(
                    f"No directory at {invalid_paths[0]}"
                    + (
                        f" and {len(invalid_paths) - 1} other invalid paths"
                        if len(invalid_paths) > 1
                        else ""
                    )
                )
            else:
                self._nzb_paths = paths

    @staticmethod
    def _extract_pw_from_nzb_filename(
        file_path: pathlib.PurePath,
    ) -> tuple[str, str | None]:
        filename = file_path.stem
        # Extract the password from title{{password}}.nzb pattern
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
    def _process_directory(
        nzb_directory: pathlib.Path,
    ) -> hoarder.password_store.PasswordStore:
        dir_store = hoarder.password_store.PasswordStore()
        for root, _, files in os.walk(nzb_directory):
            for file in files:
                title = password = None
                full_path: pathlib.Path = nzb_directory / root / file
                if full_path.suffix == ".nzb":
                    logger.debug(f"Processing NZB {full_path}")
                    title, password = NzbPasswordPlugin._extract_pw_from_nzb_filename(
                        full_path
                    )
                    if not password:
                        logger.debug("No password in filename, opening NZB file...")
                        with open(full_path) as f:
                            content = f.read()
                            password = (
                                NzbPasswordPlugin._extract_pw_from_nzb_file_content(
                                    content
                                )
                            )
                    if password:
                        dir_store.add_password(title, password)
                elif full_path.suffix == "rar":
                    logger.debug(f"Processing RARed NZB(s) {full_path}")
                    rar_file: hoarder.RarArchive = hoarder.RarArchive.from_path(
                        full_path
                    )
                    for file_entry in rar_file.files:
                        logger.debug(f"Read {file_entry.path}... extracting passwords")
                        if file_entry.path.suffix == ".nzb":
                            (
                                title,
                                password,
                            ) = NzbPasswordPlugin._extract_pw_from_nzb_filename(
                                file_entry.path
                            )
                            if not password:
                                content = rar_file.read_file(file_entry.path)
                                password = (
                                    NzbPasswordPlugin._extract_pw_from_nzb_file_content(
                                        content
                                    )
                                )
                            if password:
                                dir_store.add_password(title, password)
        return dir_store

    @override
    def extract_passwords(self) -> hoarder.password_store.PasswordStore:
        password_store = hoarder.password_store.PasswordStore()
        for p in self._nzb_paths:
            password_store = password_store | NzbPasswordPlugin._process_directory(p)
        return password_store


if __name__ == "__main__":
    config = {"nzb_paths": [r"D:\nzbs"]}
    plug_instance = NzbPasswordPlugin(config)
    password_store = plug_instance.extract_passwords()
    print(password_store.pretty_print())
