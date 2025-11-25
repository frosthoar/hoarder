import collections.abc
import sqlite3
from pathlib import Path, PurePath
from typing import cast

from ..utils.sql3_fk import Sqlite3FK
from .hash_archive import Algo, FileEntry, HashArchive
from .hash_name_archive import HashEnclosure, HashNameArchive
from .rar_archive import RarArchive
from .rar_path import RarScheme
from .sfv_archive import SfvArchive


class HashArchiveRepository:
    """Repository for any HashArchive subclass."""

    _db_path: str | Path

    _CREATE_STORAGE_PATHS: str = """
    CREATE TABLE IF NOT EXISTS storage_paths (
        id             INTEGER  PRIMARY KEY AUTOINCREMENT,
        storage_path   TEXT     NOT NULL UNIQUE
    );
    """

    _CREATE_HASH_ARCHIVES: str = """
    CREATE TABLE IF NOT EXISTS hash_archives (
        id             INTEGER  PRIMARY KEY AUTOINCREMENT,
        type           TEXT     NOT NULL,
        storage_path_id        INTEGER  NOT NULL,
        path           TEXT     NOT NULL,
        is_deleted        INTEGER,
        timestamp      TEXT     DEFAULT CURRENT_TIMESTAMP,
        -- HashNameArchive
        hash_enclosure TEXT,
        -- RarArchive
        password       TEXT,
        rar_scheme     INTEGER,
        rar_version    TEXT,
        n_volumes      INTEGER,
        FOREIGN KEY (storage_path_id)
          REFERENCES storage_paths(id)
          ON DELETE CASCADE,
        UNIQUE(storage_path_id, path)
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
        storage_path_str = str(archive.storage_path.resolve())
        archive_path_str = str(archive_row["path"])

        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            # Insert or get storage path (needed for foreign key constraint)
            _ = cur.execute(
                "INSERT OR IGNORE INTO storage_paths (storage_path) VALUES (?);",
                (storage_path_str,),
            )

            # Delete existing archive with same storage_path and path using subquery
            _ = cur.execute(
                """
                DELETE FROM hash_archives 
                WHERE storage_path_id = (SELECT id FROM storage_paths WHERE storage_path = ?)
                  AND path = ?;
                """,
                (storage_path_str, archive_path_str),
            )

            _ = cur.execute(
                f"""
                INSERT INTO hash_archives ({', '.join(archive_row.keys())}, storage_path_id)
                SELECT {', '.join([':' + k + ' AS ' + k for k in archive_row.keys()])}, (SELECT id FROM storage_paths WHERE storage_path = :storage_path)
                """,
                archive_row | {"storage_path": storage_path_str},
            )

            if archive.files:
                fe_rows = list(
                    self._build_fileentry_rows(
                        archive.files,
                        storage_path=storage_path_str,
                        archive_path=archive_path_str,
                    )
                )
                _ = cur.executemany(
                    """
                    INSERT INTO file_entries (path, size, is_dir, hash_value, algo, archive_id)
                    SELECT :path AS path, :size AS size, :is_dir AS is_dir, :hash_value AS hash_value,
                    :algo AS algo, hash_archives.id as archive_id 
                    FROM hash_archives 
                    JOIN storage_paths ON hash_archives.storage_path_id = storage_paths.id
                    WHERE storage_paths.storage_path = :storage_path AND hash_archives.path = :archive_path
                    """,
                    fe_rows,
                )

    def load(self, storage_path: Path, path: PurePath | str) -> HashArchive:
        """Return the archive (plus its FileEntry set) previously stored.

        Args:
            storage_path: The storage directory path
            path: The relative path from storage_path

        Raises:
            FileNotFoundError: If the archive with the given storage_path and path is not found.
        """
        storage_path_str = str(storage_path.resolve())
        path_str = str(path)

        with Sqlite3FK(self._db_path) as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            # Get archive with storage_path using JOIN
            arc_row = cast(
                None | sqlite3.Row,
                cur.execute(
                    """
                    SELECT hash_archives.*, storage_paths.storage_path 
                    FROM hash_archives 
                    JOIN storage_paths ON hash_archives.storage_path_id = storage_paths.id
                    WHERE storage_paths.storage_path = ? AND hash_archives.path = ?;
                    """,
                    (storage_path_str, path_str),
                ).fetchone(),
            )

            if arc_row is None:
                raise FileNotFoundError(
                    f"Archive not found: {storage_path_str}/{path_str}"
                )

            # Get storage_path from the joined row
            archive_storage_path = Path(cast(str, arc_row["storage_path"]))
            archive = self._fill_archive(arc_row, archive_storage_path)

            fe_rows = cast(
                list[sqlite3.Row],
                cur.execute(
                    "SELECT * FROM file_entries WHERE archive_id = ?;", (arc_row["id"],)
                ).fetchall(),
            )

            archive.files = {
                FileEntry(
                    path=PurePath(cast(str, r["path"])),
                    size=cast(int | None, r["size"]),
                    is_dir=bool(cast(int, r["is_dir"])),
                    hash_value=cast(bytes | None, r["hash_value"]),
                    algo=Algo(r["algo"]) if r["algo"] is not None else None,
                )
                for r in fe_rows
            }
            return archive

    def _create_tables(self) -> None:
        """Create the database tables if they don't exist."""
        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            _ = cur.execute(HashArchiveRepository._CREATE_STORAGE_PATHS)
            _ = cur.execute(HashArchiveRepository._CREATE_HASH_ARCHIVES)
            _ = cur.execute(HashArchiveRepository._CREATE_FILE_ENTRIES)

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
        storage_path: str | None = None,
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
            if storage_path:
                ret_dict["storage_path"] = storage_path
            if archive_path:
                ret_dict.update(archive_path=str(archive_path))
            yield ret_dict

    @staticmethod
    def _fill_archive(row: sqlite3.Row, storage_path: Path) -> HashArchive:
        archive_type = cast(str, row["type"])
        archive_path = cast(str, row["path"])
        arch: HashArchive | None = None
        if archive_type == "HashNameArchive":
            arch = HashNameArchive(
                storage_path,
                PurePath(archive_path),
                files=None,
                enc=HashEnclosure(row["hash_enclosure"]),
            )
        elif archive_type == "RarArchive":
            arch = RarArchive(
                storage_path,
                PurePath(archive_path),
                files=None,
                password=cast(str | None, row["password"]),
                version=cast(str | None, row["rar_version"]),
                scheme=(
                    RarScheme(cast(int, row["rar_scheme"]))
                    if row["rar_scheme"] is not None
                    else None
                ),
                n_volumes=cast(int | None, row["n_volumes"]),
            )
        elif archive_type == "SfvArchive":
            arch = SfvArchive(storage_path, PurePath(archive_path), files=set())
        else:
            raise ValueError(f"Unknown archive type in database: {archive_type}")

        arch.is_deleted = bool(cast(int, row["is_deleted"]))
        return arch
