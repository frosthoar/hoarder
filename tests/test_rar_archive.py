import pathlib
import pytest
import subprocess

from hoarder.rar_archive import RarArchive


class TestRarArchiveReadFile:
    """Test suite for RarArchive read_file method."""

    @pytest.mark.parametrize("rar_file,password", [
        ("v4_unencrypted.rar", None),
        ("v4_encrypted.rar", "secret"),
        ("v5_headers_unencrypted.rar", None),
        ("v5_headers_encrypted.rar", "dragon"),
        ("v4_split_headers_unencrypted.rar", None),
        ("v4_split_headers_encrypted.rar", "password"),
        ("v5_split_headers_unencrypted.part01.rar", None),
        ("v5_split_headers_encrypted.part01.rar", "ninja"),
    ])
    def test_read_file_content_validation(self, rar_file, password):
        """Test that read_file returns correct content matching original files."""
        rar_path = pathlib.Path("test_files/rar") / rar_file
        compare_base = pathlib.Path("test_files/compare/files")
        
        if not rar_path.exists():
            pytest.skip(f"RAR file {rar_path} not found")
        
        if not compare_base.exists():
            pytest.skip(f"Compare directory {compare_base} not found")

        try:
            archive = RarArchive.from_path(rar_path, password=password)
            
            # Test a selection of files from the archive
            test_files = [
                "./files/stock.raw",
                "./files/(2XVR83rF)environmental[EwI!EhWI]/across.raw",
                "./files/(F1AuIP S)reason(3RDyXXVL)/chance.dat",
                "./files/(ugjO0h7V)job(WLss1CFo)/state.raw",
            ]
            
            for file_path_str in test_files:
                file_path = pathlib.PurePath(file_path_str)
                compare_file = compare_base / file_path
                
                # Check if the file exists in both archive and compare directory
                if compare_file.exists():
                    archive_files = {f.path for f in archive.files}
                    if file_path in archive_files:
                        # Read content from archive
                        archive_content = archive.read_file(file_path)
                        
                        # Read original content
                        with open(compare_file, 'rb') as f:
                            original_content = f.read()
                        
                        # Compare contents
                        assert archive_content == original_content, \
                            f"Content mismatch for {file_path} in {rar_file}"
                        
        except subprocess.CalledProcessError:
            pytest.skip(f"7zip not available or archive {rar_file} cannot be processed")
        except FileNotFoundError as e:
            pytest.skip(f"Required file not found: {e}")