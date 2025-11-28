from __future__ import annotations

from pathlib import Path

import pytest
import tests.test_case_file_info as case_files
from hoarder.archives import Algo
from hoarder.realfiles import RealFile

STORAGE_ROOT = Path("test_files/compare")
CRC32_SAMPLE_FILES = [fe for fe in case_files.TEST_FILES if not fe.is_dir][:10]
CRC32_SAMPLE_DIRS = [fe for fe in case_files.TEST_FILES if fe.is_dir][:5]


def _build_real_file(entry: case_files.FileEntry) -> RealFile:
    return RealFile(
        storage_path=STORAGE_ROOT,
        path=entry.path,
        size=entry.size,
        is_dir=entry.is_dir,
    )


def test_real_file_full_path_includes_storage_root() -> None:
    entry = case_files.TEST_FILES[0]
    real_file = _build_real_file(entry)
    assert real_file.full_path == STORAGE_ROOT / entry.path


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
