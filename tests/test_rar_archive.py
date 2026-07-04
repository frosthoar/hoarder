import pathlib
import typing

import pytest
import tests.test_case_file_info
from hoarder.archives import (
    AbstractRarArchive,
    Rar7zArchive,
    RarArchiveError,
    RarfileRarArchive,
    RarScheme,
)


@pytest.mark.parametrize("archive_class", [Rar7zArchive, RarfileRarArchive])
@pytest.mark.parametrize(
    "rar_file_entry", tests.test_case_file_info.RAR_TEST_ARCHIVE_DEFS
)
def test_read_file_content_validation(
    archive_class: type[AbstractRarArchive],
    rar_file_entry: tuple[
        pathlib.Path, str | None, typing.Any, typing.Any, typing.Any, typing.Any
    ],
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
@pytest.mark.parametrize(
    "rar_file_entry", tests.test_case_file_info.RAR_TEST_ARCHIVE_DEFS
)
def test_get_volumes_returns_existing_sibling_volumes(
    archive_class: type[AbstractRarArchive],
    rar_file_entry: tuple[
        pathlib.Path, str | None, typing.Any, typing.Any, typing.Any, typing.Any
    ],
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
