import hoarder
import tempfile
import pathlib
import logging

logger = logging.getLogger()

def test_repository():

    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".sqlite", delete=False) as f:
            f.close()
            try:
                ha_repo = hoarder.HashArchiveRepository(f.name)

                saved_sfv_file = hoarder.SfvArchive.from_path(pathlib.Path("./test_files/sfv/rhash_output_lowercase.sfv"))
                saved_sfv_file_path = saved_sfv_file.path
                ha_repo.save(saved_sfv_file)
                retrieved_sfv_file = ha_repo.load(saved_sfv_file_path)

                assert repr(saved_sfv_file) == repr(retrieved_sfv_file)

                saved_rar_file = hoarder.RarArchive.from_path(pathlib.Path("./test_files/rar/winrar_rar4_password.rar"), password="password")
                saved_rar_file_path = saved_rar_file.path
                ha_repo.save(saved_rar_file)
                retrieved_rar_file = ha_repo.load(saved_rar_file_path)

                assert repr(saved_rar_file) == repr(retrieved_rar_file)

                saved_hnf_file = hoarder.HashNameArchive.from_path(pathlib.Path("./test_files/hnf/[Foobar] Lowercase and Parens - 11 (x264-AC3)(d74b7612).mkv"))
                saved_hnf_file_path = saved_hnf_file.path
                ha_repo.save(saved_hnf_file)
                retrieved_hnf_file = ha_repo.load(saved_hnf_file_path)

                assert repr(saved_hnf_file) == repr(retrieved_hnf_file)
            finally:
                pathlib.Path(f.name).unlink


