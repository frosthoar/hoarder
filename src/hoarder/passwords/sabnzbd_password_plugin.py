"""Password extraction plugin for SABnzbd history databases (history1.db)."""

import logging
import sqlite3
import typing
from pathlib import Path

from .password_plugin import PasswordPlugin
from .password_store import PasswordStore

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.passwords.sabnzbd_password_plugin")

_SELECT_NAME_PASSWORD = """
    SELECT name, password FROM history
    WHERE password IS NOT NULL AND password != '';
"""


class SabnzbdPasswordPlugin(PasswordPlugin):
    """Plugin to extract passwords from a SABnzbd history database.

    Reads the "history" table's name/password columns of a SABnzbd
    history*.db SQLite database (e.g. history1.db).
    """

    _history_paths: list[Path]

    @override
    def __init__(self, config: dict[str, typing.Any]) -> None:
        """Initialize the SabnzbdPasswordPlugin with configuration.

        Args:
            config: Must contain "history_paths", a non-empty list of paths
                to SABnzbd history SQLite databases.

        Raises:
            KeyError: If 'history_paths' is not present in the config dictionary.
            TypeError: If 'history_paths' is not a list.
            ValueError: If 'history_paths' is empty.
            FileNotFoundError: If any path in 'history_paths' is not a valid file.
        """
        if "history_paths" not in config:
            raise KeyError("history_paths not set")
        history_paths = config["history_paths"]
        if not isinstance(history_paths, list):
            raise TypeError("history_paths must be a list")
        if not history_paths:
            raise ValueError("history_paths must map to a non-empty list")
        paths = [Path(p) for p in history_paths]
        missing_paths = [p for p in paths if not p.is_file()]
        if missing_paths:
            raise FileNotFoundError(
                f"No file at {missing_paths[0]}"
                + (
                    f" and {len(missing_paths) - 1} other missing paths"
                    if len(missing_paths) > 1
                    else ""
                )
            )
        self._history_paths = paths

    @staticmethod
    def _read_history_db(db_path: Path) -> PasswordStore:
        """Read name/password pairs from one SABnzbd history database."""
        store = PasswordStore()
        uri = f"{db_path.resolve().as_uri()}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            cur = con.execute(_SELECT_NAME_PASSWORD)
            for name, password in cur.fetchall():
                if not name or not password:
                    continue
                store.add_password(name, password)
        finally:
            con.close()
        return store

    @override
    def extract_passwords(self) -> PasswordStore:
        """Extract passwords from all configured SABnzbd history databases.

        Returns:
            PasswordStore: A PasswordStore containing all extracted name-password pairs.
        """
        password_store = PasswordStore()
        for db_path in self._history_paths:
            try:
                password_store |= self._read_history_db(db_path)
            except (sqlite3.Error, OSError) as exc:
                logger.warning(
                    "Skipping unreadable SABnzbd history database %s: %s",
                    db_path,
                    exc,
                )
        return password_store
