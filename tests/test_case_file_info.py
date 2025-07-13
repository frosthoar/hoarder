from pathlib import PurePath
from hoarder.hash_archive import FileEntry
from hoarder.hash_archive import Algo
import pytest


HNF_FILES = [
    FileEntry(
        path=PurePath(
            "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv"
        ),
        size=131072,
        is_dir=False,
        hash_value=b"\x87\x14\xc7o",
        algo=Algo.CRC32,
        info=None,
    ),
    FileEntry(
        path=PurePath(
            "[Dummy] Uppercase and Brackets Ep13v2[Puresuhoruda][6519E6CF].mkv"
        ),
        size=131072,
        is_dir=False,
        hash_value=b"e\x19\xe6\xcf",
        algo=Algo.CRC32,
        info=None,
    ),
    FileEntry(
        path=PurePath(
            "[Foobar] Lowercase and Parens - 11 (x264-AC3)(d74b7612).mkv"
        ),
        size=131072,
        is_dir=False,
        hash_value=b"\xd7Kv\x12",
        algo=Algo.CRC32,
        info=None,
    ),
    FileEntry(
        path=PurePath(
            "[Test] Uppercase and Parens! S02E080 (WEB 1080p x264 10-bit AAC) (5A365C81).mkv"
        ),
        size=131072,
        is_dir=False,
        hash_value=b"Z6\\\x81",
        algo=Algo.CRC32,
        info=None,
    ),
]

TEST_FILES = [
    FileEntry(
        path=PurePath("../test_files/files/Dummy.S01E01.Title.1080p/other_file.bin"),
        size=1024,
        is_dir=False,
        hash_value=b"\xe0\x9e\xd6\x7f",
        algo=Algo.CRC32,
        info=None,
    ),
    FileEntry(
        path=PurePath("../test_files/files/Dummy.S01E01.Title.1080p/random_file.bin"),
        size=1024,
        is_dir=False,
        hash_value=b"\n\x04\xb2\x1d",
        algo=Algo.CRC32,
        info=None,
    ),
]
