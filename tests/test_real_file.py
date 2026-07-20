from __future__ import annotations

from pathlib import Path

import pytest
import tests.test_case_file_info as case_files
from hoarder.archives import Algo
from hoarder.downloads import RealFile
from hoarder.utils import AnchoredPath

STORAGE_ROOT = Path("test_files/compare")
CRC32_SAMPLE_FILES = [fe for fe in case_files.TEST_FILES if not fe.is_dir][:10]
CRC32_SAMPLE_DIRS = [fe for fe in case_files.TEST_FILES if fe.is_dir][:5]


def _build_real_file(entry: case_files.FileEntry) -> RealFile:
    assert entry.size is not None, "test fixtures always set a concrete size"
    return RealFile(
        anchor=AnchoredPath(STORAGE_ROOT, entry.path),
        size=entry.size,
        is_dir=entry.is_dir,
    )


def test_real_file_full_path_includes_storage_root() -> None:
    entry = case_files.TEST_FILES[0]
    real_file = _build_real_file(entry)
    assert real_file.full_path == STORAGE_ROOT.resolve() / entry.path


@pytest.mark.parametrize("entry", CRC32_SAMPLE_FILES)
def test_real_file_calculates_crc32_for_files(entry: case_files.FileEntry) -> None:
    if entry.hash_value is None:
        pytest.skip("Test case missing reference hash")

    real_file = _build_real_file(entry)

    result = real_file.calculate_hash()

    assert result == entry.hash_value
    assert real_file.hash_value == entry.hash_value
    assert real_file.algo == Algo.CRC32


@pytest.mark.parametrize("entry", CRC32_SAMPLE_DIRS)
def test_real_file_directory_hashes_are_empty(entry: case_files.FileEntry) -> None:
    real_file = _build_real_file(entry)
    result = real_file.calculate_hash()

    assert result == entry.hash_value == b"\x00\x00\x00\x00"
    assert real_file.algo == Algo.CRC32


def test_calculate_hash_unsupported_algo_raises() -> None:
    entry = case_files.TEST_FILES[0]
    real_file = _build_real_file(entry)

    with pytest.raises(NotImplementedError):
        real_file.calculate_hash(algo=Algo.SHA1)


def test_real_file_hash_is_based_on_full_path_not_full_equality() -> None:
    """Two RealFiles with the same full_path hash equal even when other
    fields differ - the intentional relaxation that makes RealFile usable
    as a dict/set key while staying mutable (mirrors FileEntry)."""
    entry = case_files.TEST_FILES[0]
    same_path_a = RealFile(
        anchor=AnchoredPath(STORAGE_ROOT, entry.path), size=1, is_dir=False
    )
    same_path_b = RealFile(
        anchor=AnchoredPath(STORAGE_ROOT, entry.path), size=999, is_dir=False
    )
    different_entry = next(
        fe for fe in case_files.TEST_FILES if fe.path != entry.path and not fe.is_dir
    )
    different_path = RealFile(
        anchor=AnchoredPath(STORAGE_ROOT, different_entry.path), size=1, is_dir=False
    )

    assert hash(same_path_a) == hash(same_path_b)
    assert same_path_a != same_path_b

    as_dict_keys = {
        same_path_a: "first",
        same_path_b: "second",
        different_path: "third",
    }
    assert len(as_dict_keys) == 3
