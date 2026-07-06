"""Tests for ScanTarget and DiscoveryConfig."""

from pathlib import Path, PurePath, PurePosixPath

from hoarder.phases import DiscoveryConfig, ScanTarget
from hoarder.utils import AnchoredPath


def test_get_file_search_paths_is_just_the_target_itself() -> None:
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath("sfv")))
    assert target.get_file_search_paths() == [target.anchor]


def test_get_archive_search_paths_includes_parent_by_default() -> None:
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath("sfv")))
    paths = target.get_archive_search_paths()
    assert paths[0] == target.anchor
    assert paths[1].relative_path == PurePosixPath(".")
    assert paths[1].storage_path == target.anchor.storage_path


def test_get_archive_search_paths_skips_parent_when_disabled() -> None:
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files"), PurePath("sfv")),
        config=DiscoveryConfig(search_parent=False),
    )
    assert target.get_archive_search_paths() == [target.anchor]


def test_get_archive_search_paths_skips_parent_for_storage_root_itself() -> None:
    """When the target *is* the storage root, there's no parent to add."""
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath(".")))
    assert target.get_archive_search_paths() == [target.anchor]


def test_get_archive_search_paths_includes_additional_paths() -> None:
    extra = AnchoredPath(Path("test_files"), PurePath("hnf"))
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files"), PurePath("sfv")),
        config=DiscoveryConfig(search_parent=False, additional_paths=[extra]),
    )
    assert target.get_archive_search_paths() == [target.anchor, extra]


def test_full_path_delegates_to_anchor() -> None:
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath("sfv")))
    assert target.full_path == target.anchor.full_path
