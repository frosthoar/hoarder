from __future__ import annotations

import collections.abc
import datetime as dt
import sqlite3
from pathlib import Path, PurePath

from ..archives import HashArchive, HashArchiveRepository
from .download import Download
from .real_file import RealFile
from .real_file_repository import RealFileRepository


class DownloadRepository:
    """Repository handling persistence for Download instances."""

    def __init__(
        self,
        real_file_repository: RealFileRepository | None = None,
        hash_archive_repository: HashArchiveRepository | None = None,
    ):
        """Initialize the repository.

        Args:
            real_file_repository: Optional RealFileRepository instance. If not provided,
                a new one will be created.
            hash_archive_repository: Optional HashArchiveRepository instance. If not provided,
                a new one will be created.
        """
        self.real_file_repo = real_file_repository or RealFileRepository()
        self.hash_archive_repo = hash_archive_repository or HashArchiveRepository()

    def save(self, download: Download, con: sqlite3.Connection) -> None:
        """Insert or replace a Download and its associated RealFiles and HashArchives."""
        # Ensure storage paths exist for all real_files
        for real_file in download.real_files:
            self._ensure_storage_path(con, real_file.storage_path)
            for verification in real_file.verification:
                self._ensure_storage_path(con, verification.source_storage_path)

        # Ensure storage paths exist for all hash_archives
        for hash_archive in download.hash_archives:
            self._ensure_storage_path(con, hash_archive.storage_path)

        # Save all real_files first using real_file_repository
        for real_file in download.real_files:
            self.real_file_repo.save(real_file, con)

        # Save all hash_archives using hash_archive_repository
        for hash_archive in download.hash_archives:
            self.hash_archive_repo.save(hash_archive, con)

        # Save or update the download record
        cur = con.cursor()
        _ = cur.execute(
            """
            DELETE FROM downloads
            WHERE title = ?;
            """,
            (download.title,),
        )
        _ = cur.execute(
            """
            INSERT INTO downloads (
                title,
                first_seen,
                last_seen,
                comment,
                processed
            )
            VALUES (
                :title,
                :first_seen,
                :last_seen,
                :comment,
                :processed
            );
            """,
            {
                "title": download.title,
                "first_seen": download.first_seen.isoformat(),
                "last_seen": download.last_seen.isoformat(),
                "comment": download.comment,
                "processed": int(download.processed),
            },
        )

        # Delete existing associations using SQL
        _ = cur.execute(
            """
            DELETE FROM download_real_files
            WHERE download_id = (
                SELECT downloads.id
                FROM downloads
                WHERE downloads.title = ?
            );
            """,
            (download.title,),
        )
        _ = cur.execute(
            """
            DELETE FROM download_hash_archives
            WHERE download_id = (
                SELECT downloads.id
                FROM downloads
                WHERE downloads.title = ?
            );
            """,
            (download.title,),
        )

        # Create associations between download and real_files using SQL
        if download.real_files:
            association_rows = list(
                self._build_association_rows(download.real_files, download.title)
            )
            if association_rows:
                expected_rows = len(association_rows)
                _ = cur.executemany(
                    """
                    INSERT OR IGNORE INTO download_real_files (
                        download_id,
                        real_file_id
                    )
                    SELECT
                        (
                            SELECT downloads.id
                            FROM downloads
                            WHERE downloads.title = :download_title
                        ) AS download_id,
                        (
                            SELECT real_files.id
                            FROM real_files
                            JOIN storage_paths ON real_files.storage_path_id = storage_paths.id
                            WHERE storage_paths.storage_path = :real_file_storage_path
                              AND real_files.path = :real_file_path
                        ) AS real_file_id;
                    """,
                    association_rows,
                )
                if cur.rowcount != expected_rows:
                    raise ValueError("Failed to insert download-real_file associations")

        # Create associations between download and hash_archives using SQL
        if download.hash_archives:
            archive_association_rows = list(
                self._build_archive_association_rows(
                    download.hash_archives, download.title
                )
            )
            if archive_association_rows:
                expected_rows = len(archive_association_rows)
                _ = cur.executemany(
                    """
                    INSERT OR IGNORE INTO download_hash_archives (
                        download_id,
                        hash_archive_id
                    )
                    SELECT
                        (
                            SELECT downloads.id
                            FROM downloads
                            WHERE downloads.title = :download_title
                        ) AS download_id,
                        (
                            SELECT hash_archives.id
                            FROM hash_archives
                            JOIN storage_paths ON hash_archives.storage_path_id = storage_paths.id
                            WHERE storage_paths.storage_path = :archive_storage_path
                              AND hash_archives.path = :archive_path
                        ) AS hash_archive_id;
                    """,
                    archive_association_rows,
                )
                if cur.rowcount != expected_rows:
                    raise ValueError(
                        "Failed to insert download-hash_archive associations"
                    )

    def load(self, title: str, con: sqlite3.Connection) -> Download:
        """Load one Download (including all associated RealFile and HashArchive records)."""
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        download_row = cur.execute(
            """
            SELECT downloads.*
            FROM downloads
            WHERE downloads.title = ?;
            """,
            (title,),
        ).fetchone()

        if download_row is None:
            raise FileNotFoundError(f"Download not found: {title}")

        download = self._row_to_download(download_row)
        real_files = self._load_real_files(con, download_row["id"])
        download.real_files = real_files
        hash_archives = self._load_hash_archives(con, download_row["id"])
        download.hash_archives = hash_archives
        return download

    def _build_association_rows(
        self,
        real_files: list[RealFile],
        download_title: str,
    ) -> collections.abc.Iterator[dict[str, str]]:
        """Build rows for inserting download-real_file associations."""
        for real_file in real_files:
            yield {
                "download_title": download_title,
                "real_file_storage_path": str(real_file.storage_path.resolve()),
                "real_file_path": str(real_file.path),
            }

    def _build_archive_association_rows(
        self,
        hash_archives: list[HashArchive],
        download_title: str,
    ) -> collections.abc.Iterator[dict[str, str]]:
        """Build rows for inserting download-hash_archive associations."""
        for hash_archive in hash_archives:
            yield {
                "download_title": download_title,
                "archive_storage_path": str(hash_archive.storage_path.resolve()),
                "archive_path": str(hash_archive.path),
            }

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

    def _load_hash_archives(
        self,
        con: sqlite3.Connection,
        download_id: int,
    ) -> list[HashArchive]:
        """Load all HashArchives associated with a download."""
        cursor = con.cursor()
        archive_rows = cursor.execute(
            """
            SELECT hash_archives.*, storage_paths.storage_path
            FROM hash_archives
            JOIN storage_paths ON hash_archives.storage_path_id = storage_paths.id
            JOIN download_hash_archives ON hash_archives.id = download_hash_archives.hash_archive_id
            WHERE download_hash_archives.download_id = ?
            ORDER BY hash_archives.id;
            """,
            (download_id,),
        ).fetchall()

        hash_archives: list[HashArchive] = []
        for row in archive_rows:
            storage_path = Path(row["storage_path"])
            path = PurePath(row["path"])
            hash_archive = self.hash_archive_repo.load(storage_path, path, con)
            hash_archives.append(hash_archive)
        return hash_archives

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
            title=row["title"],
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

