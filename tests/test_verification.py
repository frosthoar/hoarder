"""Tests for verify_real_files()."""

from pathlib import Path, PurePath

from hoarder.archives import HashNameArchive, SfvArchive
from hoarder.downloads import RealFile, VerificationSource
from hoarder.phases import verify_real_files

SCAN_TARGET_ROOT = Path("test_files/scan_target/release")
HNF_ROOT = Path("test_files/hnf")
HNF_FIXTURE = "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv"
HNF_WRONG_HASH_FIXTURE = "[Corrupt] 06. Wrong Hash In Name [x265][1080p][56217F28].mkv"
COMPARE_ROOT = Path("test_files/compare")


def _load_archive() -> SfvArchive:
    return SfvArchive.from_path(SCAN_TARGET_ROOT, PurePath("data.sfv"))


def _load_real_files() -> list[RealFile]:
    return [RealFile.from_path(SCAN_TARGET_ROOT, PurePath("data/note.txt"))]


def test_archive_match_is_verified_and_trusted() -> None:
    archive = _load_archive()
    real_files = _load_real_files()

    verify_real_files([archive], real_files)

    real_file = real_files[0]
    assert len(real_file.verification) == 1
    verification = real_file.verification[0]
    assert verification.source_type == VerificationSource.ARCHIVE
    assert verification.verified is True
    assert verification.is_trusted is True


def test_hash_name_archive_match_is_filename_source() -> None:
    archive = HashNameArchive.from_path(HNF_ROOT, PurePath(HNF_FIXTURE))
    real_files = [RealFile.from_path(HNF_ROOT, PurePath(HNF_FIXTURE))]

    verify_real_files([archive], real_files)

    real_file = real_files[0]
    assert len(real_file.verification) == 1
    verification = real_file.verification[0]
    assert verification.source_type == VerificationSource.FILENAME
    assert verification.verified is True
    assert verification.is_trusted is True


def test_hash_name_archive_wrong_hash_is_not_verified() -> None:
    """test_files/hnf's [Corrupt]... fixture has a name-embedded hash that
    does not match its real content - the FILENAME-source counterpart to
    test_wrong_asserted_hash_is_not_verified below."""
    archive = HashNameArchive.from_path(HNF_ROOT, PurePath(HNF_WRONG_HASH_FIXTURE))
    real_files = [RealFile.from_path(HNF_ROOT, PurePath(HNF_WRONG_HASH_FIXTURE))]

    verify_real_files([archive], real_files)

    real_file = real_files[0]
    assert len(real_file.verification) == 1
    verification = real_file.verification[0]
    assert verification.source_type == VerificationSource.FILENAME
    assert verification.verified is False
    assert verification.is_trusted is False


def test_wrong_asserted_hash_is_not_verified() -> None:
    """test_files/compare/wrong_checksum.sfv deliberately misstates the
    checksum of the committed files/stock.raw (real CRC32 A086542D)."""
    archive = SfvArchive.from_path(COMPARE_ROOT, PurePath("wrong_checksum.sfv"))
    real_files = [RealFile.from_path(COMPARE_ROOT, PurePath("files/stock.raw"))]

    verify_real_files([archive], real_files)

    real_file = real_files[0]
    assert len(real_file.verification) == 1
    verification = real_file.verification[0]
    assert verification.verified is False
    assert verification.is_trusted is False


def test_unmatched_real_file_gets_an_untrusted_self_hash() -> None:
    real_files = _load_real_files()

    verify_real_files([], real_files)

    real_file = real_files[0]
    assert len(real_file.verification) == 1
    verification = real_file.verification[0]
    assert verification.source_type == VerificationSource.SELF_HASH
    assert verification.source == real_file.anchor
    assert verification.verified is True
    assert verification.is_trusted is False


def test_real_file_matched_by_two_archives_gets_two_verifications() -> None:
    """Two independent loads of the same committed data.sfv, standing in
    for two distinct sources that both correctly check the same file (e.g.
    duplicate release-group SFVs) - exercises accumulation, not source-type
    mixing (already covered by the ARCHIVE/FILENAME tests above)."""
    first_load = _load_archive()
    second_load = _load_archive()
    real_files = _load_real_files()

    verify_real_files([first_load, second_load], real_files)

    real_file = real_files[0]
    assert len(real_file.verification) == 2
    assert all(
        v.source_type == VerificationSource.ARCHIVE for v in real_file.verification
    )
    assert all(v.verified for v in real_file.verification)


def test_directories_are_skipped() -> None:
    real_files = [RealFile.from_path(SCAN_TARGET_ROOT, PurePath("data"))]
    assert real_files[0].is_dir is True

    verify_real_files([], real_files)

    assert real_files[0].verification == []
