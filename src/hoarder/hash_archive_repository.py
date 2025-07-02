import dataclasses
import datetime
import pathlib
import sqlite3
import enum
from collections.abc import Callable
from typing import Any, cast, TypeVar

from hoarder import HashNameArchive, RarArchive, RarScheme, SfvArchive
from hoarder.hash_archive import Algo, FileEntry, HashArchive
from hoarder.hash_name_archive import HashEnclosure


@dataclasses.dataclass(frozen=True)
class TypeConfig:
    """Configuration on how to persist & hydrate classes."""

    cls: type

    # SQL column → function that extracts its value from the instance
    save: dict[str, Callable[[object], object]]

    # Obj prop   → function that extracts its value from the SQL hash_archive_row
    load: dict[str, Callable[[sqlite3.Row], object]]

def type_saver(obj: object) -> str:
    return type(obj).__name__

def timestamp_saver(_: object) -> str:
    return datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")

OUT = TypeVar("OUT", bound="type")

def build_simple_saver(attr: str, outcls: OUT) -> Callable[[object], OUT | None]:
    def simple_saver(obj: object) -> OUT | None:
        if getattr(obj, attr, None):
            val = cast(OUT, outcls(getattr(obj, attr)))
            return val
        else:
            return None
    return simple_saver

def build_simple_loader(key: str, outcls: OUT) -> Callable[[sqlite3.Row], OUT | None]:
    def simple_loader(row: sqlite3.Row) -> OUT | None:
        if row[key]:
            val = cast(OUT, outcls(row[key]))
            return val
        else:
            return None
    return simple_loader

def build_enum_saver(attr: str) -> Callable[[object],str | None]:
    def enum_saver(obj: object) -> str | None:
        if hasattr(obj, attr):
            val = cast(enum.Enum, getattr(obj, attr))
            return str(val.name)
        else:
            return None
    return enum_saver

E = TypeVar("E", bound=enum.Enum)

def build_enum_loader(attr: str, cls: type[E]) -> Callable[[sqlite3.Row], E | None]:
    def enum_loader(row: sqlite3.Row) -> E | None:
        if row[attr]:
            val = cast(str, row[attr])
            return cast(E, getattr(cls, val))
        else:
            return None
    return enum_loader
        

HASH_ARCHIVE_TYPE = TypeConfig(
    cls=HashArchive,  # will never be used, abstract class
    save={
        "path": build_simple_saver("path", str),
        "type": type_saver,
        "timestamp": timestamp_saver,
    },
    load={"path": build_simple_loader("path", pathlib.Path)}
)

TYPE_TABLE: dict[str, TypeConfig] = {
    "HashNameArchive": TypeConfig(
        cls=HashNameArchive,
        save=(
            HASH_ARCHIVE_TYPE.save
            | {
                "hash_enclosure": build_enum_saver("enc")
            }
        ),
        load=(
            HASH_ARCHIVE_TYPE.load | {"enc": build_enum_loader("hash_enclosure", HashEnclosure) }
        ),
    ),
    "RarArchive": TypeConfig(
        cls=RarArchive,
        save=(
            HASH_ARCHIVE_TYPE.save
            | {
                "password": build_simple_saver("password", str),
                "rar_scheme": build_enum_saver("scheme"),
                "rar_version": build_simple_saver("version", str),
                "n_volumes": build_simple_saver("n_volumes", int),
            }
        ),
        load=(
            HASH_ARCHIVE_TYPE.load
            | {
                "password": build_simple_loader("password", str),
                "scheme": build_enum_loader("rar_scheme", RarScheme),
                "version": build_simple_loader("rar_version", str),
                "n_volumes": build_simple_loader("n_volumes", int),
            }
        ),
    ),
    "SfvArchive": TypeConfig(
        cls=SfvArchive, save=HASH_ARCHIVE_TYPE.save, load=HASH_ARCHIVE_TYPE.load
    ),
    "FileEntry": TypeConfig(
        cls=FileEntry,
        save={
            "path": build_simple_saver("path", str),
            "size": build_simple_saver("size", int),
            "is_dir": build_simple_saver("is_dir", int),
            "hash_value": build_simple_saver("hash_value", bytes),
            "algo": build_enum_saver("algo")
        },
        load={
            "path": build_simple_loader("path", pathlib.PurePath),
            "size": build_simple_loader("size", int),
            "is_dir": build_simple_loader("is_dir", bool),
            "hash_value": build_simple_loader("hash_value", bytes),
            "algo": build_enum_loader("algo", Algo),
        },
    ),
}


def get_db_connection(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def build_insert_dict(obj: Any) -> dict[str, str]:
    insert_dict = {}
    type_config = TYPE_TABLE[type(obj).__name__]
    for key, fun in type_config.save.items():
        insert_dict[key] = fun(obj)
    return insert_dict


def construct_object_from_row(row: sqlite3.Row, type_name: str) -> Any:
    construct_dict = {}
    type_config = TYPE_TABLE[type_name].load
    for key, fun in type_config.items():
        construct_dict[key] = fun(row)
    cls = TYPE_TABLE[type_name].cls
    obj = cls(**construct_dict)
    return obj


class HashArchiveRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        cur.execute(
            """CREATE TABLE IF NOT EXISTS hash_archives
                     (
                     id             INTEGER PRIMARY KEY AUTOINCREMENT,
                     type           STRING NOT NULL,
                     path           STRING NOT NULL UNIQUE,
                     present        INTEGER,
                     password       STRING,
                     rar_scheme     STRING,
                     rar_version    STRING,
                     n_volumes      INTEGER,
                     hash_enclosure INTEGER,
                     timestamp TEXT NOT NULL
                  );"""
        )

        cur.execute(
            """CREATE TABLE IF NOT EXISTS file_entries
                     (
                     id          INTEGER PRIMARY KEY AUTOINCREMENT,
                     path        STRING NOT NULL,
                     size        INTEGER,
                     is_dir      INTEGER NOT NULL,
                     hash_value  BLOB,
                     algo        STRING,
                     archive_id  INTEGER NOT NULL,
                     FOREIGN KEY(archive_id) REFERENCES hash_archives(id) ON DELETE CASCADE
                  );"""
        )

        conn.commit()
        conn.close()

    def update(self, hash_archive: HashArchive):
        conn = get_db_connection(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.cursor()
        cur.execute("BEGIN;")

        ha_insert_dict = build_insert_dict(hash_archive)

        col_str = ", ".join([f'"{col}"' for col in ha_insert_dict.keys()])
        param_str = ", ".join([f":{col}" for col in ha_insert_dict.keys()])

        sql_insert = f"INSERT INTO hash_archives({col_str}) VALUES({param_str});"
        cur.execute('DELETE FROM "hash_archives" WHERE path = :path;', ha_insert_dict)
        cur.execute(sql_insert, ha_insert_dict)

        fe_insert_dicts = []
        if hash_archive.files:
            for file in hash_archive.files:
                fe_insert_dicts.append(build_insert_dict(file))
            col_str = ", ".join([f"{col}" for col in fe_insert_dicts[0].keys()])
            as_str = ", ".join(
                [f":{col} AS {col}" for col in fe_insert_dicts[0].keys()]
            )

            sql_insert = f"""INSERT INTO file_entries({col_str}, archive_id)
            SELECT {as_str}, id as archive_id FROM hash_archives WHERE path = :archive_path ;"""
            full = [
                (d | {"archive_path": ha_insert_dict["path"]}) for d in fe_insert_dicts
            ]
            cur.executemany(sql_insert, full)
        conn.commit()
        conn.close()

    def load(self, path: pathlib.Path):
        conn = get_db_connection(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("BEGIN;")

        cur.execute(
            """SELECT type, path, present, password, rar_scheme, rar_version, n_volumes, hash_enclosure
            FROM hash_archives WHERE path = :path""",
            {"path": str(path)},
        )
        hash_archive_row = cur.fetchone()
        hash_archive = construct_object_from_row(
            hash_archive_row, hash_archive_row["type"]
        )

        cur.execute(
            """SELECT path, size, is_dir, hash_value, algo FROM file_entries WHERE archive_id =
            (SELECT id FROM hash_archives WHERE path = :path)""",
            {"path": str(path)},
        )
        file_entry_rows = cur.fetchall()
        file_entries = set()
        for row in file_entry_rows:
            file_entries.add(construct_object_from_row(row, "FileEntry"))

        hash_archive.files = file_entries
        conn.close()
        return hash_archive
