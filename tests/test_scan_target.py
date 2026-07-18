"""Tests for ScanTarget."""

from pathlib import Path, PurePath

from hoarder.phases import ScanTarget
from hoarder.utils import AnchoredPath


def test_get_file_search_paths_is_just_the_target_itself() -> None:
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath("sfv")))
    assert target.get_file_search_paths() == [target.anchor]


def test_get_archive_search_paths_excludes_parent_by_default() -> None:
    """A ScanTarget's anchor is normally a directory holding one release, so
    its parent (e.g. the whole downloads folder) isn't a useful place to
    look for archives by default - see ScanTarget.search_parent."""
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath("sfv")))
    assert target.get_archive_search_paths() == [target.anchor]


def test_get_archive_search_paths_includes_parent_when_enabled() -> None:
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files"), PurePath("sfv")),
        search_parent=True,
    )
    paths = target.get_archive_search_paths()
    assert paths[0] == target.anchor
    assert paths[1].relative_path == PurePath(".")
    assert paths[1].storage_path == target.anchor.storage_path


def test_get_archive_search_paths_skips_parent_for_storage_root_itself() -> None:
    """When the target *is* the storage root, there's no parent to add,
    even with search_parent enabled."""
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files"), PurePath(".")),
        search_parent=True,
    )
    assert target.get_archive_search_paths() == [target.anchor]


def test_get_archive_search_paths_includes_archive_paths() -> None:
    extra = AnchoredPath(Path("test_files"), PurePath("hnf"))
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files"), PurePath("sfv")),
        archive_paths=[extra],
    )
    assert target.get_archive_search_paths() == [target.anchor, extra]


def test_get_archive_search_paths_archive_path_need_not_be_under_anchor_root() -> None:
    """archive_paths are independent AnchoredPaths - each carries its own
    storage_path, so an archive location elsewhere on disk (a different
    storage root entirely) is valid, not just paths nested under the
    anchor's own storage_path."""
    other_root = AnchoredPath(Path("test_files/compare"), PurePath("files"))
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files"), PurePath("sfv")),
        archive_paths=[other_root],
    )
    assert target.get_archive_search_paths() == [target.anchor, other_root]


def test_full_path_delegates_to_anchor() -> None:
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath("sfv")))
    assert target.full_path == target.anchor.full_path
