from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path, PurePath

from .download import Download
from .real_file import RealFile
from .real_file_repository import RealFileRepository


class DownloadRepository:
    """Repository handling persistence for Download instances."""

    def __init__(self, real_file_repository: RealFileRepository | None = None):
        """Initialize the repository.

        Args:
            real_file_repository: Optional RealFileRepository instance. If not provided,
                a new one will be created.
        """
        self.real_file_repo = real_file_repository or RealFileRepository()

    def save(self, download: Download, con: sqlite3.Connection) -> None:
        """Insert or replace a Download and its associated RealFiles."""
        storage_path_str = str(download.storage_path.resolve())
        self._ensure_storage_path(con, download.storage_path)

        # Save all real_files first using real_file_repository
        for real_file in download.real_files:
            self.real_file_repo.save(real_file, con)

        # Save or update the download record
        cur = con.cursor()
        _ = cur.execute(
            """
            DELETE FROM downloads
            WHERE storage_path_id = (SELECT id FROM storage_paths WHERE storage_path = ?)
              AND path = ?;
            """,
            (storage_path_str, str(download.path)),
        )
        _ = cur.execute(
            """
            INSERT INTO downloads (
                storage_path_id,
                path,
                first_seen,
                last_seen,
                comment,
                processed
            )
            SELECT storage_paths.id AS storage_path_id,
                   :path AS path,
                   :first_seen AS first_seen,
                   :last_seen AS last_seen,
                   :comment AS comment,
                   :processed AS processed
            FROM storage_paths
            WHERE storage_path = :storage_path;
            """,
            {
                "storage_path": storage_path_str,
                "path": str(download.path),
                "first_seen": download.first_seen.isoformat(),
                "last_seen": download.last_seen.isoformat(),
                "comment": download.comment,
                "processed": int(download.processed),
            },
        )

        # Get the download ID
        download_id = cur.lastrowid
        if download_id is None:
            # If lastrowid is None, fetch the ID we just inserted
            row = cur.execute(
                """
                SELECT id FROM downloads
                WHERE storage_path_id = (SELECT id FROM storage_paths WHERE storage_path = ?)
                  AND path = ?;
                """,
                (storage_path_str, str(download.path)),
            ).fetchone()
            if row:
                download_id = row[0]

        # Delete existing associations
        if download_id:
            _ = cur.execute(
                "DELETE FROM download_real_files WHERE download_id = ?;",
                (download_id,),
            )

        # Create associations between download and real_files
        if download.real_files and download_id:
            for real_file in download.real_files:
                # Get the real_file ID
                real_file_row = cur.execute(
                    """
                    SELECT real_files.id
                    FROM real_files
                    JOIN storage_paths ON real_files.storage_path_id = storage_paths.id
                    WHERE storage_paths.storage_path = ? AND real_files.path = ?;
                    """,
                    (
                        str(real_file.storage_path.resolve()),
                        str(real_file.path),
                    ),
                ).fetchone()

                if real_file_row:
                    real_file_id = real_file_row[0]
                    _ = cur.execute(
                        """
                        INSERT OR IGNORE INTO download_real_files (download_id, real_file_id)
                        VALUES (?, ?);
                        """,
                        (download_id, real_file_id),
                    )

    def load(
        self,
        storage_path: Path,
        path: PurePath | str,
        con: sqlite3.Connection,
    ) -> Download:
        """Load one Download (including all associated RealFile records)."""
        storage_path_str = str(storage_path.resolve())
        path_str = str(path)

        con.row_factory = sqlite3.Row
        cur = con.cursor()
        download_row = cur.execute(
            """
            SELECT downloads.*, storage_paths.storage_path
            FROM downloads
            JOIN storage_paths ON downloads.storage_path_id = storage_paths.id
            WHERE storage_paths.storage_path = ? AND downloads.path = ?;
            """,
            (storage_path_str, path_str),
        ).fetchone()

        if download_row is None:
            raise FileNotFoundError(
                f"Download not found: {storage_path_str}/{path_str}"
            )

        download = self._row_to_download(download_row)
        real_files = self._load_real_files(con, download_row["id"])
        download.real_files = real_files
        return download

    def _load_real_files(
        self,
        con: sqlite3.Connection,
        download_id: int,
    ) -> list[RealFile]:
        """Load all RealFiles associated with a download."""
        cursor = con.cursor()
        real_file_rows = cursor.execute(
            """
            SELECT real_files.*, storage_paths.storage_path
            FROM real_files
            JOIN storage_paths ON real_files.storage_path_id = storage_paths.id
            JOIN download_real_files ON real_files.id = download_real_files.real_file_id
            WHERE download_real_files.download_id = ?
            ORDER BY real_files.id;
            """,
            (download_id,),
        ).fetchall()

        real_files: list[RealFile] = []
        for row in real_file_rows:
            real_file = self.real_file_repo._row_to_real_file(row)
            # Load verifications for each real_file
            verifications = self.real_file_repo._load_verifications(
                con, row["id"], real_file
            )
            real_file.verification = verifications
            real_files.append(real_file)
        return real_files

    @staticmethod
    def _ensure_storage_path(con: sqlite3.Connection, storage_path: Path) -> None:
        cur = con.cursor()
        _ = cur.execute(
            "INSERT OR IGNORE INTO storage_paths (storage_path) VALUES (?);",
            (str(storage_path.resolve()),),
        )

    @staticmethod
    def _row_to_download(row: sqlite3.Row) -> Download:
        return Download(
            storage_path=Path(row["storage_path"]),
            path=PurePath(row["path"]),
            first_seen=DownloadRepository._parse_datetime(row["first_seen"]),
            last_seen=DownloadRepository._parse_datetime(row["last_seen"]),
            comment=row["comment"],
            processed=bool(row["processed"]),
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> dt.datetime:
        if value is None:
            raise ValueError("Datetime field cannot be None")
        return dt.datetime.fromisoformat(value)


__all__ = ["DownloadRepository"]

