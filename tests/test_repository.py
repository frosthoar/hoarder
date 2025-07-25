import logging
import pathlib

import hoarder
import pytest

logger = logging.getLogger()


@pytest.fixture(scope="session")
def create_test_repo(tmpdir_factory):
    p = tmpdir_factory.mktemp("db")
    ha_repo = hoarder.HashArchiveRepository(pathlib.Path(p / "hoarder.db"))
    return ha_repo


def test_sfv_repositories(create_test_repo):
    for sfv_fn in [
        "files.sfv",
    ]:
        p = pathlib.Path("./test_files/sfv/") / sfv_fn

        print(p.is_file())

        saved_sfv_file = hoarder.SfvArchive.from_path(pathlib.Path(p))
        saved_sfv_file_path = saved_sfv_file.path
        create_test_repo.save(saved_sfv_file)
        retrieved_sfv_file = create_test_repo.load(saved_sfv_file_path)

        assert repr(saved_sfv_file) == repr(retrieved_sfv_file)


def test_rar_repositories(create_test_repo):
    for rar_fn, password in [
        ("v4_split_headers_encrypted.rar", "password"),
        ("v4_split_headers_unencrypted.rar", None),
        ("v4_unencrypted.rar", None),
        ("v4_encrypted.rar", "secret"),
        ("v5_split_headers_encrypted.part01.rar", "ninja"),
        ("v5_split_headers_unencrypted.part01.rar", None),
        ("v5_headers_encrypted.rar", "dragon"),
        ("v5_headers_unencrypted.rar", None),
    ]:
        logger.debug(rar_fn)
        saved_rar_file = hoarder.RarArchive.from_path(
            pathlib.Path("./test_files/rar/") / rar_fn,
            password=password,
        )
        saved_rar_file_path = saved_rar_file.path
        create_test_repo.save(saved_rar_file)
        retrieved_rar_file = create_test_repo.load(saved_rar_file_path)

        assert repr(saved_rar_file) == repr(retrieved_rar_file)


def test_hnf_repositories(create_test_repo):
    for hnf_fn in [
        "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv",
        "[Dummy] Uppercase and Brackets Ep13v2[Puresuhoruda][6519E6CF].mkv",
        "[Foobar] Lowercase and Parens - 11 (x264-AC3)(d74b7612).mkv",
        "[Test] Uppercase and Parens! S02E080 (WEB 1080p x264 10-bit AAC) (5A365C81).mkv",
    ]:
        saved_hnf_file = hoarder.HashNameArchive.from_path(
            pathlib.Path("./test_files/hnf/") / hnf_fn
        )
        saved_hnf_file_path = saved_hnf_file.path
        create_test_repo.save(saved_hnf_file)
        retrieved_hnf_file = create_test_repo.load(saved_hnf_file_path)

    assert repr(saved_hnf_file) == repr(retrieved_hnf_file)
