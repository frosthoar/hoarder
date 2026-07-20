import pathlib

import pytest
import tests.test_case_file_info
from hoarder.archives import SfvArchive
from hoarder.utils import AnchoredPath

SFV_TUPLES = [
    (
        pathlib.Path("./test_files/sfv/files.sfv"),
        filter(lambda x: not x.is_dir, tests.test_case_file_info.TEST_FILES),
    )
]


@pytest.mark.parametrize("sfv_data_tuple", SFV_TUPLES)
def test_sfv_files(sfv_data_tuple):
    full_path = sfv_data_tuple[0].resolve()
    root = full_path.parent
    path = pathlib.PurePath(full_path.name)
    sfv_archive = SfvArchive.from_path(root, path)
    for a, b in zip(sorted(sfv_archive.files), sorted(sfv_data_tuple[1])):
        assert a.path == b.path
        assert a.is_dir == b.is_dir
        assert a.hash_value == b.hash_value
    assert sfv_archive.full_path == sfv_data_tuple[0].absolute()


def test_sfv_discover_finds_sfv_in_directory():
    scope = AnchoredPath(pathlib.Path("test_files/sfv"), pathlib.PurePath("."))
    found = SfvArchive.discover(scope)
    assert [str(a.anchor.relative_path) for a in found] == ["files.sfv"]


def test_sfv_discover_finds_sfv_given_directly():
    scope = AnchoredPath(pathlib.Path("test_files/sfv"), pathlib.PurePath("files.sfv"))
    found = SfvArchive.discover(scope)
    assert [str(a.anchor.relative_path) for a in found] == ["files.sfv"]


def test_sfv_discover_returns_empty_when_no_sfv_present():
    scope = AnchoredPath(pathlib.Path("test_files/hnf"), pathlib.PurePath("."))
    assert SfvArchive.discover(scope) == []
