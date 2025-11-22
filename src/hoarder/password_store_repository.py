import abc
import json
from pathlib import Path

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

from hoarder.password_store import PasswordStore
from hoarder.sql3_fk import Sqlite3FK


class PasswordRepository(abc.ABC):
    """Abstract base class for a password storage backend."""

    @abc.abstractmethod
    def load_all(self) -> PasswordStore:
        """Load all passwords and return them as a PasswordStore."""
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, store: PasswordStore) -> None:
        """Save the given PasswordStore to persistent storage."""
        raise NotImplementedError


class PasswordSqlite3Repository(PasswordRepository):
    """Repository for PasswordStore using SQLite3 backend."""

    _db_path: str | Path

    _CREATE_TITLES: str = """
    CREATE TABLE IF NOT EXISTS titles (
        id             INTEGER  PRIMARY KEY AUTOINCREMENT,
        title          TEXT     NOT NULL UNIQUE,
        timestamp      TEXT     DEFAULT CURRENT_TIMESTAMP
    );
    """

    _CREATE_PASSWORDS: str = """
    CREATE TABLE IF NOT EXISTS passwords (
        id             INTEGER  PRIMARY KEY AUTOINCREMENT,
        password       TEXT     NOT NULL,
        timestamp      TEXT     DEFAULT CURRENT_TIMESTAMP,
        title_id       INTEGER  NOT NULL,
        FOREIGN KEY (title_id)
          REFERENCES titles(id)
          ON DELETE CASCADE,
        UNIQUE(title_id, password) ON CONFLICT IGNORE
    );
    """

    @staticmethod
    def _create_tables(db_path: str | Path) -> None:
        """Create the database tables if they don't exist."""
        with Sqlite3FK(db_path) as con:
            cur = con.cursor()
            _ = cur.execute(PasswordSqlite3Repository._CREATE_TITLES)
            _ = cur.execute(PasswordSqlite3Repository._CREATE_PASSWORDS)

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the repository with the given database path."""
        self._db_path = db_path
        self._create_tables(self._db_path)

    @override
    def save(self, store: PasswordStore) -> None:
        """Save the given PasswordStore to persistent storage."""
        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            title: str
            passwords: set[str]
            for title, passwords in store:
                _ = cur.execute(
                    "INSERT INTO titles (title) VALUES (:title) ON CONFLICT DO NOTHING;",
                    {"title": title},
                )
                for password in passwords:
                    _ = cur.execute(
                        "INSERT INTO passwords(title_id, password) SELECT id AS title_id, :password AS password FROM titles WHERE title = :title",
                        {"password": password, "title": title},
                    )

    @override
    def load_all(self) -> PasswordStore:
        """Load all passwords and return them as a PasswordStore."""
        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            _ = cur.execute(
                "SELECT title, json_group_array(password) FROM titles JOIN passwords ON titles.id = passwords.title_id GROUP BY title ORDER BY title;"
            )
            ret = cur.fetchall()
        data = {title: set(json.loads(passwords)) for title, passwords in ret}
        return PasswordStore(data)
