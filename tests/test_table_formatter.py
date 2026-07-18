"""Tests for the TableFormatter presentation module."""

import pathlib

import pytest
import tests.test_case_file_info
from hoarder.archives import SfvArchive
from hoarder.utils.presentation import PresentationSpec, TableFormatter

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
    assert TableFormatter._truncate_middle(  # pyright: ignore[reportPrivateUsage]
        "short", 80
    ) == "short"


def test_format_table_truncates_long_values_in_the_middle():
    """End-to-end: a long path cell must show both start and end, not just
    the start followed by "..."."""
    long_path = "/mnt/ds423plus/usenet/" + "x" * 40 + "-DISTINCTIVE-SUFFIX"
    spec: PresentationSpec = {
        "scalar": {},
        "collection": [{"path": long_path}],
    }
    output = TableFormatter().format(spec)

    assert "DISTINCTIVE-SUFFIX" in output
    assert "/mnt/ds423plus/usenet/" in output
