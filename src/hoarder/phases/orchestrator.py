"""Wire discovery and correlation together for a single ScanTarget."""

import dataclasses

from ..archives import FileEntry, HashArchive, HashNameArchive, RarArchive, SfvArchive
from ..downloads import RealFile
from ..passwords import PasswordStore
from .correlation import correlate_archives, correlate_files_to_entries
from .discovery import collect_archive_paths, discover_real_files
from .password_resolution import resolve_passwords
from .scan_target import ScanTarget

ARCHIVE_TYPES: list[type[HashArchive]] = [SfvArchive, RarArchive, HashNameArchive]


@dataclasses.dataclass
class ProcessingResult:
    """Everything discovered and correlated for one ScanTarget."""

    target: ScanTarget
    archives: list[HashArchive]
    real_files: list[RealFile]
    matches: dict[RealFile, list[FileEntry]]


def process_target(
    target: ScanTarget,
    password_store: PasswordStore | None = None,
    title: str | None = None,
) -> ProcessingResult:
    """Discover archives and real files for target, and correlate them.

    If password_store is given, password-protected archives discover()
    couldn't open are retried against passwords known for `title` (default:
    the anchor's own directory name, e.g. the release folder) before
    correlation, so a working password lets the archive correlate normally
    instead of merely being recorded as "needs a password".
    """
    archives: list[HashArchive] = []
    for scope in target.get_archive_search_paths():
        for archive_cls in ARCHIVE_TYPES:
            archives.extend(archive_cls.discover(scope))

    if password_store is not None:
        resolved_title = (
            title if title is not None else target.anchor.relative_path.name
        )
        archives = resolve_passwords(archives, password_store, resolved_title)

    archive_volume_paths = collect_archive_paths(archives)
    real_files = discover_real_files(
        target.get_file_search_paths(), exclude=archive_volume_paths
    )

    relevant_archives = correlate_archives(archives, real_files)
    file_matches = correlate_files_to_entries(real_files, relevant_archives)

    return ProcessingResult(
        target=target,
        archives=relevant_archives,
        real_files=real_files,
        matches=file_matches,
    )
