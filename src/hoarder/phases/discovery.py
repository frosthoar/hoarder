"""Real file discovery and archive-path collection."""

from pathlib import Path

from ..archives import HashArchive
from ..downloads import RealFile
from ..utils.path_utils import AnchoredPath


def discover_real_files(
    scopes: list[AnchoredPath], exclude: set[Path] | None = None
) -> list[RealFile]:
    """Scan for real files within scopes, excluding known archive paths."""
    exclude = exclude or set()
    results: list[RealFile] = []
    for scope in scopes:
        search_path = scope.full_path
        if search_path.is_file():
            if search_path not in exclude:
                results.append(
                    RealFile.from_path(scope.storage_path, scope.relative_path)
                )
        else:
            for p in search_path.rglob("*"):
                if p.is_file() and p not in exclude:
                    relative = p.relative_to(scope.storage_path)
                    results.append(RealFile.from_path(scope.storage_path, relative))
    return results


def collect_archive_paths(archives: list[HashArchive]) -> set[Path]:
    """All paths on disk occupied by the given archives.

    Includes every volume of a multi-volume archive, not just its main file.
    Used to exclude archive volumes from being treated as real files.
    """
    paths: set[Path] = set()
    for archive in archives:
        paths.update(archive.get_occupied_paths())
    return paths
