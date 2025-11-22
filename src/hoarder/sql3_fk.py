import sqlite3
from pathlib import Path
from types import TracebackType


class Sqlite3FK:
    """
    Context-manager that turns ON foreign-key enforcement,
    and actually closes the connection.
    Does not suppress any encountered exceptions.
    """

    _db_path: Path
    _conn: sqlite3.Connection | None

    def __init__(self, db_path: str | Path):
        """Initialize the context manager with the database path."""
        self._db_path = Path(db_path)
        self._conn = None

    def __enter__(self) -> sqlite3.Connection:
        """Enter the context manager and return a connection with foreign keys enabled."""
        self._conn = sqlite3.connect(self._db_path)
        _ = self._conn.execute("PRAGMA foreign_keys = ON;")
        return self._conn

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the context manager, committing or rolling back, then closing the connection."""
        if self._conn is None:
            return
        try:
            if exc_value is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()
