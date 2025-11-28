"""Models and persistence helpers describing real files stored on disk."""

from .contents_hasher import ContentsHasher, CRC32Hasher
from .download import Download
from .download_repository import DownloadRepository
from .real_file import RealFile, Verification, VerificationSource
from .real_file_repository import RealFileRepository

__all__ = [
    "CRC32Hasher",
    "ContentsHasher",
    "Download",
    "DownloadRepository",
    "RealFile",
    "Verification",
    "VerificationSource",
    "RealFileRepository",
]
