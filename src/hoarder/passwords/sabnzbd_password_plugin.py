"""Password extraction plugin for SABnzbd history databases (history1.db)."""

import logging
import os
import sqlite3
import sys
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

# SABnzbd names its history db from DB_HISTORY_VERSION (constants.py), which
# has been 1 since introduction - i.e. "history1.db" isn't a guess, it's
# SABnzbd's current actual default filename.
_DEFAULT_HISTORY_DB_NAME = "history1.db"


class SabnzbdPasswordPlugin(PasswordPlugin):
    """Plugin to extract passwords from a SABnzbd history database.

    Reads the "history" table's name/password columns of a SABnzbd
    history SQLite database (history1.db).
    """

    _history_paths: list[Path]

    @staticmethod
    def _default_admin_dirs() -> list[Path]:
        """Return SABnzbd's default per-platform admin-directory candidates.

        SABnzbd's own default (Windows: %LOCALAPPDATA%\\sabnzbd\\admin, POSIX:
        ~/.sabnzbd/admin) plus ~/.config/sabnzbd/admin, since some POSIX
        packages/services set up SABnzbd to follow the XDG base directory
        convention instead.
        """
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            return [Path(local_appdata) / "sabnzbd" / "admin"] if local_appdata else []
        home = Path.home()
        return [home / ".config" / "sabnzbd" / "admin", home / ".sabnzbd" / "admin"]

    @classmethod
    def _autodetect_history_paths(cls) -> list[Path]:
        """Return existing default-location history db paths for this platform."""
        candidates = (d / _DEFAULT_HISTORY_DB_NAME for d in cls._default_admin_dirs())
        return [p for p in candidates if p.is_file()]

    @override
    def __init__(self, config: dict[str, typing.Any]) -> None:
        """Initialize the SabnzbdPasswordPlugin with configuration.

        Args:
            config: "history_paths" (list of paths to SABnzbd history SQLite
                databases) and/or "auto_detect_history_paths" (bool, default
                True) to additionally look for a history db under SABnzbd's
                default per-platform admin directory. Defaulting to True
                means zero-config usage works out of the box; set it to False
                to require 'history_paths' to be given explicitly instead. At
                least one of the two must yield a database; explicit and
                auto-detected paths are merged and deduplicated.

        Raises:
            KeyError: If 'history_paths' is absent and
                'auto_detect_history_paths' is explicitly set to False.
            TypeError: If 'history_paths' is present and not a list, or
                'auto_detect_history_paths' is present and not a bool.
            ValueError: If no history database paths result from either
                'history_paths' or auto-detection.
            FileNotFoundError: If any explicit path in 'history_paths' is not
                a valid file.
        """
        auto_detect = config.get("auto_detect_history_paths", True)
        if not isinstance(auto_detect, bool):
            raise TypeError("auto_detect_history_paths must be a bool")

        if "history_paths" not in config and not auto_detect:
            raise KeyError("history_paths not set")

        history_paths = config.get("history_paths", [])
        if not isinstance(history_paths, list):
            raise TypeError("history_paths must be a list")
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

        if auto_detect:
            paths += self._autodetect_history_paths()

        if not paths:
            raise ValueError(
                "history_paths must map to a non-empty list, or "
                "auto_detect_history_paths must locate a SABnzbd history database"
            )
        self._history_paths = list({p.resolve(): p for p in paths}.values())

    def __repr__(self) -> str:
        paths = [str(p) for p in self._history_paths]
        return f"{self.__class__.__name__}(history_paths={paths})"

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
        loaded = 0
        for db_path in self._history_paths:
            logger.info("Reading SABnzbd history database %s", db_path)
            try:
                db_store = self._read_history_db(db_path)
            except (sqlite3.Error, OSError) as exc:
                logger.warning(
                    "Skipping unreadable SABnzbd history database %s: %s",
                    db_path,
                    exc,
                )
                continue
            logger.info("Loaded %d entries from %s", len(db_store), db_path)
            password_store |= db_store
            loaded += 1
        logger.info(
            "Loaded %d entries from %d SABnzbd history database(s)",
            len(password_store),
            loaded,
        )
        return password_store
