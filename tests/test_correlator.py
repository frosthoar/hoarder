"""Tests for correlate_archives() and correlate_files_to_entries()."""

from pathlib import Path, PurePath, PurePosixPath

from hoarder.archives import SfvArchive
from hoarder.downloads import RealFile
from hoarder.phases import correlate_archives, correlate_files_to_entries
from hoarder.utils import AnchoredPath

SCAN_TARGET_ROOT = Path("test_files/scan_target/release")


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


def test_correlate_files_to_entries_matches_by_absolute_path() -> None:
    archive = _load_archive()
    real_files = _load_real_files()

    matches = correlate_files_to_entries(real_files, [archive])

    assert len(matches) == 1
    entries = matches[real_files[0]]
    assert len(entries) == 1
    assert entries[0].path == PurePosixPath("data/note.txt")


def test_correlate_files_to_entries_excludes_unmatched_real_files() -> None:
    archive = _load_archive()
    unmatched = RealFile(
        anchor=AnchoredPath(SCAN_TARGET_ROOT, PurePath("data.sfv")),
        size=0,
        is_dir=False,
    )

    matches = correlate_files_to_entries([unmatched], [archive])

    assert matches == {}
