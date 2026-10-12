"""Tests for discover_real_files() and collect_archive_paths()."""

from pathlib import Path, PurePath

from hoarder.archives import SfvArchive
from hoarder.phases import collect_archive_paths, discover_real_files
from hoarder.utils import AnchoredPath

SCAN_TARGET_ROOT = Path("test_files/scan_target")


def test_discover_real_files_walks_directory() -> None:
    scope = AnchoredPath(SCAN_TARGET_ROOT, PurePath("release"))
    real_files = discover_real_files([scope])

    relative_paths = {rf.anchor.relative_path for rf in real_files}
    assert relative_paths == {
        PurePath("release/data.sfv"),
        PurePath("release/data/note.txt"),
    }


def test_discover_real_files_excludes_given_paths() -> None:
    scope = AnchoredPath(SCAN_TARGET_ROOT, PurePath("release"))
    sfv_full_path = (SCAN_TARGET_ROOT / "release" / "data.sfv").resolve()

    real_files = discover_real_files([scope], exclude={sfv_full_path})

    relative_paths = {rf.anchor.relative_path for rf in real_files}
    assert relative_paths == {PurePath("release/data/note.txt")}


def test_discover_real_files_single_file_scope() -> None:
    scope = AnchoredPath(SCAN_TARGET_ROOT, PurePath("release/data/note.txt"))
    real_files = discover_real_files([scope])
    assert len(real_files) == 1
    assert real_files[0].anchor.relative_path == PurePath("release/data/note.txt")


def test_discover_real_files_ignores_nfo_and_par2(tmp_path: Path) -> None:
    (tmp_path / "payload.bin").write_bytes(b"data")
    (tmp_path / "release.nfo").write_text("scene info")
    (tmp_path / "release.par2").write_bytes(b"recovery")
    (tmp_path / "release.vol000+01.PAR2").write_bytes(b"recovery")

    scope = AnchoredPath(tmp_path, PurePath("."))
    real_files = discover_real_files([scope])

    relative_paths = {rf.anchor.relative_path for rf in real_files}
    assert relative_paths == {PurePath("payload.bin")}


def test_discover_real_files_ignores_single_file_scope_with_ignored_extension(
    tmp_path: Path,
) -> None:
    (tmp_path / "release.nfo").write_text("scene info")

    scope = AnchoredPath(tmp_path, PurePath("release.nfo"))
    real_files = discover_real_files([scope])

    assert real_files == []


def test_collect_archive_paths_returns_full_path_for_single_file_archives() -> None:
    archive = SfvArchive.from_path(SCAN_TARGET_ROOT / "release", PurePath("data.sfv"))
    paths = collect_archive_paths([archive])
    assert paths == {archive.full_path}
