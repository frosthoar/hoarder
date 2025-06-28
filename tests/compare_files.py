import pathlib

import hoarder

compare_files = [
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath("empty_file"),
        0,
        False,
        b"\x00\x00\x00\x00",
        hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(  # 902F433D 902F433D
        pathlib.PurePath("english text.txt"),
        637,
        False,
        b"\x90\x2f\x43\x3d",
        hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath("Stück.txt"),
        964,
        False,
        b"\xb3\xa6\x5a\xf4",
        hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        path=pathlib.PurePath("sample_dir"),
        size=0,
        is_dir=True,
        hash_value=b"\x00\x00\x00\x00",
        algo=hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        path=pathlib.PurePath("sample_dir/english text 2.txt"),
        size=360,
        is_dir=False,
        hash_value=b"\xdf\x9d\x9dH",
        algo=hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath("trailing whitespace .txt"),
        729,
        False,
        b"\x47\x5f\x91\x8b",
        hoarder.hash_archive.Algo.CRC32,
    ),
    hoarder.hash_archive.FileEntry(
        pathlib.PurePath("日本語テキスト.txt"),
        5070,
        False,
        b"\x80\xed\x75\x5f",
        hoarder.hash_archive.Algo.CRC32,
    ),
]
