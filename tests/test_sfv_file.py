import pathlib

import pytest

import tests.test_case_file_info
import hoarder

SFV_TUPLES = [
    (
        pathlib.Path("./test_files/sfv/files.sfv"),
        filter(lambda x: not x.is_dir, tests.test_case_file_info.TEST_FILES),
    )
]


@pytest.mark.parametrize("sfv_data_tuple", SFV_TUPLES)
def test_sfv_files(sfv_data_tuple):
    sfv_archive = hoarder.SfvArchive.from_path(sfv_data_tuple[0].resolve())
    for a, b in zip(sorted(sfv_archive.files), sorted(sfv_data_tuple[1])):
        assert a.path == b.path
        assert a.is_dir == b.is_dir
        assert a.hash_value == b.hash_value
    assert sfv_archive.path == sfv_data_tuple[0].absolute()
