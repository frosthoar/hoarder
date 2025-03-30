import logging
import pathlib
import sys

import hoarder
import compare_files

test_file_path = pathlib.Path(__file__).parent.resolve()
add_path = (test_file_path / ".." / "src").resolve()
sys.path.append(add_path.as_posix())

logger = logging.getLogger("hoarder.test_sfv_file")

compare_files_wo_dir = [
    el for el in compare_files.compare_files if not el.is_dir
]

def test_sfv_files():
    sfv_file_path = (
        test_file_path / ".." / "test_files" / "sfv" / "rhash_output.sfv"
    ).resolve()
    sfv_file = hoarder.SfvFile.from_path(sfv_file_path)
    assert len(sfv_file.files) == 6
    assert sorted(sfv_file.files) == sorted(compare_files_wo_dir)
    assert sfv_file.path == sfv_file_path

    sfv_file_lowercase_path = (
        test_file_path / ".." / "test_files" / "sfv" / "rhash_output_lowercase.sfv"
    ).resolve()

    sfv_file_lowercase = hoarder.SfvFile.from_path(sfv_file_lowercase_path)

    assert len(sfv_file_lowercase.files) == 6
    assert sorted(sfv_file_lowercase.files) == sorted(compare_files_wo_dir)
    assert sfv_file_lowercase.path == sfv_file_lowercase_path
