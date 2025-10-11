import abc
from pathlib import Path

from hoarder.sql3_fk import Sqlite3FK

class PasswordRepository(abc.ABC):
    """Abstract base class for a password storage backend."""

    @abc.abstractmethod
    def load(self) -> Dict[str, Set[str]]:
        """Load all passwords and return them as a dict."""
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, data: Dict[str, Set[str]]) -> None:
        """Save the given password dictionary to persistent storage."""
        raise NotImplementedError

class PasswordStoreRepository:
    """Repository for PasswordStore."""

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

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = db_path
        self._create_tables()

    def save(self, title: str, password: str) -> None:
        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            _ = cur.execute("BEGIN;")
            _ = cur.execute(
                "INSERT INTO titles (title) VALUES (:title) ON CONFLICT DO NOTHING;", {"title": title}
            )
            _ = cur.execute(
                    "INSERT INTO passwords(title_id, password) SELECT id AS title_id, :password AS password FROM titles WHERE title = :title", {"password": password, "title": title}
                )
            con.commit()

    def load_all(

    def _create_tables(self) -> None:
        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            _ = cur.execute(PasswordStoreRepository._CREATE_TITLES)
            _ = cur.execute(PasswordStoreRepository._CREATE_PASSWORDS)
