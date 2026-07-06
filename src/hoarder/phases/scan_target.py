"""ScanTarget: the input/work item for the discovery pipeline."""

import dataclasses
import pathlib
from pathlib import PurePosixPath

from ..utils.path_utils import AnchoredPath


@dataclasses.dataclass
class DiscoveryConfig:
    """Configuration controlling where a ScanTarget looks for archives."""

    search_parent: bool = True
    additional_paths: list[AnchoredPath] = dataclasses.field(default_factory=list)


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
        if self.config.search_parent and self.anchor.relative_path != PurePosixPath(
            "."
        ):
            paths.append(
                self.anchor.with_relative_path(self.anchor.relative_path.parent)
            )
        paths.extend(self.config.additional_paths)
        return paths

    def get_file_search_paths(self) -> list[AnchoredPath]:
        """Where to look for real files belonging to this target."""
        return [self.anchor]
