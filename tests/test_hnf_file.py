import itertools
import logging
import os
import pathlib

import hoarder
import pytest

import tests.test_case_file_info

logger = logging.getLogger("hoarder.test_hnf_file")


@pytest.fixture
def list_hnf_file_paths():
    hnf_file_path = (
        pathlib.Path(__file__).parent.resolve() / ".." / "test_files" / "hnf"
    )
    return [hnf_file_path / p for p in os.listdir(hnf_file_path)]


def test_hnf_archives(list_hnf_file_paths: list[pathlib.Path]):
    hnf_archives = []
    for hnf_file_path in list_hnf_file_paths:
        hnf_archive = hoarder.HashNameArchive.from_path(hnf_file_path)
        hnf_archives.append(hnf_archive)
    assert len(hnf_archives) == 4
    assert sorted(itertools.chain(*map(lambda x: x.files, hnf_archives))) == sorted(
        tests.test_case_file_info.HNF_FILES
    )
