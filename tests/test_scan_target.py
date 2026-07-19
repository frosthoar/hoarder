"""Tests for ScanTarget."""

from pathlib import Path, PurePath

from hoarder.phases import ScanTarget
from hoarder.utils import AnchoredPath


def test_get_file_search_paths_is_just_the_target_itself() -> None:
    target = ScanTarget(anchor=AnchoredPath(Path("test_files"), PurePath("sfv")))
    assert target.get_file_search_paths() == [target.anchor]


def test_get_archive_search_paths_includes_subdirectories(tmp_path: Path) -> None:
    """An archive living in a release's subdirectory (e.g. a per-disc
    "CD1/checks.sfv") must be found even though it isn't in the anchor's own
    top-level directory - discover() itself only looks at one directory, so
    this method has to enumerate every subdirectory beneath the anchor,
    matching the recursive walk get_file_search_paths()/discover_real_files()
    already does for real files."""
    (tmp_path / "CD1").mkdir()
    (tmp_path / "CD2" / "nested").mkdir(parents=True)

    target = ScanTarget(anchor=AnchoredPath(tmp_path, PurePath(".")))
    paths = target.get_archive_search_paths()

    relative_paths = {p.relative_path for p in paths}
    assert relative_paths == {
        PurePath("."),
        PurePath("CD1"),
        PurePath("CD2"),
        PurePath("CD2/nested"),
    }


def test_get_archive_search_paths_single_file_anchor_is_not_walked() -> None:
    """A file anchor (e.g. a RAR archive itself, not a release directory)
    has no subdirectories to enumerate - it's just itself."""
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files/rar"), PurePath("v5_unencrypted.rar"))
    )
    assert target.get_archive_search_paths() == [target.anchor]


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


def test_get_archive_search_paths_skips_parent_for_storage_root_itself(
    tmp_path: Path,
) -> None:
    """When the target *is* the storage root, there's no parent to add,
    even with search_parent enabled. Uses an empty tmp_path (rather than
    test_files, which has many subdirectories) so the assertion isn't also
    exercising the subdirectory-recursion this method separately does."""
    target = ScanTarget(
        anchor=AnchoredPath(tmp_path, PurePath(".")),
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
