import itertools
import logging
import os
import pathlib
import sys

import hoarder
import tests.compare_files

hnf_compare_files = tests.compare_files.hnf_file_entries

test_file_path = pathlib.Path(__file__).parent.resolve()
add_path = (test_file_path / ".." / "src").resolve()
sys.path.append(add_path.as_posix())

logger = logging.getLogger("hoarder.test_hnf_file")

compare_files_wo_dir = [el for el in hnf_compare_files if not el.is_dir]


def test_hnf_archives():
    hnf_archives = []
    p = test_file_path / ".." / "test_files" / "hnf"
    for hnf_file_path in os.listdir(p):
        logger.debug(hnf_file_path)
        hnf_archive = hoarder.HashNameArchive.from_path(p / hnf_file_path)
        hnf_archives.append(hnf_archive)
    assert len(hnf_archives) == 4
    assert sorted(itertools.chain(*map(lambda x: x.files, hnf_archives))) == sorted(
        hnf_compare_files
    )
