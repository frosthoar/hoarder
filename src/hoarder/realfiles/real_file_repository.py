from __future__ import annotations

import collections.abc
import datetime as dt
import sqlite3
from pathlib import Path, PurePath
from typing import Iterable

from hoarder.archives.hash_archive import Algo, HashArchive
from hoarder.archives.hash_archive_repository import HashArchiveRepository
from hoarder.realfiles.real_file import RealFile, Verification, VerificationSource
from hoarder.utils.db_schema import ensure_repository_tables
from hoarder.utils.sql3_fk import Sqlite3FK


class RealFileRepository:
    """Repository handling persistence for RealFile and Verification instances."""

    _db_path: str | Path
    _allowed_storage_paths: set[Path]

    def __init__(
        self,
        db_path: str | Path,
        allowed_storage_paths: Iterable[Path],
    ) -> None:
        self._db_path = db_path
        normalized_paths: list[Path] = []
        for path in allowed_storage_paths:
            normalized = path.resolve()
            if not normalized.exists():
                raise FileNotFoundError(
                    f"Storage path does not exist on disk: {normalized}"
                )
            normalized_paths.append(normalized)
        self._allowed_storage_paths = set(normalized_paths)
        ensure_repository_tables(self._db_path)
        self._initialize_storage_paths()

    def save(self, real_file: RealFile) -> None:
        """Insert or replace a RealFile and its verifications."""
        normalized_storage_path = self._check_storage_path_allowed(
            real_file.storage_path
        )
        storage_path_str = str(normalized_storage_path)
        real_file_row = self._build_real_file_row(real_file)

        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            _ = cur.execute(
                """
                DELETE FROM real_files
                WHERE storage_path_id = (SELECT id FROM storage_paths WHERE storage_path = ?)
                  AND path = ?;
                """,
                (storage_path_str, str(real_file.path)),
            )
            _ = cur.execute(
                """
                INSERT INTO real_files (
                    storage_path_id,
                    path,
                    size,
                    is_dir,
                    hash_value,
                    algo,
                    first_seen,
                    last_seen,
                    comment
                )
                SELECT storage_paths.id AS storage_path_id,
                       :path AS path,
                       :size AS size,
                       :is_dir AS is_dir,
                       :hash_value AS hash_value,
                       :algo AS algo,
                       :first_seen AS first_seen,
                       :last_seen AS last_seen,
                       :comment AS comment
                FROM storage_paths
                WHERE storage_path = :storage_path;
                """,
                real_file_row | {"storage_path": storage_path_str},
            )
            if real_file.verification:
                verification_rows = list(
                    self._build_verification_rows(
                        real_file.verification,
                        str(real_file.path),
                        storage_path_str,
                        cur,
                    )
                )
                if verification_rows:
                    _ = cur.executemany(
                        """
                        INSERT INTO verifications (
                            real_file_id,
                            source_type,
                            hash_archive_id,
                            hash_value,
                            algo,
                            comment
                        )
                        SELECT
                            real_files.id,
                            :source_type,
                            :hash_archive_id,
                            :hash_value,
                            :algo,
                            :comment
                        FROM real_files
                        JOIN storage_paths
                          ON real_files.storage_path_id = storage_paths.id
                        WHERE storage_paths.storage_path = :storage_path
                          AND real_files.path = :path;
                        """,
                        verification_rows,
                    )

    def load(self, storage_path: Path, path: PurePath | str) -> RealFile:
        """Load one RealFile (including all Verification records)."""
        normalized_storage_path = self._check_storage_path_allowed(storage_path)
        storage_path_str = str(normalized_storage_path)
        path_str = str(path)

        with Sqlite3FK(self._db_path) as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            rf_row = cur.execute(
                """
                SELECT real_files.*, storage_paths.storage_path
                FROM real_files
                JOIN storage_paths ON real_files.storage_path_id = storage_paths.id
                WHERE storage_paths.storage_path = ? AND real_files.path = ?;
                """,
                (storage_path_str, path_str),
            ).fetchone()

            if rf_row is None:
                raise FileNotFoundError(
                    f"Real file not found: {storage_path_str}/{path_str}"
                )

            real_file = self._row_to_real_file(rf_row)
            verifications = self._load_verifications(cur, rf_row["id"], real_file)
            real_file.verification = verifications
            return real_file

    def _initialize_storage_paths(self) -> None:
        with Sqlite3FK(self._db_path) as con:
            cur = con.cursor()
            for storage_path in self._allowed_storage_paths:
                storage_path_str = str(storage_path)
                _ = cur.execute(
                    "INSERT OR IGNORE INTO storage_paths (storage_path) VALUES (?);",
                    (storage_path_str,),
                )

    def _check_storage_path_allowed(self, storage_path: Path) -> Path:
        normalized = storage_path.resolve()
        if normalized not in self._allowed_storage_paths:
            raise ValueError(
                f"Storage path '{normalized}' is not in the allowed set. "
                f"Allowed paths: {sorted(str(p) for p in self._allowed_storage_paths)}"
            )
        return normalized

    @staticmethod
    def _build_real_file_row(real_file: RealFile) -> dict[str, object]:
        return {
            "path": str(real_file.path),
            "size": real_file.size,
            "is_dir": int(real_file.is_dir),
            "hash_value": real_file.hash_value,
            "algo": real_file.algo.value if real_file.algo is not None else None,
            "first_seen": real_file.first_seen.isoformat()
            if real_file.first_seen
            else None,
            "last_seen": real_file.last_seen.isoformat()
            if real_file.last_seen
            else None,
            "comment": real_file.comment,
        }

    def _build_verification_rows(
        self,
        verifications: Iterable[Verification],
        path: str,
        storage_path: str,
        cursor: sqlite3.Cursor,
    ) -> collections.abc.Iterator[dict[str, object | None]]:
        for verification in verifications:
            yield {
                "source_type": verification.source_type.value,
                "hash_archive_id": self._lookup_hash_archive_id(
                    cursor, verification.hash_archive
                ),
                "hash_value": verification.hash_value,
                "algo": verification.algo.value,
                "comment": verification.comment,
                "path": path,
                "storage_path": storage_path,
            }

    def _lookup_hash_archive_id(
        self, cursor: sqlite3.Cursor, hash_archive: HashArchive | None
    ) -> int | None:
        if hash_archive is None:
            return None

        storage_path_str = str(hash_archive.storage_path.resolve())
        path_str = str(hash_archive.path)
        row = cursor.execute(
            """
            SELECT hash_archives.id
            FROM hash_archives
            JOIN storage_paths ON hash_archives.storage_path_id = storage_paths.id
            WHERE storage_paths.storage_path = ? AND hash_archives.path = ?;
            """,
            (storage_path_str, path_str),
        ).fetchone()

        if row is None:
            raise ValueError(
                "Verification refers to a HashArchive that is not stored in the database: "
                f"{storage_path_str}/{path_str}"
            )
        return int(row[0])

    def _load_verifications(
        self, cursor: sqlite3.Cursor, real_file_db_id: int, real_file: RealFile
    ) -> list[Verification]:
        verification_rows = cursor.execute(
            "SELECT * FROM verifications WHERE real_file_id = ? ORDER BY id;",
            (real_file_db_id,),
        ).fetchall()

        verifications: list[Verification] = []
        for row in verification_rows:
            hash_archive: HashArchive | None = None
            hash_archive_id = row["hash_archive_id"]
            if hash_archive_id is not None:
                hash_archive = self._load_hash_archive_by_id(cursor, hash_archive_id)

            verification = Verification(
                real_file=real_file,
                source_type=VerificationSource(row["source_type"]),
                hash_archive=hash_archive,
                hash_value=row["hash_value"],
                algo=Algo(row["algo"]),
                comment=row["comment"],
            )
            verifications.append(verification)
        return verifications

    def _load_hash_archive_by_id(
        self, cursor: sqlite3.Cursor, archive_id: int
    ) -> HashArchive | None:
        hash_archive_row = cursor.execute(
            """
            SELECT hash_archives.*, storage_paths.storage_path
            FROM hash_archives
            JOIN storage_paths ON hash_archives.storage_path_id = storage_paths.id
            WHERE hash_archives.id = ?;
            """,
            (archive_id,),
        ).fetchone()

        if hash_archive_row is None:
            return None
        return HashArchiveRepository._fill_archive(hash_archive_row)

    @staticmethod
    def _row_to_real_file(row: sqlite3.Row) -> RealFile:
        return RealFile(
            storage_path=Path(row["storage_path"]),
            path=PurePath(row["path"]),
            size=int(row["size"]),
            is_dir=bool(row["is_dir"]),
            algo=Algo(row["algo"]) if row["algo"] is not None else None,
            hash_value=row["hash_value"],
            first_seen=RealFileRepository._parse_datetime(row["first_seen"]),
            last_seen=RealFileRepository._parse_datetime(row["last_seen"]),
            comment=row["comment"],
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> dt.datetime | None:
        return dt.datetime.fromisoformat(value) if value else None


__all__ = ["RealFileRepository"]
