"""Public, backend-agnostic RAR archive class.

Code outside this package should construct and persist RarArchive rather
than referring to a specific backend (Rar7zArchive, RarfileRarArchive)
directly, so the choice of backend can change without touching callers
or previously stored data.
"""

from .rar_archive_rarfile import RarfileRarArchive


class RarArchive(RarfileRarArchive):
    """RAR archive using the currently preferred backend implementation."""
