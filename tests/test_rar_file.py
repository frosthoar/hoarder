import logging
import pathlib
import sys
import logging

import hoarder
import tests.compare_files

logger = logging.getLogger("hoarder.test_rar_file")

def test_rar_archives():
    rar4_archive_path = (
         pathlib.Path(r"../test_files/rar/v4_split_encrypted.rar")
    ).resolve()
    v4_split_archive = hoarder.RarArchive.from_path(rar4_archive_path, password="dragon")
    for f in v4_split_archive.files:
        logger.debug(f)
    assert len(v4_split_archive.files) == 4
    v4_split_archive.update_hash_values()
    assert sorted(v4_split_archive.files) == sorted(tests.compare_files.hnf_file_entries)
    assert v4_split_archive.path == rar4_archive_path
    assert (
        v4_split_archive.scheme == hoarder.RarScheme.DOT_RNN
    )  # cannot be distinguished from RAR4
    assert v4_split_archive.n_volumes == 9

    v4_s_eh_path = pathlib.Path("../test_files/rar/v4_split_headers_encrypted.rar").resolve()

    v4_split_encrypted_headers = hoarder.RarArchive.from_path(v4_s_eh_path, password="secret")
    assert len(v4_split_encrypted_headers.files) == 4
    assert sorted(v4_split_encrypted_headers.files) == sorted(tests.compare_files.hnf_file_entries)  # no hashes in RAR5 in header
    assert v4_split_encrypted_headers.path == v4_s_eh_path

    v4_split_encrypted_headers.update_hash_values()
    assert sorted(v4_split_encrypted_headers.files) == sorted(tests.compare_files.hnf_file_entries)  # hashes now have been calculated
    #    assert v4_split_encrypted_headers.scheme == hoarder.RarScheme.PART_N
    assert v4_split_encrypted_headers.n_volumes == 9
