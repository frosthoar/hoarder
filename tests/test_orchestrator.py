"""End-to-end tests for process_target()."""

from pathlib import Path, PurePath

from hoarder.phases import ScanTarget, process_target
from hoarder.utils import AnchoredPath


def test_process_target_discovers_and_correlates_a_release() -> None:
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files/scan_target"), PurePath("release"))
    )

    result = process_target(target)

    assert len(result.archives) == 1
    assert str(result.archives[0].anchor.relative_path) == "release/data.sfv"

    assert len(result.real_files) == 1
    real_file = result.real_files[0]
    assert str(real_file.anchor.relative_path) == "release/data/note.txt"

    assert len(result.matches) == 1
    entries = result.matches[real_file]
    assert len(entries) == 1
    assert entries[0].path == PurePath("data/note.txt")


def test_process_target_finds_nothing_for_an_empty_directory(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    target = ScanTarget(anchor=AnchoredPath(tmp_path, PurePath("empty")))

    result = process_target(target)

    assert result.archives == []
    assert result.real_files == []
    assert result.matches == {}
