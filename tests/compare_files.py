import pathlib
import binascii
import os

import hoarder

ap = pathlib.Path(os.path.abspath(__file__)).parent
os.chdir(ap)


def CRC32_from_file(filename: str | pathlib.Path) -> bytes:
    with open(filename,"rb") as f:
        buf = f.read()
        buf = (binascii.crc32(buf) & 0xFFFFFFFF)
        return buf.to_bytes(4, byteorder='big')

dummy_dir_entries = []

test_file_path = ap / ".." / "test_files" / "files"

for entry in os.walk(test_file_path):
    path = pathlib.PurePath(entry)
    size = filestats = os.stat(test_file_path / path).st_size
    is_dir = (test_file_path / entry).is_dir()
    if is_dir:
        hash = bytes(4)
    else:
        hash = CRC32_from_file(test_file_path / entry)
    fe = hoarder.hash_archive.FileEntry(
        path,
        size,
        is_dir,
        hash,
        hoarder.hash_archive.Algo.CRC32
    )
    dummy_dir_entries.append(fe)

for d in dummy_dir_entries:
    print(d.pretty_print())
    print("\n")
