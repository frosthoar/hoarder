"""ScanTarget: the input/work item for the discovery pipeline."""

import dataclasses
import logging
import pathlib
from pathlib import PurePath

from ..utils.path_utils import AnchoredPath

logger = logging.getLogger("hoarder.phases.scan_target")


@dataclasses.dataclass
class ScanTarget:
    """A single unit (file or directory) to discover archives/real files for."""

    anchor: AnchoredPath
    # Off by default: a ScanTarget's anchor is normally a directory holding
    # one release/download, and its parent is one level ABOVE that (e.g. the
    # whole downloads folder) - not a useful place to look for archives, and
    # searching it risks pulling in unrelated archives. Turn this on only
    # when the anchor is nested one level deeper than its archive, e.g. a
    # per-disc "CD1/", "CD2/" subfolder sharing one .sfv in the parent.
    search_parent: bool = False
    # Extra locations to search for archives, independent of the anchor's
    # own storage root - each AnchoredPath carries its own storage_path, so
    # these need not live anywhere near (or even share a root with) the
    # file(s) they end up correlated with.
    archive_paths: list[AnchoredPath] = dataclasses.field(default_factory=list)

    @property
    def full_path(self) -> pathlib.Path:
        return self.anchor.full_path

    def get_archive_search_paths(self) -> list[AnchoredPath]:
        """Where to look for archives related to this target.

        Each archive type's own discover() only looks at one directory (see
        HashArchive.discover), so a directory anchor is expanded into itself
        plus every subdirectory beneath it - matching the recursive walk
        get_file_search_paths()/discover_real_files() already does for real
        files. Without this, an archive living in a release's subdirectory
        (e.g. "subdir/checks.sfv" next to "subdir/payload.bin") would never
        be found, even though its payload is.
        """
        if self.anchor.full_path.is_dir():
            directories = [
                self.anchor.full_path,
                *(p for p in self.anchor.full_path.rglob("*") if p.is_dir()),
            ]
            paths = [
                self.anchor.with_relative_path(
                    directory.relative_to(self.anchor.storage_path)
                )
                for directory in directories
            ]
        else:
            paths = [self.anchor]
        if self.search_parent and self.anchor.relative_path != PurePath("."):
            paths.append(
                self.anchor.with_relative_path(self.anchor.relative_path.parent)
            )
        paths.extend(self.archive_paths)
        logger.debug(
            "Archive search paths for %s: %s",
            self.anchor.full_path,
            [p.full_path for p in paths],
        )
        return paths

    def get_file_search_paths(self) -> list[AnchoredPath]:
        """Where to look for real files belonging to this target."""
        logger.debug(
            "File search path for %s: %s", self.anchor.full_path, self.anchor.full_path
        )
        return [self.anchor]
