from __future__ import annotations

import datetime as dt
from pathlib import Path, PurePath

import pytest
from hoarder import HoarderRepository
from hoarder.archives import SfvArchive
from hoarder.downloads import Download, RealFile

FROZEN_TS = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)


def _require_path(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"Required test data missing: {path}")
    return path.resolve()


@pytest.fixture(scope="session")
def compare_storage_path() -> Path:
    return _require_path(Path("./test_files"))


@pytest.fixture
def hoarder_repo(tmp_path, compare_storage_path: Path) -> HoarderRepository:
    db_path = tmp_path / "downloads.db"
    return HoarderRepository(db_path, [compare_storage_path])


def _collect_files_from_directory(
    storage_path: Path, directory_path: PurePath | str
) -> list[RealFile]:
    """Collect all files from a directory and create RealFile instances."""
    real_files: list[RealFile] = []
    files_dir = storage_path / directory_path

    if not files_dir.exists():
        pytest.skip(f"Test directory missing: {files_dir}")

    # Walk through the directory and collect all files (not directories)
    for file_path in files_dir.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(storage_path)
            real_file = RealFile.from_path(
                storage_path=storage_path,
                path=relative_path,
                include_hash=True,
            )
            real_file.first_seen = FROZEN_TS
            real_file.last_seen = FROZEN_TS
            real_files.append(real_file)

    return sorted(real_files, key=lambda rf: str(rf.path))


def _build_download(title: str, real_files: list[RealFile]) -> Download:
    """Build a Download instance with the given real files."""
    return Download(
        title=title,
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="test download",
        processed=False,
        real_files=real_files,
    )


def test_download_repository_roundtrip(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that a download can be saved and loaded correctly."""
    # Collect all files from test_files/compare/files
    real_files = _collect_files_from_directory(
        compare_storage_path, Path("compare/files")
    )
    if not real_files:
        pytest.skip("No files found in test_files/compare/files")

    # Create a download named "files"
    original = _build_download("files", real_files)

    hoarder_repo.save_download(original)

    loaded = hoarder_repo.load_download("files")

    assert loaded.title == "files"
    assert loaded.first_seen == FROZEN_TS
    assert loaded.last_seen == FROZEN_TS
    assert loaded.comment == "test download"
    assert loaded.processed is False
    assert len(loaded.real_files) == len(real_files)

    # Verify all real_files are present and correct
    loaded_paths = {rf.path for rf in loaded.real_files}
    original_paths = {rf.path for rf in real_files}
    assert loaded_paths == original_paths

    # Verify a sample real_file has correct attributes
    if real_files:
        sample_original = real_files[0]
        sample_loaded = next(
            rf for rf in loaded.real_files if rf.path == sample_original.path
        )
        assert sample_loaded.storage_path == sample_original.storage_path
        assert sample_loaded.path == sample_original.path
        assert sample_loaded.size == sample_original.size
        assert sample_loaded.hash_value == sample_original.hash_value
    assert sample_loaded.first_seen == sample_original.first_seen
    assert sample_loaded.last_seen == sample_original.last_seen
    assert len(loaded.hash_archives) == 0


def test_download_repository_persists_real_files(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that real_files associated with a download are persisted correctly."""
    real_files = _collect_files_from_directory(
        compare_storage_path, PurePath("compare/files")
    )
    if not real_files:
        pytest.skip("No files found in test_files/compare/files")

    # Take a subset for this test
    test_files = real_files[:5] if len(real_files) >= 5 else real_files

    download = _build_download("files", test_files)

    hoarder_repo.save_download(download)
    loaded = hoarder_repo.load_download("files")

    assert len(loaded.real_files) == len(test_files)
    for original_file in test_files:
        loaded_file = next(
            rf for rf in loaded.real_files if rf.path == original_file.path
        )
        assert loaded_file.size == original_file.size
        assert loaded_file.hash_value == original_file.hash_value
        assert loaded_file.algo == original_file.algo


def test_download_repository_empty_real_files(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that a download with no real_files can be saved and loaded."""
    download = Download(
        title="empty download",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="empty download",
        processed=True,
        real_files=[],
    )

    hoarder_repo.save_download(download)
    loaded = hoarder_repo.load_download("empty download")

    assert loaded.title == "empty download"
    assert loaded.comment == "empty download"
    assert loaded.processed is True
    assert loaded.real_files == []
    assert loaded.hash_archives == []


def test_download_repository_updates_existing_download(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that saving a download with the same path updates the existing record."""
    real_files = _collect_files_from_directory(
        compare_storage_path, PurePath("compare/files")
    )
    if not real_files:
        pytest.skip("No files found in test_files/compare/files")

    # Create initial download
    download1 = _build_download("files", real_files[:3])
    download1.comment = "initial comment"
    download1.processed = False

    hoarder_repo.save_download(download1)

    # Update with different data
    download2 = _build_download("files", real_files)
    download2.comment = "updated comment"
    download2.processed = True

    hoarder_repo.save_download(download2)

    loaded = hoarder_repo.load_download("files")

    assert loaded.comment == "updated comment"
    assert loaded.processed is True
    assert len(loaded.real_files) == len(real_files)


def test_download_repository_disallows_unknown_storage_path_on_save(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that saving a download with real_files from disallowed storage path raises ValueError."""
    disallowed_storage = compare_storage_path.parent
    real_file = RealFile(
        storage_path=disallowed_storage,
        path=Path("nonexistent.dat"),
        size=0,
        is_dir=False,
    )
    download = Download(
        title="test download",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment=None,
        processed=False,
        real_files=[real_file],
    )

    with pytest.raises(ValueError):
        hoarder_repo.save_download(download)


def test_download_repository_file_not_found(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that loading a non-existent download raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        hoarder_repo.load_download("nonexistent")


def test_download_repository_persists_hash_archives(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that hash_archives associated with a download are persisted correctly."""
    # Load an SFV archive from test files
    if not Path("./test_files/sfv").exists():
        pytest.skip("SFV test files not found")

    if not Path("./test_files/sfv/files.sfv").exists():
        pytest.skip("SFV file not found")

    sfv_archive = SfvArchive.from_path(compare_storage_path, PurePath("sfv/files.sfv"))
    hoarder_repo.save_hash_archive(sfv_archive)

    # Create a download with hash archives
    download = Download(
        title="download with archives",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="test with archives",
        processed=False,
        real_files=[],
        hash_archives=[sfv_archive],
    )

    hoarder_repo.save_download(download)
    loaded = hoarder_repo.load_download("download with archives")

    assert len(loaded.hash_archives) == 1
    loaded_archive = loaded.hash_archives[0]
    assert loaded_archive.storage_path == sfv_archive.storage_path
    assert loaded_archive.path == sfv_archive.path
    assert loaded_archive.__class__ == sfv_archive.__class__
    assert len(loaded_archive.files) == len(sfv_archive.files)


def test_download_repository_persists_real_files_and_hash_archives(
    hoarder_repo: HoarderRepository, compare_storage_path: Path
) -> None:
    """Test that a download with both real_files and hash_archives is persisted correctly."""
    # Collect some real files
    real_files = _collect_files_from_directory(
        compare_storage_path, Path("compare/files")
    )
    if not real_files:
        pytest.skip("No files found in test_files/compare/files")

    # Take a small subset
    test_files = real_files[:3] if len(real_files) >= 3 else real_files

    # Load an SFV archive
    if not Path("./test_files/sfv").exists():
        pytest.skip("SFV test files not found")

    if not Path("./test_files/sfv/files.sfv").exists():
        pytest.skip("SFV file not found")

    sfv_archive = SfvArchive.from_path(compare_storage_path, PurePath("sfv/files.sfv"))
    hoarder_repo.save_hash_archive(sfv_archive)

    # Create a download with both
    download = _build_download("files with archives", test_files)
    download.hash_archives = [sfv_archive]

    hoarder_repo.save_download(download)
    loaded = hoarder_repo.load_download("files with archives")

    assert len(loaded.real_files) == len(test_files)
    assert len(loaded.hash_archives) == 1
    assert loaded.hash_archives[0].path == sfv_archive.path
