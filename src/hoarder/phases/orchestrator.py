"""Wire discovery and correlation together for a single ScanTarget."""

import dataclasses
import logging

from ..archives import FileEntry, HashArchive, HashNameArchive, RarArchive, SfvArchive
from ..downloads import RealFile
from ..passwords import PasswordStore
from ..utils import PresentationSpec, ScalarValue
from .correlation import correlate_archives, correlate_files_to_entries
from .discovery import collect_archive_paths, discover_real_files
from .password_resolution import resolve_passwords
from .scan_target import ScanTarget

logger = logging.getLogger("hoarder.phases.orchestrator")

ARCHIVE_TYPES: list[type[HashArchive]] = [SfvArchive, RarArchive, HashNameArchive]


@dataclasses.dataclass
class ProcessingResult:
    """Everything discovered and correlated for one ScanTarget."""

    target: ScanTarget
    archives: list[HashArchive]
    real_files: list[RealFile]
    matches: dict[RealFile, list[FileEntry]]

    def to_presentation(self) -> PresentationSpec:
        """Convert this result to a presentation specification.

        Returns:
            A PresentationSpec with target/archive/match counts as scalars,
            an "archives" collection summarizing each discovered archive,
            and a "real_files" collection with each real file's correlation
            status and which archive entries it matched.
        """
        scalar: dict[str, ScalarValue] = {
            "type": "ProcessingResult",
            "path": str(self.target.full_path),
            "archives": len(self.archives),
            "real_files": len(self.real_files),
            "matched_files": sum(1 for f in self.real_files if self.matches.get(f)),
        }

        archive_rows: list[dict[str, ScalarValue]] = []
        for archive in sorted(self.archives, key=lambda a: str(a.full_path)):
            row: dict[str, ScalarValue] = {
                "path": str(archive.full_path),
                "type": type(archive).__name__,
                "files": len(archive),
                "requires_password": getattr(archive, "requires_password", False),
            }
            archive_rows.append(row)

        real_file_rows: list[dict[str, ScalarValue]] = []
        for real_file in sorted(self.real_files, key=lambda f: str(f.full_path)):
            entries = self.matches.get(real_file, [])
            row = {
                "path": str(real_file.full_path),
                "size": real_file.size,
                "matched": bool(entries),
                "matched_entries": ", ".join(str(e.path) for e in entries) or None,
            }
            real_file_rows.append(row)

        return PresentationSpec(
            scalar=scalar,
            collections={"archives": archive_rows, "real_files": real_file_rows},
        )


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
            found = archive_cls.discover(scope)
            logger.debug(
                "%s.discover(%s) found %d archive(s)",
                archive_cls.__name__,
                scope.full_path,
                len(found),
            )
            archives.extend(found)
    logger.debug(
        "Discovered %d archive(s) total for target %s", len(archives), target.full_path
    )

    if password_store is not None:
        resolved_title = (
            title if title is not None else target.anchor.relative_path.name
        )
        logger.debug(
            "Resolving passwords for target %s using title %r",
            target.full_path,
            resolved_title,
        )
        archives = resolve_passwords(archives, password_store, resolved_title)
    else:
        logger.debug(
            "No password_store given for target %s; skipping password resolution",
            target.full_path,
        )

    archive_volume_paths = collect_archive_paths(archives)
    real_files = discover_real_files(
        target.get_file_search_paths(), exclude=archive_volume_paths
    )
    logger.debug(
        "Discovered %d real file(s) for target %s (excluding %d archive volume path(s))",
        len(real_files),
        target.full_path,
        len(archive_volume_paths),
    )

    relevant_archives = correlate_archives(archives, real_files)
    file_matches = correlate_files_to_entries(real_files, relevant_archives)
    logger.debug(
        "Correlated %d relevant archive(s) and %d file match(es) for target %s",
        len(relevant_archives),
        len(file_matches),
        target.full_path,
    )

    return ProcessingResult(
        target=target,
        archives=relevant_archives,
        real_files=real_files,
        matches=file_matches,
    )
