import collections.abc
import datetime
import sqlite3
from pathlib import Path, PurePath
from types import TracebackType
from typing import cast

from hoarder.hash_archive import Algo, FileEntry, HashArchive
from hoarder.hash_name_archive import HashEnclosure, HashNameArchive
from hoarder.rar_archive import RarArchive
from hoarder.rar_path import RarScheme
from hoarder.sfv_archive import SfvArchive


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


class HashArchiveRepository:
    """Repository for any HashArchive subclass."""

    _db_path: str | Path

    _CREATE_HASH_ARCHIVES: str = """
    CREATE TABLE IF NOT EXISTS hash_archives (
        id             INTEGER  PRIMARY KEY AUTOINCREMENT,
        type           TEXT     NOT NULL,
        path           TEXT     NOT NULL UNIQUE,
        is_deleted        INTEGER,
        timestamp      TEXT     DEFAULT CURRENT_TIMESTAMP,
        -- HashNameArchive
        hash_enclosure TEXT,
        -- RarArchive
        password       TEXT,
        rar_scheme     INTEGER,
        rar_version    TEXT,
        n_volumes      INTEGER
    );
    """

    _CREATE_FILE_ENTRIES: str = """
    CREATE TABLE IF NOT EXISTS file_entries (
        id          INTEGER  PRIMARY KEY AUTOINCREMENT,
        path        TEXT     NOT NULL,
        size        INTEGER,
        is_dir      INTEGER  NOT NULL,
        hash_value  BLOB,
        algo        INTEGER,
        archive_id  INTEGER  NOT NULL,
        FOREIGN KEY (archive_id)
          REFERENCES hash_archives(id)
          ON DELETE CASCADE
    );
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = db_path
        self._create_tables()

    def save(self, archive: HashArchive) -> None:
        """Insert or replace one archive and all its FileEntry rows."""
        archive_row = self._build_archive_row(archive)

        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            _ = cur.execute("BEGIN;")
            _ = cur.execute(
                "DELETE FROM hash_archives WHERE path = ?;", (archive_row["path"],)
            )
            _ = cur.execute(
                f"""
                INSERT INTO hash_archives ({', '.join(archive_row)})
                VALUES ({', '.join(':' + k for k in archive_row)});
                """,
                archive_row,
            )

            if archive.files:
                fe_rows = list(
                    self._build_fileentry_rows(archive.files, archive_path=archive.path)
                )
                _ = cur.executemany(
                    """
                    INSERT INTO file_entries (path, size, is_dir, hash_value, algo, archive_id)
                    SELECT :path AS path, :size AS size, :is_dir AS is_dir, :hash_value AS hash_value,
                    :algo AS algo, id as archive_id FROM hash_archives WHERE path = :archive_path
                    """,
                    fe_rows,
                )
            con.commit()

    def load(self, path: Path | str) -> HashArchive | None:
        """Return the archive (plus its FileEntry set) previously stored."""
        with Sqlite3FK(self._db_path) as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            arc_row = cast(
                None | sqlite3.Row,
                cur.execute(
                    "SELECT * FROM hash_archives WHERE path = :path;",
                    {"path": str(path)},
                ).fetchone(),
            )

            if arc_row is None:
                raise FileNotFoundError(str(path))

            archive = self._fill_archive(arc_row)

            fe_rows = cast(
                list[sqlite3.Row],
                cur.execute(
                    "SELECT * FROM file_entries WHERE archive_id = ?;", (arc_row["id"],)
                ).fetchall(),
            )

            archive.files = {
                FileEntry(
                    path=PurePath(cast(str, r["path"])),
                    size=cast(int, r["size"]),
                    is_dir=bool(cast(int, r["is_dir"])),
                    hash_value=cast(bytes, r["hash_value"]),
                    algo=Algo(r["algo"]) if r["algo"] is not None else None,
                )
                for r in fe_rows
            }
            return archive

    def _create_tables(self) -> None:
        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            _ = cur.execute(HashArchiveRepository._CREATE_HASH_ARCHIVES)
            _ = cur.execute(HashArchiveRepository._CREATE_FILE_ENTRIES)

    @staticmethod
    def _now() -> str:
        return datetime.datetime.strftime(
            datetime.datetime.now().astimezone(), "%Y-%m-%d %H:%M:%S%z"
        )

    def _build_archive_row(self, arch: HashArchive) -> dict[str, str | int | None]:
        """Return a dict used directly with named-parameter SQL."""
        base: dict[str, str | int | None] = {
            "type": type(arch).__name__,
            "path": str(arch.path),
            "is_deleted": int(arch.is_deleted),
            "hash_enclosure": None,
            "password": None,
            "rar_scheme": None,
            "rar_version": None,
            "n_volumes": None,
        }
        if isinstance(arch, HashNameArchive):
            base["hash_enclosure"] = arch.enc.value
        elif isinstance(arch, RarArchive):
            base.update(
                password=arch.password,
                rar_scheme=arch.scheme.value if arch.scheme else None,
                rar_version=arch.version,
                n_volumes=arch.n_volumes,
            )
        elif isinstance(arch, SfvArchive):
            pass
        else:
            raise TypeError(f"Unsupported HashArchive subclass: {type(arch).__name__}")
        return base

    @staticmethod
    def _build_fileentry_rows(
        entries: collections.abc.Iterable[FileEntry],
        archive_path: str | Path | None = None,
    ) -> collections.abc.Iterable[dict[str, str | int | None | bytes]]:
        for fe in entries:
            ret_dict: dict[str, str | int | None | bytes] = {
                "path": str(fe.path),
                "size": fe.size,
                "is_dir": int(fe.is_dir),
                "hash_value": fe.hash_value,
                "algo": fe.algo.value if fe.algo is not None else None,
            }
            if archive_path:
                ret_dict.update(archive_path=str(archive_path))
            yield (ret_dict)

    @staticmethod
    def _fill_archive(row: sqlite3.Row) -> HashArchive:
        archive_type = cast(str, row["type"])
        archive_path = cast(str, row["path"])
        arch: HashArchive | None = None
        if archive_type == "HashNameArchive":
            arch = HashNameArchive(
                Path(archive_path),
                files=None,
                enc=HashEnclosure(row["hash_enclosure"]),
            )
        elif archive_type == "RarArchive":
            arch = RarArchive(
                Path(archive_path),
                files=None,
                password=cast(str, row["password"]),
                version=cast(str, row["rar_version"]),
                scheme=(
                    RarScheme(cast(int, row["rar_scheme"]))
                    if row["rar_scheme"] is not None
                    else None
                ),
                n_volumes=cast(int, row["n_volumes"]),
            )
        elif archive_type == "SfvArchive":
            arch = SfvArchive(Path(archive_path), files=set())
        else:
            raise ValueError(f"Unknown archive type in databaase: {archive_type}")

        arch.is_deleted = bool(cast(int, row["is_deleted"]))
        return arch
