import pathlib

import pytest
import tests.test_case_file_info
from hoarder.archives import (
    AbstractRarArchive,
    FileEntry,
    Rar7zArchive,
    RarArchiveError,
    RarfileRarArchive,
    RarPasswordError,
    RarScheme,
)
from hoarder.utils import AnchoredPath

RarFileEntry = tuple[pathlib.Path, str | None, int, int, RarScheme, list[FileEntry]]


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
@pytest.mark.parametrize(
    "rar_file_entry", tests.test_case_file_info.RAR_TEST_ARCHIVE_DEFS
)
def test_read_file_content_validation(
    archive_class: type[AbstractRarArchive],
    rar_file_entry: RarFileEntry,
):
    rar_path = rar_file_entry[0]
    password = rar_file_entry[1]
    compare_base = pathlib.Path("test_files/compare")

    if not rar_path.exists():
        pytest.skip(f"RAR file {rar_path} not found")
    if not compare_base.exists():
        pytest.skip(f"Compare directory {compare_base} not found")

    try:
        root = rar_path.parent
        path = pathlib.PurePath(rar_path.name)
        archive = archive_class.from_path(root, path, password=password)

        test_files = [
            "files/stock.raw",
            "files/(2XVR83rF)environmental[EwI!EhWI]/across.raw",
            "files/(F1AuIP S)reason(3RDyXXVL)/chance.dat",
            "files/(ugjO0h7V)job(WLss1CFo)/state.raw",
        ]

        archive_paths = {f.path for f in archive.files}
        for file_path_str in test_files:
            file_path = pathlib.PurePath(file_path_str)
            compare_file = compare_base / file_path
            assert compare_file.exists(), f"Compare fixture missing: {compare_file}"
            assert file_path in archive_paths, f"{file_path} not found in {rar_path}"
            archive_content = archive.read_file(file_path)
            with open(compare_file, "rb") as f:
                original_content = f.read()
            assert (
                archive_content == original_content
            ), f"Content mismatch for {file_path} in {rar_path}"

    except RarArchiveError as e:
        pytest.skip(f"{archive_class.__name__} cannot process {rar_path}: {e}")
    except FileNotFoundError as e:
        pytest.skip(f"Required file not found: {e}")


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
def test_part_n_padding_must_represent_n_volumes(
    archive_class: type[AbstractRarArchive],
) -> None:
    with pytest.raises(ValueError, match="part_n_padding=2 cannot represent"):
        archive_class(
            pathlib.Path("/tmp"),
            pathlib.PurePath("archive.part01.rar"),
            scheme=RarScheme.PART_N,
            n_volumes=300,
            part_n_padding=2,
        )


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
def test_part_n_padding_matching_n_volumes_is_allowed(
    archive_class: type[AbstractRarArchive],
) -> None:
    archive_class(
        pathlib.Path("/tmp"),
        pathlib.PurePath("archive.part001.rar"),
        scheme=RarScheme.PART_N,
        n_volumes=300,
        part_n_padding=3,
    )


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
def test_get_volumes_raises_on_malformed_part_n_stem(
    archive_class: type[AbstractRarArchive],
) -> None:
    """scheme=PART_N requires the relative_path to actually look like a
    PART_N volume name; a mismatched name must raise rather than silently
    deriving a wrong stem."""
    archive = archive_class(
        pathlib.Path("/tmp"),
        pathlib.PurePath("archive.rar"),
        scheme=RarScheme.PART_N,
        n_volumes=2,
        part_n_padding=2,
    )

    with pytest.raises(ValueError, match="does not match the PART_N naming pattern"):
        archive.get_volumes()


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
@pytest.mark.parametrize(
    "rar_file_entry", tests.test_case_file_info.RAR_TEST_ARCHIVE_DEFS
)
def test_get_volumes_returns_existing_sibling_volumes(
    archive_class: type[AbstractRarArchive],
    rar_file_entry: RarFileEntry,
):
    rar_path = rar_file_entry[0]
    password = rar_file_entry[1]
    expected_n_volumes = rar_file_entry[3]

    if not rar_path.exists():
        pytest.skip(f"RAR file {rar_path} not found")

    try:
        root = rar_path.parent
        path = pathlib.PurePath(rar_path.name)
        archive = archive_class.from_path(root, path, password=password)

        volumes = archive.get_volumes()

        assert len(volumes) == expected_n_volumes
        for volume in volumes:
            assert volume.exists(), f"Volume {volume} does not exist"
        assert volumes[0] == archive.full_path
    except RarArchiveError as e:
        pytest.skip(f"{archive_class.__name__} cannot process {rar_path}: {e}")
    except FileNotFoundError as e:
        pytest.skip(f"Required file not found: {e}")


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
def test_rar_discover_finds_archives_in_directory(
    archive_class: type[AbstractRarArchive],
) -> None:
    scope = AnchoredPath(pathlib.Path("test_files/rar"), pathlib.PurePath("."))
    found = archive_class.discover(scope)
    assert len(found) > 0
    for archive in found:
        assert isinstance(archive, archive_class)


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
def test_rar_discover_returns_empty_when_no_match(
    archive_class: type[AbstractRarArchive],
) -> None:
    scope = AnchoredPath(pathlib.Path("test_files/sfv"), pathlib.PurePath("."))
    assert archive_class.discover(scope) == []


PROTECTED_RAR_DEFS = [
    entry for entry in tests.test_case_file_info.RAR_TEST_ARCHIVE_DEFS if entry[1]
]


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
@pytest.mark.parametrize("rar_file_entry", PROTECTED_RAR_DEFS)
def test_from_path_raises_password_error_with_no_password(
    archive_class: type[AbstractRarArchive],
    rar_file_entry: RarFileEntry,
) -> None:
    """A password-protected archive opened with no password must raise,
    not silently come back with an empty file list."""
    rar_path = rar_file_entry[0]
    if not rar_path.exists():
        pytest.skip(f"RAR file {rar_path} not found")

    with pytest.raises(RarPasswordError):
        archive_class.from_path(rar_path.parent, pathlib.PurePath(rar_path.name))


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
@pytest.mark.parametrize("rar_file_entry", PROTECTED_RAR_DEFS)
def test_from_path_raises_password_error_with_wrong_password(
    archive_class: type[AbstractRarArchive],
    rar_file_entry: RarFileEntry,
) -> None:
    rar_path = rar_file_entry[0]
    if not rar_path.exists():
        pytest.skip(f"RAR file {rar_path} not found")

    with pytest.raises(RarPasswordError):
        archive_class.from_path(
            rar_path.parent,
            pathlib.PurePath(rar_path.name),
            password="definitely-the-wrong-password",
        )


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
@pytest.mark.parametrize(
    "rar_file_entry", tests.test_case_file_info.RAR_TEST_ARCHIVE_DEFS
)
def test_from_path_sets_requires_password(
    archive_class: type[AbstractRarArchive],
    rar_file_entry: RarFileEntry,
) -> None:
    """requires_password reflects whether the archive is encrypted at all,
    independent of whether the password we supplied was correct."""
    rar_path = rar_file_entry[0]
    password = rar_file_entry[1]
    if not rar_path.exists():
        pytest.skip(f"RAR file {rar_path} not found")

    try:
        archive = archive_class.from_path(
            rar_path.parent, pathlib.PurePath(rar_path.name), password=password
        )
    except RarArchiveError as e:
        pytest.skip(f"{archive_class.__name__} cannot process {rar_path}: {e}")

    assert archive.requires_password == (password is not None)


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
def test_discover_records_password_protected_archives_without_contents(
    archive_class: type[AbstractRarArchive],
) -> None:
    """Bulk discovery over a directory doesn't know passwords upfront.
    Archives it can't open because they're encrypted must still show up
    in the results (marked requires_password=True, empty files) rather
    than silently vanishing, so they can be found later and re-tried."""
    scope = AnchoredPath(pathlib.Path("test_files/rar"), pathlib.PurePath("."))
    found = archive_class.discover(scope)

    protected_stems = {entry[0].name for entry in PROTECTED_RAR_DEFS}
    stubs = [a for a in found if a.anchor.relative_path.name in protected_stems]

    assert len(stubs) == len(protected_stems)
    for stub in stubs:
        assert stub.requires_password is True
        assert stub.password is None
        assert len(stub.files) == 0
        assert stub.n_volumes is not None


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
def test_try_candidate_passwords_finds_the_correct_one(
    archive_class: type[AbstractRarArchive],
) -> None:
    """Simulates the intended usage from the password-store integration:
    keep trying candidate passwords, using RarPasswordError specifically
    to know "wrong guess, try the next one" rather than "archive broken,
    give up"."""
    rar_path = pathlib.Path("test_files/rar/v4_encrypted.rar")
    if not rar_path.exists():
        pytest.skip(f"RAR file {rar_path} not found")

    candidates = ["wrong-1", "wrong-2", "secret", "wrong-3"]
    root = rar_path.parent
    path = pathlib.PurePath(rar_path.name)

    archive = None
    tried = []
    for candidate in candidates:
        tried.append(candidate)
        try:
            archive = archive_class.from_path(root, path, password=candidate)
            break
        except RarPasswordError:
            continue

    assert archive is not None, "None of the candidate passwords worked"
    assert tried == ["wrong-1", "wrong-2", "secret"]
    assert archive.password == "secret"
    assert len(archive.files) > 0
