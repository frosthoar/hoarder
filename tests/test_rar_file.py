import logging
import pathlib
import collections.abc

import pytest
import hoarder
import tests.compare_files

logger = logging.getLogger("hoarder.test_rar_file")

RAR_TUPLES = [
    (
        "../test_files/rar/v4_split_encrypted.rar",
        "dragon",
        4,
        9,
        hoarder.RarScheme.DOT_RNN,
        tests.compare_files.hnf_file_entries,
    ),
    (
        "../test_files/rar/v4_split_headers_encrypted.rar",
        "secret",
        4,
        9,
        hoarder.RarScheme.DOT_RNN,
        tests.compare_files.hnf_file_entries,
    ),
]


@pytest.mark.parametrize("rar_data_tuple", RAR_TUPLES)
def test_rar_archives_set(rar_data_tuple) -> None:
    print(rar_data_tuple)
    (
        main_archive_path,
        password,
        n_contained_files,
        n_volumes,
        naming_scheme,
        compare_files_list,
    ) = rar_data_tuple

    main_archive_path = (pathlib.Path(main_archive_path)).resolve()
    rar_archive = hoarder.RarArchive.from_path(main_archive_path, password=password)
    logger.debug(f"== Listing {main_archive_path}")
    for f in rar_archive.files:
        logger.debug(f)
    logger.debug(f"==============================")
    assert len(rar_archive.files) == n_contained_files
    rar_archive.update_hash_values()
    assert sorted(rar_archive.files) == sorted(compare_files_list)
    assert rar_archive.path == main_archive_path
    assert rar_archive.scheme == naming_scheme
    assert rar_archive.n_volumes == n_volumes


def x() -> collections.abc.Generator[int]:
    yield 1
