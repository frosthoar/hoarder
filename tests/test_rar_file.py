import logging
import pathlib
import sys

import hoarder

test_file_path = pathlib.Path(__file__).parent.resolve()
add_path = (test_file_path / ".." / "src").resolve()
sys.path.append(add_path.as_posix())

logger = logging.getLogger("hoarder.test_rar_file")

rar_file_compare = [
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
        path=pathlib.Path("sample_dir"),
        size=0,
        is_dir=True,
        hash_value=b"\x00\x00\x00\x00",
        algo=hoarder.hash_file.Algo.CRC32,
    ),
    hoarder.hash_file.FileEntry(
        path=pathlib.Path("sample_dir/english text 2.txt"),
        size=360,
        is_dir=False,
        hash_value=b"\xdf\x9d\x9dH",
        algo=hoarder.hash_file.Algo.CRC32,
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

rar_file_wo_hashes_compare = [
    hoarder.hash_file.FileEntry(el.path, el.size, el.is_dir, None, None)
    for el in rar_file_compare
]


def test_rar_files():
    rar4_file_path = (
        test_file_path / ".." / "test_files" / "rar" / "winrar_rar4_password.rar"
    ).resolve()
    rar4_file = hoarder.RarFile.from_path(rar4_file_path, password="password")
    for f in rar4_file.files:
        logger.debug(f)
    assert len(rar4_file.files) == 7
    assert sorted(rar4_file.files) == sorted(rar_file_compare)
    assert rar4_file.path == rar4_file_path

    rar_file_path = (
        test_file_path / ".." / "test_files" / "rar" / "winrar_rar5_password.rar"
    ).resolve()

    rar5_file = hoarder.RarFile.from_path(rar_file_path, password="password")
    assert len(rar5_file.files) == 7
    assert sorted(rar5_file.files) == sorted(
        rar_file_wo_hashes_compare
    )  # no hashes in RAR5 in header
    assert rar5_file.path == rar_file_path

    rar5_file.update_hash_values()
    assert sorted(rar5_file.files) == sorted(
        rar_file_compare
    )  # hashes now have been calculated
