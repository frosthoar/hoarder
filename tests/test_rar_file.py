import logging
import pathlib

import pytest
import hoarder
import tests.test_case_file_info

logger = logging.getLogger("hoarder.test_rar_file")

RAR_TEST_ARCHIVE_DEFS = [
    (
        pathlib.Path("./test_files/rar/v4_split_headers_encrypted.rar"),
        "password",
        100,
        19,
        hoarder.RarScheme.DOT_RNN,
        tests.test_case_file_info.TEST_FILES,
    ),
    (
        pathlib.Path("./test_files/rar/v4_split_headers_unencrypted.rar"),
        None,
        100,
        18,
        hoarder.RarScheme.DOT_RNN,
        tests.test_case_file_info.TEST_FILES,
    ),
    (
        pathlib.Path("./test_files/rar/v4_unencrypted.rar"),
        None,
        100,
        1,
        hoarder.RarScheme.DOT_RNN,
        tests.test_case_file_info.TEST_FILES,
    ),
    (
        pathlib.Path("./test_files/rar/v4_encrypted.rar"),
        "secret",
        100,
        1,
        hoarder.RarScheme.DOT_RNN,
        tests.test_case_file_info.TEST_FILES,
    ),
   (
        pathlib.Path("./test_files/rar/v5_split_headers_encrypted.part01.rar"),
        "dragon",
        101,
        21,
        hoarder.RarScheme.PART_N,
        tests.test_case_file_info.TEST_FILES + [tests.test_case_file_info.TEST_FILES_MAIN_DIR]
    ),
#(
#       pathlib.Path("./test_files/rar/v5_split_encrypted.part01.rar"),
#       "swordfish",
#       4,
#       17,
#       hoarder.RarScheme.PART_N,
#       tests.test_case_file_info.TEST_FILES,
#   ),
#   (
#       pathlib.Path("./test_files/rar/v5_split_unencrypted.rar"),
#       None,
#       4,
#       1,
#       hoarder.RarScheme.DOT_RNN,
#       tests.test_case_file_info.HNF_FILES,
#   ),
#   (
#       pathlib.Path("./test_files/rar/v5_unencrypted_dir.rar"),
#       None,
#       2,
#       1,
#       hoarder.RarScheme.DOT_RNN,
#       tests.test_case_file_info.TEST_FILES
#   )
]


@pytest.mark.parametrize("rar_data_tuple", RAR_TEST_ARCHIVE_DEFS)
def test_rar_archives_set(rar_data_tuple: tuple[pathlib.Path, str, int, int, hoarder.RarScheme, list[hoarder.FileEntry]]) -> None:
    (
        main_archive_path,
        password,
        n_contained_files,
        n_volumes,
        naming_scheme,
        compare_files_list,
    ) = rar_data_tuple

    main_archive_path = main_archive_path.resolve()
    rar_archive = hoarder.RarArchive.from_path(main_archive_path, password=password)
    logger.debug(f"== Listing {main_archive_path}")
    for f in rar_archive.files:
        logger.debug(f)
    logger.debug(f"==============================")
    assert len(rar_archive.files) == n_contained_files
    rar_archive.update_hash_values()
    logger.info(f"+ {list(map(lambda x: x.path,rar_archive))}")
    logger.info(f"* {list(map(lambda x: x.path,compare_files_list))}")
    assert sorted(rar_archive.files) == sorted(compare_files_list)
    assert rar_archive.path == main_archive_path
    assert rar_archive.scheme == naming_scheme
    assert rar_archive.n_volumes == n_volumes
