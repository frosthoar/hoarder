import logging
import pathlib
import sys

import hoarder

test_file_path = pathlib.Path(__file__).parent.resolve()
add_path = (test_file_path / ".." / "src").resolve()
sys.path.append(add_path.as_posix())

logger = logging.getLogger("hoarder.test_sfv_file")

sfv_file_compare = [
    hoarder.hash_file.FileEntry(
        pathlib.Path("empty_file"),
        0,
        False,
        b"\x00\x00\x00\x00",
        hoarder.hash_file.Algo.CRC32,
    ),
    hoarder.hash_file.FileEntry(  # 902F433D 902F433D
        pathlib.Path("english text.txt"),
        637,
        False,
        b"\x90\x2f\x43\x3d",
        hoarder.hash_file.Algo.CRC32,
    ),
    hoarder.hash_file.FileEntry(
        pathlib.Path("Stück.txt"),
        964,
        False,
        b"\xb3\xa6\x5a\xf4",
        hoarder.hash_file.Algo.CRC32,
    ),
    hoarder.hash_file.FileEntry(
        pathlib.Path("trailing whitespace .txt"),
        729,
        False,
        b"\x47\x5f\x91\x8b",
        hoarder.hash_file.Algo.CRC32,
    ),
    hoarder.hash_file.FileEntry(
        pathlib.Path("日本語テキスト.txt"),
        5070,
        False,
        b"\x80\xed\x75\x5f",
        hoarder.hash_file.Algo.CRC32,
    ),
]


def test_sfv_files():
    sfv_file_path = (
        test_file_path / ".." / "test_files" / "sfv" / "rhash_output.sfv"
    ).resolve()
    sfv_file = hoarder.SfvFile.from_path(sfv_file_path)
    assert len(sfv_file.files) == 5
    assert sorted(sfv_file.files) == sorted(sfv_file_compare)
    assert sfv_file.path == sfv_file_path

    sfv_file_lowercase_path = (
        test_file_path / ".." / "test_files" / "sfv" / "rhash_output_lowercase.sfv"
    ).resolve()

    sfv_file_lowercase = hoarder.SfvFile.from_path(sfv_file_lowercase_path)
    assert len(sfv_file_lowercase.files) == 5
    assert sorted(sfv_file_lowercase.files) == sorted(sfv_file_compare)
    assert sfv_file_lowercase.path == sfv_file_lowercase_path
