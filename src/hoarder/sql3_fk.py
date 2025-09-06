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

    def __init__(self, _db_path: str | Path):
        self._db_path = Path(_db_path)
        self._conn = None

    def __enter__(self) -> sqlite3.Connection:
        self._conn = sqlite3.connect(self._db_path)
        _ = self._conn.execute("PRAGMA foreign_keys = ON;")
        return self._conn

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        assert self._conn is not None
        if exc_value is None:
            self._conn.commit()
            self._conn.close()
        else:
            self._conn.rollback()
            self._conn.close()
