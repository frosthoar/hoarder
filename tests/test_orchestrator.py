"""End-to-end tests for process_target()."""

import zlib
from pathlib import Path, PurePath

from hoarder.archives import AbstractRarArchive
from hoarder.passwords import PasswordStore
from hoarder.phases import ScanTarget, process_target
from hoarder.utils import AnchoredPath, Presentable

ENCRYPTED_RAR_FIXTURE = Path("test_files/rar/v4_content_and_headers_encrypted.rar")
ENCRYPTED_RAR_PASSWORD = "secret"


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


def test_processing_result_to_presentation() -> None:
    target = ScanTarget(
        anchor=AnchoredPath(Path("test_files/scan_target"), PurePath("release"))
    )
    result = process_target(target)

    presentable: Presentable = result  # structural check: satisfies the protocol
    spec = presentable.to_presentation()

    assert spec["scalar"]["archives"] == 1
    assert spec["scalar"]["real_files"] == 1
    assert spec["scalar"]["matched_files"] == 1

    assert len(spec["collections"]["archives"]) == 1
    archive_row = spec["collections"]["archives"][0]
    assert archive_row["type"] == "SfvArchive"

    assert len(spec["collections"]["real_files"]) == 1
    file_row = spec["collections"]["real_files"][0]
    assert file_row["matched"] is True
    assert file_row["matched_entries"] == "data/note.txt"


def test_process_target_resolves_a_password_protected_archive_when_known() -> None:
    """title defaults to the anchor's own name, since the anchor here is
    the archive file itself (not a release directory)."""
    assert (
        ENCRYPTED_RAR_FIXTURE.exists()
    ), f"Committed RAR fixture missing: {ENCRYPTED_RAR_FIXTURE}"
    target = ScanTarget(
        anchor=AnchoredPath(
            ENCRYPTED_RAR_FIXTURE.parent, PurePath(ENCRYPTED_RAR_FIXTURE.name)
        )
    )
    store = PasswordStore()
    store.add_password(ENCRYPTED_RAR_FIXTURE.name, "wrong-guess")
    store.add_password(ENCRYPTED_RAR_FIXTURE.name, ENCRYPTED_RAR_PASSWORD)

    result = process_target(target, password_store=store)

    assert len(result.archives) == 1
    archive = result.archives[0]
    assert isinstance(archive, AbstractRarArchive)
    assert archive.requires_password is True
    assert archive.password == ENCRYPTED_RAR_PASSWORD
    assert len(archive.files) > 0


def test_process_target_keeps_unresolved_password_protected_archive_visible() -> None:
    """No known password works: the archive still shows up in results
    (so it's findable/persistable later) rather than vanishing, but stays
    an unopened placeholder."""
    assert (
        ENCRYPTED_RAR_FIXTURE.exists()
    ), f"Committed RAR fixture missing: {ENCRYPTED_RAR_FIXTURE}"
    target = ScanTarget(
        anchor=AnchoredPath(
            ENCRYPTED_RAR_FIXTURE.parent, PurePath(ENCRYPTED_RAR_FIXTURE.name)
        )
    )
    store = PasswordStore()
    store.add_password(ENCRYPTED_RAR_FIXTURE.name, "wrong-guess")

    result = process_target(target, password_store=store)

    assert len(result.archives) == 1
    archive = result.archives[0]
    assert isinstance(archive, AbstractRarArchive)
    assert archive.requires_password is True
    assert archive.password is None
    assert archive.files == set()


def test_process_target_discovers_archives_in_a_release_subdirectory(
    tmp_path: Path,
) -> None:
    """A release's archive isn't always at its top level - e.g. a per-disc
    "CD1/checks.sfv" verifying "CD1/payload.bin". discover() itself only
    looks at one directory, so this must be found via the anchor's
    subdirectory recursion (ScanTarget.get_archive_search_paths), not
    silently left as an unmatched real file."""
    subdir = tmp_path / "release" / "CD1"
    subdir.mkdir(parents=True)
    payload = subdir / "payload.bin"
    payload.write_bytes(b"hello world")
    crc = zlib.crc32(payload.read_bytes()) & 0xFFFFFFFF
    (subdir / "checks.sfv").write_text(f"payload.bin {crc:08X}\n")

    target = ScanTarget(anchor=AnchoredPath(tmp_path, PurePath("release")))
    result = process_target(target)

    assert len(result.archives) == 1
    assert result.archives[0].anchor.relative_path == PurePath("release/CD1/checks.sfv")

    assert len(result.real_files) == 1
    real_file = result.real_files[0]
    assert real_file.anchor.relative_path == PurePath("release/CD1/payload.bin")
    assert result.matches[real_file]


def test_process_target_finds_nothing_for_an_empty_directory(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    target = ScanTarget(anchor=AnchoredPath(tmp_path, PurePath("empty")))

    result = process_target(target)

    assert result.archives == []
    assert result.real_files == []
    assert result.matches == {}
