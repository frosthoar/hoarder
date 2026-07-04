import subprocess
from functools import lru_cache

import pytest


@lru_cache(maxsize=1)
def _has_7z_rar_support() -> bool:
    from hoarder.utils import SEVENZIP

    try:
        result = subprocess.run([str(SEVENZIP), "i"], capture_output=True, timeout=5)
        return b"Rar5" in result.stdout
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(autouse=True)
def skip_missing_rar7z(request: pytest.FixtureRequest) -> None:
    from hoarder.archives import Rar7zArchive

    if "archive_class" in request.fixturenames:
        cls = request.getfixturevalue("archive_class")
        if cls is Rar7zArchive and not _has_7z_rar_support():
            pytest.skip("p7zip-rar not installed or 7z RAR codec unavailable")
