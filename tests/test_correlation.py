"""Tests for correlate_archives() and correlate_files_to_entries()."""

from pathlib import Path, PurePath

from hoarder.archives import RarArchive, SfvArchive
from hoarder.downloads import RealFile
from hoarder.phases import correlate_archives, correlate_files_to_entries
from hoarder.utils import AnchoredPath

SCAN_TARGET_ROOT = Path("test_files/scan_target/release")
RAR_ROOT = Path("test_files/rar")


def _load_archive() -> SfvArchive:
    return SfvArchive.from_path(SCAN_TARGET_ROOT, PurePath("data.sfv"))


def _load_real_files() -> list[RealFile]:
    return [RealFile.from_path(SCAN_TARGET_ROOT, PurePath("data/note.txt"))]


def test_correlate_archives_keeps_archives_with_matching_real_files() -> None:
    archive = _load_archive()
    real_files = _load_real_files()

    relevant = correlate_archives([archive], real_files)

    assert relevant == [archive]


def test_correlate_archives_drops_archives_without_matching_real_files() -> None:
    archive = _load_archive()
    unrelated_real_file = RealFile(
        anchor=AnchoredPath(SCAN_TARGET_ROOT, PurePath("data.sfv")),
        size=0,
        is_dir=False,
    )

    relevant = correlate_archives([archive], [unrelated_real_file])

    assert relevant == []


def test_correlate_archives_keeps_password_protected_archives_without_a_match() -> None:
    """A password-protected archive we couldn't open has no files to match
    by content, but must not be dropped: that would undo discover()'s
    whole point of keeping it visible for a later password retry."""
    fixture = RAR_ROOT / "v4_content_and_headers_encrypted.rar"
    assert fixture.exists(), f"Committed RAR fixture missing: {fixture}"
    stub = RarArchive.discover(AnchoredPath(RAR_ROOT, PurePath(fixture.name)))[0]
    assert stub.requires_password is True
    assert stub.files == set()

    relevant = correlate_archives([stub], [])

    assert relevant == [stub]


def test_correlate_files_to_entries_matches_by_absolute_path() -> None:
    archive = _load_archive()
    real_files = _load_real_files()

    matches = correlate_files_to_entries(real_files, [archive])

    assert len(matches) == 1
    entries = matches[real_files[0]]
    assert len(entries) == 1
    assert entries[0].path == PurePath("data/note.txt")


def test_correlate_files_to_entries_excludes_unmatched_real_files() -> None:
    archive = _load_archive()
    unmatched = RealFile(
        anchor=AnchoredPath(SCAN_TARGET_ROOT, PurePath("data.sfv")),
        size=0,
        is_dir=False,
    )

    matches = correlate_files_to_entries([unmatched], [archive])

    assert matches == {}
