"""Verification: recording where each real file's hash was confirmed from."""

import logging

from ..archives import Algo, HashArchive, HashNameArchive
from ..downloads import RealFile, Verification, VerificationSource

logger = logging.getLogger("hoarder.phases.verification")


def _ensure_hash(real_file: RealFile, algo: Algo) -> bytes:
    """Return real_file's own content hash for algo, computing it if needed."""
    if real_file.hash_value is not None and real_file.algo == algo:
        return real_file.hash_value
    return real_file.calculate_hash(algo=algo)


def verify_real_files(archives: list[HashArchive], real_files: list[RealFile]) -> None:
    """Attach Verification records to each real file, in place.

    For every non-directory FileEntry an archive has that matches a real
    file's absolute path (archive.anchor.full_path.parent / entry.path -
    same join as correlation.py, never compare entry.path directly against
    real_file.full_path), computes that real file's hash with the entry's
    algo and records a Verification: VerificationSource.FILENAME for
    HashNameArchive matches (the "archive" *is* the file itself), ARCHIVE
    otherwise. A real file matched by more than one archive accumulates one
    Verification per match.

    Real files no archive matched fall back to a single untrusted
    VerificationSource.SELF_HASH record of their own computed hash, so
    every non-directory real file ends up with at least one Verification
    (mirrors FileEntry/RealFile being designed for gradual enrichment
    rather than replacement - see their docstrings). Directories are
    skipped entirely; there's nothing meaningful to hash.
    """
    real_files_by_path = {rf.full_path: rf for rf in real_files}

    for archive in archives:
        archive_dir = archive.anchor.full_path.parent
        source_type = (
            VerificationSource.FILENAME
            if isinstance(archive, HashNameArchive)
            else VerificationSource.ARCHIVE
        )
        for entry in archive.files:
            if entry.is_dir or entry.hash_value is None or entry.algo is None:
                continue
            real_file = real_files_by_path.get(archive_dir / entry.path)
            if real_file is None:
                continue
            try:
                _ensure_hash(real_file, entry.algo)
            except NotImplementedError:
                logger.warning(
                    "Cannot verify %s against %s: hashing algo %s is not implemented",
                    real_file.full_path,
                    archive.full_path,
                    entry.algo.name,
                )
                continue
            real_file.verification.append(
                Verification(
                    real_file=real_file,
                    source_type=source_type,
                    source=archive.anchor,
                    hash_value=entry.hash_value,
                    algo=entry.algo,
                )
            )

    for real_file in real_files:
        if real_file.is_dir or real_file.verification:
            continue
        hash_value = _ensure_hash(real_file, Algo.CRC32)
        real_file.verification.append(
            Verification(
                real_file=real_file,
                source_type=VerificationSource.SELF_HASH,
                source=real_file.anchor,
                hash_value=hash_value,
                algo=Algo.CRC32,
            )
        )
