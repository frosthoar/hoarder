"""Correlation: matching discovered archives with discovered real files."""

import collections
from pathlib import Path

from ..archives import AbstractRarArchive, FileEntry, HashArchive
from ..downloads import RealFile


def correlate_archives(
    archives: list[HashArchive], real_files: list[RealFile]
) -> list[HashArchive]:
    """Filter archives to those with at least one entry matching a real file.

    Compares absolute paths (archive.anchor.full_path.parent / entry.path vs.
    real_file.full_path) rather than storage-relative ones, so this doesn't
    assume every archive and real file share one storage root.

    A password-protected archive we couldn't open (requires_password=True,
    no files - see AbstractRarArchive.discover()) can never match by
    content, but is kept anyway: dropping it here would undo discover()'s
    whole point of keeping it visible for a later password retry.
    """
    real_paths = {rf.full_path for rf in real_files}
    relevant: list[HashArchive] = []
    for archive in archives:
        if isinstance(archive, AbstractRarArchive) and archive.requires_password:
            relevant.append(archive)
            continue
        archive_dir = archive.anchor.full_path.parent
        archive_paths = {archive_dir / fe.path for fe in archive.files}
        if archive_paths & real_paths:
            relevant.append(archive)
    return relevant


def correlate_files_to_entries(
    real_files: list[RealFile], archives: list[HashArchive]
) -> dict[RealFile, list[FileEntry]]:
    """Match real files to their corresponding FileEntry records."""
    path_to_entries: dict[Path, list[FileEntry]] = collections.defaultdict(list)
    for archive in archives:
        archive_dir = archive.anchor.full_path.parent
        for entry in archive.files:
            path_to_entries[archive_dir / entry.path].append(entry)

    matches: dict[RealFile, list[FileEntry]] = {}
    for rf in real_files:
        if rf.full_path in path_to_entries:
            matches[rf] = path_to_entries[rf.full_path]
    return matches
