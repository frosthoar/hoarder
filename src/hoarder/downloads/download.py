from __future__ import annotations

import dataclasses
import datetime as dt

from ..archives import HashArchive
from .real_file import RealFile


@dataclasses.dataclass(slots=True, eq=True)
class Download:
    """Represents a download that may contain real files and hash archives."""

    title: str
    first_seen: dt.datetime
    last_seen: dt.datetime
    comment: str | None = None
    processed: bool = False
    real_files: list[RealFile] = dataclasses.field(default_factory=list)
    hash_archives: list[HashArchive] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate that title is not empty."""
        if not self.title:
            raise ValueError("Download title cannot be empty")
