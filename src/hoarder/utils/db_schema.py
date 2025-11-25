from __future__ import annotations

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
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    real_file_id     INTEGER NOT NULL,
    source_type      INTEGER NOT NULL,
    hash_archive_id  INTEGER,
    verified         INTEGER NOT NULL,
    hash_value       BLOB,
    algo             INTEGER,
    verified_at      TEXT NOT NULL,
    comment          TEXT,
    FOREIGN KEY (real_file_id)
      REFERENCES real_files(id)
      ON DELETE CASCADE,
    FOREIGN KEY (hash_archive_id)
      REFERENCES hash_archives(id)
      ON DELETE SET NULL
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


__all__ = ["ensure_repository_tables"]

