from pathlib import Path

import pytest
import tests.test_case_file_info
from hoarder.contents_hasher import CRC32Hasher
from hoarder.archives import FileEntry


def test_crc32_hasher_nonexistent_file():
    nonexistent_path = Path("nonexistent_file.txt")
    hasher = CRC32Hasher(nonexistent_path)

    with pytest.raises(FileNotFoundError):
        _ = hasher.hash_contents()


@pytest.fixture(autouse=True, scope="session")
def test_hashes_present():
    if not all(
        [fe.hash_value is not None for fe in tests.test_case_file_info.TEST_FILES]
    ):
        raise ValueError()


@pytest.mark.parametrize("test_files", tests.test_case_file_info.TEST_FILES)
def test_crc32_hasher_parametrized(test_files: FileEntry) -> None:
    file_path = Path("test_files/compare") / test_files.path
    if file_path.exists():
        if test_files.hash_value is None:
            return
        hasher = CRC32Hasher(file_path)
        computed_hash = hasher.hash_contents()

        assert (
            computed_hash == test_files.hash_value
        ), f"CRC32 mismatch for {test_files.path}: expected {test_files.hash_value.hex()}, got {computed_hash.hex()}"
