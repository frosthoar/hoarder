"""ScanTarget: the input/work item for the discovery pipeline."""

import dataclasses
import pathlib
from pathlib import PurePath

from ..utils.path_utils import AnchoredPath


@dataclasses.dataclass
class DiscoveryConfig:
    """Configuration controlling where a ScanTarget looks for archives."""

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


@dataclasses.dataclass
class ScanTarget:
    """A single unit (file or directory) to discover archives/real files for."""

    anchor: AnchoredPath
    config: DiscoveryConfig = dataclasses.field(default_factory=DiscoveryConfig)

    @property
    def full_path(self) -> pathlib.Path:
        return self.anchor.full_path

    def get_archive_search_paths(self) -> list[AnchoredPath]:
        """Where to look for archives related to this target."""
        paths = [self.anchor]
        if self.config.search_parent and self.anchor.relative_path != PurePath("."):
            paths.append(
                self.anchor.with_relative_path(self.anchor.relative_path.parent)
            )
        paths.extend(self.config.archive_paths)
        return paths

    def get_file_search_paths(self) -> list[AnchoredPath]:
        """Where to look for real files belonging to this target."""
        return [self.anchor]
