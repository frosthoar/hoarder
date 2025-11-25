import logging
import pathlib
import typing

import pytest
from hoarder.archives import (
    HashArchiveRepository,
    HashNameArchive,
    RarArchive,
    SfvArchive,
)
from tests.test_case_file_info import RAR_TEST_ARCHIVE_DEFS

logger = logging.getLogger()


@pytest.fixture(scope="session")
def create_test_repo(tmpdir_factory):
    """Create a test repository with allowed storage paths from test_files."""
    p = tmpdir_factory.mktemp("db")

    # Collect all unique storage paths from test files
    storage_paths = set()

    # Add SFV storage path
    sfv_path = pathlib.Path("./test_files/sfv/")
    if sfv_path.exists():
        storage_paths.add(sfv_path)

    # Add HNF storage path
    hnf_path = pathlib.Path("./test_files/hnf/")
    if hnf_path.exists():
        storage_paths.add(hnf_path)

    # Add RAR storage paths from test cases
    for rar_file_tuple in RAR_TEST_ARCHIVE_DEFS:
        rar_file = rar_file_tuple[0]
        if rar_file.exists():
            storage_paths.add(rar_file.parent)

    # Ensure we have at least one storage path
    if not storage_paths:
        # Fallback to test_files directory if it exists
        test_files_path = pathlib.Path("./test_files/")
        if test_files_path.exists():
            storage_paths.add(test_files_path)

    ha_repo = HashArchiveRepository(pathlib.Path(p / "hoarder.db"), storage_paths)
    return ha_repo


def test_sfv_repositories(create_test_repo):
    for sfv_fn in [
        "files.sfv",
    ]:
        p = pathlib.Path("./test_files/sfv/") / sfv_fn

        print(p.is_file())

        root = p.parent
        path = pathlib.PurePath(p.name)
        saved_sfv_file = SfvArchive.from_path(root, path)
        create_test_repo.save(saved_sfv_file)
        retrieved_sfv_file = create_test_repo.load(
            saved_sfv_file.storage_path, saved_sfv_file.path
        )

        print(saved_sfv_file)
        print(retrieved_sfv_file)
        assert repr(saved_sfv_file) == repr(retrieved_sfv_file)


@pytest.mark.parametrize("rar_file_tuple", RAR_TEST_ARCHIVE_DEFS)
def test_rar_repositories(
    create_test_repo,
    rar_file_tuple: tuple[
        pathlib.Path, str | None, typing.Any, typing.Any, typing.Any, typing.Any
    ],
):
    rar_file = rar_file_tuple[0]
    logger.debug(f"Now processing {rar_file}")
    password = rar_file_tuple[1]
    root = rar_file.parent
    path = pathlib.PurePath(rar_file.name)
    saved_rar_file = RarArchive.from_path(
        root,
        path,
        password=password,
    )
    create_test_repo.save(saved_rar_file)
    retrieved_rar_file = create_test_repo.load(
        saved_rar_file.storage_path, saved_rar_file.path
    )

    assert repr(saved_rar_file) == repr(retrieved_rar_file)


def test_hnf_repositories(create_test_repo):
    for hnf_fn in [
        "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv",
        "[Dummy] Uppercase and Brackets Ep13v2[Puresuhoruda][6519E6CF].mkv",
        "[Foobar] Lowercase and Parens - 11 (x264-AC3)(d74b7612).mkv",
        "[Test] Uppercase and Parens! S02E080 (WEB 1080p x264 10-bit AAC) (5A365C81).mkv",
    ]:
        hnf_path = pathlib.Path("./test_files/hnf/") / hnf_fn
        root = hnf_path.parent
        path = pathlib.PurePath(hnf_path.name)
        saved_hnf_file = HashNameArchive.from_path(root, path)
        create_test_repo.save(saved_hnf_file)
        retrieved_hnf_file = create_test_repo.load(
            saved_hnf_file.storage_path, saved_hnf_file.path
        )

    assert repr(saved_hnf_file) == repr(retrieved_hnf_file)


def test_storage_path_not_allowed_error(tmpdir_factory):
    """Test that ValueError is raised for disallowed storage paths."""
    p = tmpdir_factory.mktemp("db")

    # Create repository with only one allowed storage path
    allowed_path = pathlib.Path("./test_files/sfv/")
    if not allowed_path.exists():
        pytest.skip(f"Test file directory not found: {allowed_path}")

    repo = HashArchiveRepository(
        pathlib.Path(p / "hoarder.db"), [allowed_path]
    )

    # Try to save an archive from a different storage path
    hnf_path = (
        pathlib.Path("./test_files/hnf/")
        / "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv"
    )
    if not hnf_path.exists():
        pytest.skip(f"Test file not found: {hnf_path}")

    storage_path = hnf_path.parent
    path = pathlib.PurePath(hnf_path.name)
    hnf_archive = HashNameArchive.from_path(storage_path, path)

    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        repo.save(hnf_archive)

    assert str(storage_path.resolve()) in str(exc_info.value)


def test_storage_path_not_allowed_on_load(tmpdir_factory):
    """Test that ValueError is raised on load for disallowed storage paths."""
    p = tmpdir_factory.mktemp("db")

    # Create repository with only SFV storage path
    allowed_path = pathlib.Path("./test_files/sfv/")
    if not allowed_path.exists():
        pytest.skip(f"Test file directory not found: {allowed_path}")

    repo = HashArchiveRepository(
        pathlib.Path(p / "hoarder.db"), [allowed_path]
    )

    # Try to load from a disallowed storage path
    hnf_path = (
        pathlib.Path("./test_files/hnf/")
        / "[ABC] 05. Lowercase and Brackets [x265][1080p][8714c76f].mkv"
    )
    if not hnf_path.exists():
        pytest.skip(f"Test file not found: {hnf_path}")

    storage_path = hnf_path.parent
    path = pathlib.PurePath(hnf_path.name)

    # Should raise ValueError before even checking the database
    with pytest.raises(ValueError) as exc_info:
        repo.load(storage_path, path)

    assert str(storage_path.resolve()) in str(exc_info.value)


def test_storage_path_validation_on_init(tmpdir_factory):
    """Test that storage paths are validated and normalized on initialization."""
    p = tmpdir_factory.mktemp("db")

    # Test with non-existent path
    non_existent = pathlib.Path("/nonexistent/path/that/does/not/exist")
    with pytest.raises(FileNotFoundError):
        HashArchiveRepository(pathlib.Path(p / "hoarder.db"), [non_existent])

    # Test with existing path - should normalize (resolve)
    sfv_path = pathlib.Path("./test_files/sfv/")
    if not sfv_path.exists():
        pytest.skip(f"Test file directory not found: {sfv_path}")

    repo = HashArchiveRepository(pathlib.Path(p / "hoarder.db"), [sfv_path])

    # Verify the path was normalized
    assert sfv_path.resolve() in repo._allowed_storage_paths
