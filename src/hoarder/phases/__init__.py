"""Discovery and correlation phase.

Turns a ScanTarget into correlated archives, real files, and file matches.
"""

from . import correlator, discovery, orchestrator, scan_target
from .correlator import correlate_archives, correlate_files_to_entries
from .discovery import collect_archive_paths, discover_real_files
from .orchestrator import ARCHIVE_TYPES, ProcessingResult, process_target
from .scan_target import DiscoveryConfig, ScanTarget

__all__ = [
    "correlator",
    "discovery",
    "orchestrator",
    "scan_target",
    "correlate_archives",
    "correlate_files_to_entries",
    "collect_archive_paths",
    "discover_real_files",
    "ARCHIVE_TYPES",
    "ProcessingResult",
    "process_target",
    "DiscoveryConfig",
    "ScanTarget",
]
