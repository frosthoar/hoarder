"""Tests for the TableFormatter presentation module."""

import pathlib

import pytest
import tests.test_case_file_info
from hoarder.archives import SfvArchive
from hoarder.utils.presentation import TableFormatter

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
    file_paths_in_output = any(
        str(file.path) in output for file in sfv_archive.files
    )
    assert file_paths_in_output, "At least one file path should appear in the formatted output"

