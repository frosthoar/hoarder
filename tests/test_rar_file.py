import logging
import pathlib
import sys

import hoarder

import compare_files

test_file_path = pathlib.Path(__file__).parent.resolve()
add_path = (test_file_path / ".." / "src").resolve()
sys.path.append(add_path.as_posix())

logger = logging.getLogger("hoarder.test_rar_file")


compare_files_wo_hashes = [
    hoarder.hash_file.FileEntry(el.path, el.size, el.is_dir, None, None)
    for el in compare_files.compare_files
]


def test_rar_files():
    rar4_file_path = (
        test_file_path / ".." / "test_files" / "rar" / "winrar_rar4_password.rar"
    ).resolve()
    rar4_file = hoarder.RarFile.from_path(rar4_file_path, password="password")
    for f in rar4_file.files:
        logger.debug(f)
    assert len(rar4_file.files) == 7
    assert sorted(rar4_file.files) == sorted(compare_files.compare_files)
    assert rar4_file.path == rar4_file_path

    rar_file_path = (
        test_file_path / ".." / "test_files" / "rar" / "winrar_rar5_password.rar"
    ).resolve()

    rar5_file = hoarder.RarFile.from_path(rar_file_path, password="password")
    assert len(rar5_file.files) == 7
    assert sorted(rar5_file.files) == sorted(
        compare_files_wo_hashes
    )  # no hashes in RAR5 in header
    assert rar5_file.path == rar_file_path

    rar5_file.update_hash_values()
    assert sorted(rar5_file.files) == sorted(
        compare_files.compare_files
    )  # hashes now have been calculated
