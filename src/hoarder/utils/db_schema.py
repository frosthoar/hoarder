from __future__ import annotations

import sqlite3
from pathlib import Path

from .sql3_fk import Sqlite3FK

_CREATE_STORAGE_PATHS = """
CREATE TABLE IF NOT EXISTS storage_paths (
    id             INTEGER  PRIMARY KEY AUTOINCREMENT,
    storage_path   TEXT     NOT NULL UNIQUE
);
"""

_CREATE_HASH_ARCHIVES = """
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
    part_n_padding INTEGER,
    requires_password INTEGER,
    FOREIGN KEY (storage_path_id)
      REFERENCES storage_paths(id)
      ON DELETE CASCADE,
    UNIQUE(storage_path_id, path)
);
"""

_CREATE_FILE_ENTRIES = """
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

_CREATE_REAL_FILES = """
CREATE TABLE IF NOT EXISTS real_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    storage_path_id INTEGER NOT NULL,
    path            TEXT NOT NULL,
    size            INTEGER NOT NULL,
    is_dir          INTEGER NOT NULL,
    hash_value      BLOB,
    algo            INTEGER,
    first_seen      TEXT,
    last_seen       TEXT,
    comment         TEXT,
    FOREIGN KEY (storage_path_id)
      REFERENCES storage_paths(id)
      ON DELETE CASCADE,
    UNIQUE(storage_path_id, path)
);
"""

_CREATE_VERIFICATIONS = """
CREATE TABLE IF NOT EXISTS verifications (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    real_file_id             INTEGER NOT NULL,
    source_type              INTEGER NOT NULL,
    source_path              TEXT    NOT NULL,
    source_storage_path_id   INTEGER NOT NULL,
    hash_value               BLOB NOT NULL,
    algo                     INTEGER NOT NULL,
    comment                  TEXT,
    FOREIGN KEY (real_file_id)
      REFERENCES real_files(id)
      ON DELETE CASCADE,
    FOREIGN KEY (source_storage_path_id)
      REFERENCES storage_paths(id)
      ON DELETE CASCADE
);
"""

_CREATE_DOWNLOADS = """
CREATE TABLE IF NOT EXISTS downloads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL UNIQUE,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    comment         TEXT,
    processed       INTEGER NOT NULL
);
"""

_CREATE_DOWNLOAD_REAL_FILES = """
CREATE TABLE IF NOT EXISTS download_real_files (
    download_id     INTEGER NOT NULL,
    real_file_id    INTEGER NOT NULL,
    FOREIGN KEY (download_id)
      REFERENCES downloads(id)
      ON DELETE CASCADE,
    FOREIGN KEY (real_file_id)
      REFERENCES real_files(id)
      ON DELETE CASCADE,
    UNIQUE(download_id, real_file_id)
);
"""

_CREATE_DOWNLOAD_HASH_ARCHIVES = """
CREATE TABLE IF NOT EXISTS download_hash_archives (
    download_id     INTEGER NOT NULL,
    hash_archive_id INTEGER NOT NULL,
    FOREIGN KEY (download_id)
      REFERENCES downloads(id)
      ON DELETE CASCADE,
    FOREIGN KEY (hash_archive_id)
      REFERENCES hash_archives(id)
      ON DELETE CASCADE,
    UNIQUE(download_id, hash_archive_id)
);
"""


def ensure_repository_tables(db_path: str | Path) -> None:
    """Create all shared repository tables if needed."""
    with Sqlite3FK(db_path) as con:
        cur = con.cursor()
        _ = cur.execute(_CREATE_STORAGE_PATHS)
        _ = cur.execute(_CREATE_HASH_ARCHIVES)
        _ = cur.execute(_CREATE_FILE_ENTRIES)
        _ = cur.execute(_CREATE_REAL_FILES)
        _ = cur.execute(_CREATE_VERIFICATIONS)
        _ = cur.execute(_CREATE_DOWNLOADS)
        _ = cur.execute(_CREATE_DOWNLOAD_REAL_FILES)
        _ = cur.execute(_CREATE_DOWNLOAD_HASH_ARCHIVES)
        _normalize_legacy_backslash_paths(con)


def _normalize_legacy_backslash_paths(con: sqlite3.Connection) -> None:
    """Rewrite path values a pre-fix build stored with native Windows
    separators to the posix form all repositories now read and write.

    Without this, rows written before paths were normalized to posix on
    save are permanently invisible to lookups (which now always query with
    a posix-form key), and a subsequent save() recreates them under the
    posix key instead of replacing them, leaving orphaned duplicates behind.
    """
    cur = con.cursor()

    # file_entries.path and verifications.source_path carry no uniqueness
    # constraint, so an in-place rewrite can't collide.
    for table, column in (("file_entries", "path"), ("verifications", "source_path")):
        _ = cur.execute(
            f"UPDATE {table} SET {column} = REPLACE({column}, '\\', '/') "  # noqa: S608
            f"WHERE INSTR({column}, '\\') > 0;"
        )

    # hash_archives.path and real_files.path are each UNIQUE(storage_path_id,
    # path). A legacy backslash row can coexist with a row already written
    # under the posix key (created by the mismatch bug before this fix), so
    # rewriting in place could violate that constraint. Drop the legacy
    # duplicate when a posix counterpart already exists; otherwise rewrite.
    for table in ("hash_archives", "real_files"):
        legacy_rows = cur.execute(
            f"SELECT id, storage_path_id, path FROM {table} "  # noqa: S608
            f"WHERE INSTR(path, '\\') > 0;"
        ).fetchall()
        for row_id, storage_path_id, path in legacy_rows:
            normalized = path.replace("\\", "/")
            exists = cur.execute(
                f"SELECT 1 FROM {table} WHERE storage_path_id = ? AND path = ?;",  # noqa: S608
                (storage_path_id, normalized),
            ).fetchone()
            if exists:
                _ = cur.execute(f"DELETE FROM {table} WHERE id = ?;", (row_id,))  # noqa: S608
            else:
                _ = cur.execute(
                    f"UPDATE {table} SET path = ? WHERE id = ?;",  # noqa: S608
                    (normalized, row_id),
                )


__all__ = ["ensure_repository_tables"]
