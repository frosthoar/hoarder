from __future__ import annotations

import collections.abc
import sqlite3
from pathlib import Path, PurePath

from hoarder.archives.hash_archive import HashArchive
from hoarder.archives.hash_archive_repository import HashArchiveRepository
from hoarder.passwords.password_store import PasswordStore
from hoarder.passwords.password_store_repository import PasswordSqlite3Repository
from hoarder.realfiles.real_file import RealFile
from hoarder.realfiles.real_file_repository import RealFileRepository
from hoarder.utils.db_schema import ensure_repository_tables
from hoarder.utils.sql3_fk import Sqlite3FK


class HoarderRepository:
    """Facade that combines archive and real file repositories with one connection."""

    def __init__(
        self, db_path: str | Path, allowed_storage_paths: collections.abc.Iterable[Path]
    ) -> None:
        self.db_path = Path(db_path)
        self.allowed_storage_paths = self._normalize_paths(allowed_storage_paths)

        ensure_repository_tables(self.db_path)

        self.hash_repo = HashArchiveRepository()
        self.real_file_repo = RealFileRepository()
        self.password_repo = PasswordSqlite3Repository()

        self._initialize_storage_paths()
        self._initialize_password_tables()

    def save_hash_archive(self, archive: HashArchive) -> None:
        normalized_storage_path = self._check_storage_path_allowed(
            archive.storage_path
        )
        with Sqlite3FK(self.db_path) as con:
            self._ensure_storage_path(con, normalized_storage_path)
            self.hash_repo.save(archive, con)

    def load_hash_archive(self, storage_path: Path, path: PurePath | str) -> HashArchive:
        normalized_storage_path = self._check_storage_path_allowed(storage_path)
        with Sqlite3FK(self.db_path) as con:
            self._ensure_storage_path(con, normalized_storage_path)
            return self.hash_repo.load(normalized_storage_path, path, con)

    def save_real_file(self, real_file: RealFile) -> None:
        normalized_storage_path = self._check_storage_path_allowed(
            real_file.storage_path
        )
        with Sqlite3FK(self.db_path) as con:
            self._ensure_storage_path(con, normalized_storage_path)
            self.real_file_repo.save(real_file, con, self.hash_repo)

    def load_real_file(self, storage_path: Path, path: PurePath | str) -> RealFile:
        normalized_storage_path = self._check_storage_path_allowed(storage_path)
        with Sqlite3FK(self.db_path) as con:
            self._ensure_storage_path(con, normalized_storage_path)
            return self.real_file_repo.load(
                normalized_storage_path, path, con, self.hash_repo
            )

    def save_password_store(self, store: PasswordStore) -> None:
        with Sqlite3FK(self.db_path) as con:
            self.password_repo.ensure_tables(con)
            self.password_repo.save(store, con)

    def load_password_store(self) -> PasswordStore:
        with Sqlite3FK(self.db_path) as con:
            self.password_repo.ensure_tables(con)
            return self.password_repo.load(con)

    def _initialize_storage_paths(self) -> None:
        with Sqlite3FK(self.db_path) as con:
            for storage_path in self.allowed_storage_paths:
                self._ensure_storage_path(con, storage_path)

    def _initialize_password_tables(self) -> None:
        with Sqlite3FK(self.db_path) as con:
            self.password_repo.ensure_tables(con)

    @staticmethod
    def _normalize_paths(
        storage_paths: collections.abc.Iterable[Path],
    ) -> set[Path]:
        normalized_paths: set[Path] = set()
        for path in storage_paths:
            resolved = path.resolve()
            if not resolved.exists():
                raise FileNotFoundError(
                    f"Storage path does not exist on disk: {resolved}"
                )
            normalized_paths.add(resolved)
        if not normalized_paths:
            raise ValueError("At least one allowed storage path is required")
        return normalized_paths

    def _ensure_storage_path(
        self, con: sqlite3.Connection, storage_path: Path
    ) -> None:
        cur = con.cursor()
        _ = cur.execute(
            "INSERT OR IGNORE INTO storage_paths (storage_path) VALUES (?);",
            (str(storage_path),),
        )

    def _check_storage_path_allowed(self, storage_path: Path) -> Path:
        normalized = storage_path.resolve()
        if normalized not in self.allowed_storage_paths:
            raise ValueError(
                f"Storage path '{normalized}' is not in the allowed set. "
                f"Allowed paths: {sorted(str(p) for p in self.allowed_storage_paths)}"
            )
        return normalized


__all__ = ["HoarderRepository"]

