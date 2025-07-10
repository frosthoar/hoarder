import logging
import pathlib
import sys

import compare_files
#   import hoarder

#   test_file_path = pathlib.Path(__file__).parent.resolve()
#   add_path = (test_file_path / ".." / "src").resolve()
#   sys.path.append(add_path.as_posix())

#   logger = logging.getLogger("hoarder.test_rar_file")


#   compare_files_wo_hashes = [
#       hoarder.hash_archive.FileEntry(el.path, el.size, el.is_dir, None, None)
#       for el in compare_files.compare_files
#   ]


#   def test_rar_archives():
#       rar4_archive_path = (
#           test_file_path / ".." / "test_files" / "rar" / "winrar_rar4_password.rar"
#       ).resolve()
#       rar4_archive = hoarder.RarArchive.from_path(rar4_archive_path, password="password")
#       for f in rar4_archive.files:
#           logger.debug(f)
#       assert len(rar4_archive.files) == 7
#       rar4_archive.update_hash_values()
#       assert sorted(rar4_archive.files) == sorted(compare_files.compare_files)
#       assert rar4_archive.path == rar4_archive_path
#       assert (
#           rar4_archive.scheme == hoarder.RarScheme.DOT_RNN
#       )  # cannot be distinguished from RAR4
#       assert rar4_archive.n_volumes == 1

#       rar_file_path = (
#           test_file_path / ".." / "test_files" / "rar" / "winrar_rar5_password.rar"
#       ).resolve()

#       rar5_archive = hoarder.RarArchive.from_path(rar_file_path, password="password")
#       assert len(rar5_archive.files) == 7
#       assert sorted(rar5_archive.files) == sorted(
#           compare_files_wo_hashes
#       )  # no hashes in RAR5 in header
#       assert rar5_archive.path == rar_file_path

#       rar5_archive.update_hash_values()
#       assert sorted(rar5_archive.files) == sorted(
#           compare_files.compare_files
#       )  # hashes now have been calculated
#       #    assert rar5_archive.scheme == hoarder.RarScheme.PART_N
#       assert rar5_archive.n_volumes == 1
