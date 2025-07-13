import logging
import pathlib
import tempfile

import pytest
import hoarder

logger = logging.getLogger()


@pytest.fixture(scope="session")
def create_test_dir(tmpdir_factory):
    p = tmpdir_factory.mktemp("db")
    print(type(p))
    return p


def test_repository(create_test_dir):
    ha_repo = hoarder.HashArchiveRepository(create_test_dir / "hoarder.db")
    for sfv_fn in [
        "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].sfv",
        "[Dummy] Uppercase and Brackets Ep13v2[Puresuhoruda][6519E6CF].sfv",
        "[Foobar] Lowercase and Parens - 11 (x264-AC3)(d74b7612).sfv",
        "[Test] Uppercase and Parens! S02E080 (WEB 1080p x264 10-bit AAC) (5A365C81).sfv",
    ]:
        p = pathlib.Path("../test_files/sfv/") / sfv_fn

        print(p.is_file())

        saved_sfv_file = hoarder.SfvArchive.from_path(
            pathlib.Path(p)
        )
        saved_sfv_file_path = saved_sfv_file.path
        ha_repo.save(saved_sfv_file)
        retrieved_sfv_file = ha_repo.load(saved_sfv_file_path)

        assert repr(saved_sfv_file) == repr(retrieved_sfv_file)

    for rar_fn, password in [
            ("v4_split_encrypted.rar", "dragon"),
        ("v4_split_headers_encrypted.rar", "secret"),
        ("v5_split_headers_encrypted.part01.rar", "swordfish"),
        ("v5_unencrypted.rar", None),
        ("v5_unencrypted_dir.rar", None)
    ]:
        logger.debug(rar_fn)
        saved_rar_file = hoarder.RarArchive.from_path(
            pathlib.Path("../test_files/rar/") / rar_fn,
            password=password,
        )
        saved_rar_file_path = saved_rar_file.path
        ha_repo.save(saved_rar_file)
        retrieved_rar_file = ha_repo.load(saved_rar_file_path)

        assert repr(saved_rar_file) == repr(retrieved_rar_file)

    for hnf_fn in [
        "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv",
        "[Dummy] Uppercase and Brackets Ep13v2[Puresuhoruda][6519E6CF].mkv",
        "[Foobar] Lowercase and Parens - 11 (x264-AC3)(d74b7612).mkv",
        "[Test] Uppercase and Parens! S02E080 (WEB 1080p x264 10-bit AAC) (5A365C81).mkv"
    ]:
        saved_hnf_file = hoarder.HashNameArchive.from_path(
            pathlib.Path("../test_files/hnf/") / hnf_fn
        )
        saved_hnf_file_path = saved_hnf_file.path
        ha_repo.save(saved_hnf_file)
        retrieved_hnf_file = ha_repo.load(saved_hnf_file_path)

    assert repr(saved_hnf_file) == repr(retrieved_hnf_file)
