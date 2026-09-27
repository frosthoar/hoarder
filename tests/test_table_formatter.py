"""Tests for the TableFormatter presentation module."""

import pathlib

import pytest
import tests.test_case_file_info
from hoarder.archives import SfvArchive
from hoarder.utils.presentation import PresentationSpec, TableFormatter, pformat, pprint

SFV_TUPLES = [
    (
        pathlib.Path("./test_files/sfv/files.sfv"),
        filter(lambda x: not x.is_dir, tests.test_case_file_info.TEST_FILES),
    )
]


@pytest.mark.parametrize("sfv_data_tuple", SFV_TUPLES)
def test_hash_archive_table_formatter(sfv_data_tuple):
    """Test that TableFormatter correctly formats a hash archive."""
    full_path = sfv_data_tuple[0].resolve()
    root = full_path.parent
    path = pathlib.PurePath(full_path.name)
    sfv_archive = SfvArchive.from_path(root, path)

    formatter = TableFormatter()
    output = formatter.format_presentable(sfv_archive)

    # Verify the output contains expected elements
    assert "SfvArchive" in output
    assert str(sfv_archive.full_path) in output

    # Verify table structure is present
    assert "┏" in output  # Top border
    assert "┗" in output  # Bottom border
    assert "┃" in output  # Vertical borders

    # Verify table headers
    assert "path" in output
    assert "type" in output
    assert "size" in output
    assert "hash" in output
    assert "algo" in output

    # Verify at least one file entry is present in the table
    # (we know the test file has files, so we should see at least one)
    assert len(sfv_archive.files) > 0
    # Check that at least one file path appears in the output
    file_paths_in_output = any(str(file.path) in output for file in sfv_archive.files)
    assert (
        file_paths_in_output
    ), "At least one file path should appear in the formatted output"


def test_truncate_middle_keeps_both_ends():
    """Long values should be elided in the middle, not just cut off at the
    end - the distinguishing part of a long release-name path is often at
    the tail, which a naive tail-truncation would discard entirely."""
    long_name = (
        "Gate.2.E01.Das.Bankett.ist.eroeffnet.German.2016.ANiME.DL.1080p."
        "BluRay.x264-STARS"
    )
    assert len(long_name) > TableFormatter.MAX_COL_WIDTH

    truncated = TableFormatter._truncate_middle(  # pyright: ignore[reportPrivateUsage]
        long_name, TableFormatter.MAX_COL_WIDTH
    )

    assert len(truncated) == TableFormatter.MAX_COL_WIDTH
    assert "..." in truncated
    assert truncated.startswith(long_name[:10])
    assert truncated.endswith(long_name[-10:])
    assert "STARS" in truncated


def test_truncate_middle_leaves_short_values_untouched():
    assert (
        TableFormatter._truncate_middle(  # pyright: ignore[reportPrivateUsage]
            "short", 80
        )
        == "short"
    )


def test_format_table_truncates_long_values_in_the_middle():
    """End-to-end: a long path cell must show both start and end, not just
    the start followed by "..."."""
    long_path = "/mnt/ds423plus/usenet/" + "x" * 40 + "-DISTINCTIVE-SUFFIX"
    spec: PresentationSpec = {
        "scalar": {},
        "collections": {"rows": [{"path": long_path}]},
    }
    output = TableFormatter().format(spec)

    assert "DISTINCTIVE-SUFFIX" in output
    assert "/mnt/ds423plus/usenet/" in output


def test_format_single_collection_has_no_heading():
    spec: PresentationSpec = {
        "scalar": {"type": "Thing"},
        "collections": {"files": [{"path": "a"}]},
    }
    output = TableFormatter().format(spec)

    assert "files:" not in output


def test_format_multiple_collections_are_each_labeled_and_shown():
    spec: PresentationSpec = {
        "scalar": {"type": "Thing"},
        "collections": {
            "archives": [{"path": "archive.rar"}],
            "real_files": [{"path": "movie.mkv"}],
        },
    }
    output = TableFormatter().format(spec)

    assert "archives:" in output
    assert "real_files:" in output
    assert "archive.rar" in output
    assert "movie.mkv" in output
    # The archives table should come before the real_files table.
    assert output.index("archive.rar") < output.index("movie.mkv")


def test_format_honors_spec_merge_first_column_hint():
    """A spec's own merge_first_column hint should be honored - this is what
    lets pformat/pprint work with no configuration, since the object
    producing the spec (e.g. PasswordStore) is the one that knows its first
    column repeats."""
    spec: PresentationSpec = {
        "scalar": {},
        "collections": {"rows": [{"title": "a", "x": 1}, {"title": "a", "x": 2}]},
        "merge_first_column": True,
    }
    output = TableFormatter().format(spec)
    lines = output.splitlines()

    # Merged rows draw no separator between them.
    row_separators = [line for line in lines if line.startswith("┠")]
    assert len(row_separators) == 0

    # The second row's repeated first-column cell is blanked out, not "a".
    data_lines = [line for line in lines if line.startswith("┃")]
    assert len(data_lines) == 3  # header + 2 rows
    second_row_first_cell = data_lines[2].split("│")[0]
    assert "a" not in second_row_first_cell


def test_format_defaults_to_not_merging_when_spec_omits_the_hint():
    spec: PresentationSpec = {
        "scalar": {},
        "collections": {"rows": [{"title": "a", "x": 1}, {"title": "a", "x": 2}]},
    }
    output = TableFormatter().format(spec)
    lines = output.splitlines()
    row_separators = [line for line in lines if line.startswith("┠")]
    assert len(row_separators) == 1


class _FakePresentable:
    def to_presentation(self) -> PresentationSpec:
        return {"scalar": {"type": "Fake"}, "collections": {"rows": [{"a": 1}]}}


def test_pformat_formats_a_presentable_without_any_setup():
    output = pformat(_FakePresentable())
    assert "Fake" in output
    assert "┏" in output


def test_pprint_prints_the_same_output_as_pformat(capsys: pytest.CaptureFixture[str]):
    obj = _FakePresentable()
    pprint(obj)
    captured = capsys.readouterr()
    assert captured.out.rstrip("\n") == pformat(obj)
