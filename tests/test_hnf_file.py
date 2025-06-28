import itertools
import logging
import os
import pathlib
import sys

import hoarder

compare_files = [
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath(
            r"[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv"
        ),
        131072,
        False,
        b"\x87\x14\xc7\x6f",
        hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath(
            r"[Dummy] Uppercase and Brackets Ep13v2[Puresuhoruda][6519E6CF].mkv"
        ),
        131072,
        False,
        b"\x65\x19\xe6\xcf",
        hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath(
            r"[Foobar] Lowercase and Parens - 11 (x264-AC3)(d74b7612).mkv"
        ),
        131072,
        False,
        b"\xd7\x4b\x76\x12",
        hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath(
            r"[Test] Uppercase and Parens! S02E080 (WEB 1080p x264 10-bit AAC) (5A365C81).mkv"
        ),
        131072,
        False,
        b"\x5a\x36\x5c\x81",
        hoarder.hash_archive.Algo.CRC32,
    ),
]

test_file_path = pathlib.Path(__file__).parent.resolve()
add_path = (test_file_path / ".." / "src").resolve()
sys.path.append(add_path.as_posix())

logger = logging.getLogger("hoarder.test_hnf_file")

compare_files_wo_dir = [el for el in compare_files if not el.is_dir]


def test_hnf_archives():
    hnf_archives = []
    p = test_file_path / ".." / "test_files" / "hnf"
    for hnf_file_path in os.listdir(p):
        logger.debug(hnf_file_path)
        hnf_archive = hoarder.HashNameArchive.from_path(p / hnf_file_path)
        hnf_archives.append(hnf_archive)
    assert len(hnf_archives) == 4
    assert sorted(itertools.chain(*map(lambda x: x.files, hnf_archives))) == sorted(
        compare_files
    )
