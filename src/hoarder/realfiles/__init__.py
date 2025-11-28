"""Models and persistence helpers describing real files stored on disk."""

from .contents_hasher import ContentsHasher, CRC32Hasher
from .real_file import RealFile, Verification, VerificationSource
from .real_file_repository import RealFileRepository

__all__ = [
    "CRC32Hasher",
    "ContentsHasher",
    "RealFile",
    "Verification",
    "VerificationSource",
    "RealFileRepository",
]
