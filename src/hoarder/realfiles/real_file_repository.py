from __future__ import annotations

import collections.abc
import datetime as dt
import sqlite3
from pathlib import Path, PurePath
from typing import Iterable

from ..archives import Algo
from .real_file import RealFile, Verification, VerificationSource


class RealFileRepository:
    """Repository handling persistence for RealFile and Verification instances."""

    def save(self, real_file: RealFile, con: sqlite3.Connection) -> None:
        """Insert or replace a RealFile and its verifications."""
        storage_path_str = str(real_file.storage_path.resolve())
        real_file_row = self._build_real_file_row(real_file)

        self._ensure_storage_path(con, real_file.storage_path)
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
            for verification in real_file.verification:
                self._ensure_storage_path(con, verification.source_storage_path)
            verification_rows = list(
                self._build_verification_rows(
                    real_file.verification,
                    str(real_file.path),
                    storage_path_str,
                )
            )
            if verification_rows:
                expected_rows = len(verification_rows)
                _ = cur.executemany(
                    """
                    INSERT INTO verifications (
                        real_file_id,
                        source_type,
                        source_path,
                        source_storage_path_id,
                        hash_value,
                        algo,
                        comment
                    )
                    SELECT
                        real_files.id,
                        :source_type,
                        :source_path,
                        (
                            SELECT id
                            FROM storage_paths
                            WHERE storage_path = :source_storage_path
                        ) AS source_storage_path_id,
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
                if cur.rowcount != expected_rows:
                    raise ValueError("Failed to insert verification rows")

    def load(
        self,
        storage_path: Path,
        path: PurePath | str,
        con: sqlite3.Connection,
    ) -> RealFile:
        """Load one RealFile (including all Verification records)."""
        storage_path_str = str(storage_path.resolve())
        path_str = str(path)

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
        verifications = self._load_verifications(con, rf_row["id"], real_file)
        real_file.verification = verifications
        return real_file

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
    ) -> collections.abc.Iterator[dict[str, object | None]]:
        for verification in verifications:
            yield {
                "source_type": verification.source_type.value,
                "source_path": str(verification.source_path),
                "source_storage_path": str(verification.source_storage_path.resolve()),
                "hash_value": verification.hash_value,
                "algo": verification.algo.value,
                "comment": verification.comment,
                "path": path,
                "storage_path": storage_path,
            }

    def _load_verifications(
        self,
        con: sqlite3.Connection,
        real_file_db_id: int,
        real_file: RealFile,
    ) -> list[Verification]:
        cursor = con.cursor()
        verification_rows = cursor.execute(
            """
            SELECT verifications.*, storage_paths.storage_path AS source_storage_path
            FROM verifications
            JOIN storage_paths
              ON verifications.source_storage_path_id = storage_paths.id
            WHERE real_file_id = ?
            ORDER BY verifications.id;
            """,
            (real_file_db_id,),
        ).fetchall()

        verifications: list[Verification] = []
        for row in verification_rows:
            verification = Verification(
                real_file=real_file,
                source_type=VerificationSource(row["source_type"]),
                source_path=PurePath(row["source_path"]),
                source_storage_path=Path(row["source_storage_path"]),
                hash_value=row["hash_value"],
                algo=Algo(row["algo"]),
                comment=row["comment"],
            )
            verifications.append(verification)
        return verifications

    @staticmethod
    def _ensure_storage_path(con: sqlite3.Connection, storage_path: Path) -> None:
        cur = con.cursor()
        _ = cur.execute(
            "INSERT OR IGNORE INTO storage_paths (storage_path) VALUES (?);",
            (str(storage_path.resolve()),),
        )

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
