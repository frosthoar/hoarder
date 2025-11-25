from __future__ import annotations

import datetime as dt
from pathlib import Path, PurePath

import pytest

import tests.test_case_file_info as case_files
from hoarder.archives import Algo, SfvArchive
from hoarder.realfiles import (
    RealFile,
    RealFileRepository,
    Verification,
    VerificationSource,
)

FROZEN_TS = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)


def _require_path(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"Required test data missing: {path}")
    return path.resolve()


@pytest.fixture(scope="session")
def compare_storage_path() -> Path:
    return _require_path(Path("./test_files/compare"))


@pytest.fixture
def real_file_repo(tmp_path, compare_storage_path: Path) -> RealFileRepository:
    db_path = tmp_path / "realfiles.db"
    return RealFileRepository(db_path, [compare_storage_path])


def _build_real_file(entry: case_files.FileEntry, storage_path: Path) -> RealFile:
    real_file = RealFile.from_path(
        storage_path=storage_path,
        path=entry.path,
        include_hash=not entry.is_dir,
    )
    real_file.first_seen = FROZEN_TS
    real_file.last_seen = FROZEN_TS
    real_file.comment = "test"
    return real_file


def test_real_file_repository_roundtrip(real_file_repo: RealFileRepository, compare_storage_path: Path) -> None:
    entry = next(file for file in case_files.TEST_FILES if not file.is_dir)
    full_path = compare_storage_path / entry.path
    if not full_path.exists():
        pytest.skip(f"Fixture file missing: {full_path}")

    original = _build_real_file(entry, compare_storage_path)
    real_file_repo.save(original)

    loaded = real_file_repo.load(compare_storage_path, entry.path)

    assert loaded.storage_path == compare_storage_path
    assert loaded.path == entry.path
    assert loaded.size == original.size
    assert loaded.hash_value == original.hash_value
    assert loaded.first_seen == FROZEN_TS
    assert loaded.last_seen == FROZEN_TS
    assert loaded.comment == "test"
    assert loaded.verification == []


def test_real_file_repository_persists_verifications(real_file_repo: RealFileRepository, compare_storage_path: Path) -> None:
    entry = next(file for file in case_files.TEST_FILES if not file.is_dir)
    real_file = _build_real_file(entry, compare_storage_path)

    verification = Verification(
        real_file=real_file,
        source_type=VerificationSource.ARCHIVE,
        hash_archive=None,
        hash_value=real_file.hash_value or b"",
        algo=real_file.algo or Algo.CRC32,
        comment="verified from archive",
    )
    real_file.verification.append(verification)

    real_file_repo.save(real_file)
    loaded = real_file_repo.load(compare_storage_path, entry.path)

    assert len(loaded.verification) == 1
    loaded_verification = loaded.verification[0]
    assert loaded_verification.source_type is VerificationSource.ARCHIVE
    assert loaded_verification.hash_archive is None
    assert loaded_verification.hash_value == verification.hash_value
    assert loaded_verification.algo == verification.algo
    assert loaded_verification.comment == "verified from archive"
    assert loaded_verification.verified


def test_real_file_repository_requires_known_hash_archive(real_file_repo: RealFileRepository, compare_storage_path: Path) -> None:
    sfv_path = Path("./test_files/sfv/files.sfv")
    if not sfv_path.exists():
        pytest.skip(f"SFV test file missing: {sfv_path}")
    sfv_archive = SfvArchive.from_path(sfv_path.parent, PurePath(sfv_path.name))

    entry = next(file for file in case_files.TEST_FILES if not file.is_dir)
    real_file = _build_real_file(entry, compare_storage_path)
    verification = Verification(
        real_file=real_file,
        source_type=VerificationSource.ARCHIVE,
        hash_archive=sfv_archive,
        hash_value=real_file.hash_value or b"",
        algo=real_file.algo or Algo.CRC32,
        comment=None,
    )
    real_file.verification.append(verification)

    with pytest.raises(ValueError):
        real_file_repo.save(real_file)


def test_real_file_repository_disallows_unknown_storage_path_on_save(real_file_repo: RealFileRepository, compare_storage_path: Path) -> None:
    disallowed_storage = compare_storage_path.parent
    real_file = RealFile(
        storage_path=disallowed_storage,
        path=PurePath("nonexistent.dat"),
        size=0,
        is_dir=False,
        algo=None,
        hash_value=None,
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment=None,
    )

    with pytest.raises(ValueError):
        real_file_repo.save(real_file)


def test_real_file_repository_disallows_unknown_storage_path_on_load(real_file_repo: RealFileRepository, compare_storage_path: Path) -> None:
    disallowed_storage = compare_storage_path.parent
    with pytest.raises(ValueError):
        real_file_repo.load(disallowed_storage, PurePath("missing"))


def test_real_file_repository_validates_paths_on_init(tmp_path) -> None:
    missing_path = Path("/nonexistent/path")
    with pytest.raises(FileNotFoundError):
        RealFileRepository(tmp_path / "db.sqlite", [missing_path])

    existing_path = Path("./test_files/compare")
    if not existing_path.exists():
        pytest.skip(f"Fixture path missing: {existing_path}")
    repo = RealFileRepository(tmp_path / "db.sqlite", [existing_path])
    assert existing_path.resolve() in repo._allowed_storage_paths

