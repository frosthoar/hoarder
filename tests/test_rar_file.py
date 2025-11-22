import logging
import pathlib

import pytest
import tests.test_case_file_info

from hoarder.archives import FileEntry, RarArchive, RarScheme

logger = logging.getLogger("hoarder.test_rar_file")


@pytest.mark.parametrize(
    "rar_data_tuple", tests.test_case_file_info.RAR_TEST_ARCHIVE_DEFS
)
def test_rar_archives_set(
    rar_data_tuple: tuple[pathlib.Path, str, int, int, RarScheme, list[FileEntry]]
) -> None:
    (
        main_archive_path,
        password,
        n_contained_files,
        n_volumes,
        naming_scheme,
        compare_files_list,
    ) = rar_data_tuple

    main_archive_path = main_archive_path.resolve()
    rar_archive = RarArchive.from_path(main_archive_path, password=password)
    logger.debug(f"== Listing {main_archive_path}")
    for f in rar_archive.files:
        logger.debug(f)
    logger.debug("==============================")
    assert len(rar_archive.files) == n_contained_files
    rar_archive.update_hash_values()
    logger.info(f"+ {list(map(lambda x: x.path,rar_archive))}")
    logger.info(f"* {list(map(lambda x: x.path,compare_files_list))}")
    assert sorted(rar_archive.files) == sorted(compare_files_list)
    assert rar_archive.path == main_archive_path
    assert rar_archive.scheme == naming_scheme
    assert rar_archive.n_volumes == n_volumes
