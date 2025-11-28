from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path, PurePath

from .real_file import RealFile


@dataclasses.dataclass(slots=True, eq=True)
class Download:
    """Represents a download that may contain real files."""

    storage_path: Path
    path: PurePath
    first_seen: dt.datetime
    last_seen: dt.datetime
    comment: str | None = None
    processed: bool = False
    real_files: list[RealFile] = dataclasses.field(default_factory=list)

