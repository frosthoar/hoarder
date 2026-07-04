import subprocess

import pytest

from hoarder.archives import Rar7zArchive
from hoarder.utils import SEVENZIP


def _has_7z_rar_support() -> bool:
    try:
        result = subprocess.run([str(SEVENZIP), "i"], capture_output=True, timeout=5)
        return b"Rar5" in result.stdout
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


_RAR7Z_AVAILABLE = _has_7z_rar_support()


@pytest.fixture(autouse=True)
def skip_missing_rar7z(request: pytest.FixtureRequest) -> None:
    if "archive_class" in request.fixturenames:
        cls = request.getfixturevalue("archive_class")
        if cls is Rar7zArchive and not _RAR7Z_AVAILABLE:
            pytest.skip("p7zip-rar not installed or 7z RAR codec unavailable")
