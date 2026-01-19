import abc
import dataclasses
import enum
import pathlib


class PathType(enum.IntEnum):
    UNRESOLVABLE = -1
    AMBIVALENT = 0
    POSIX = 1  # not easily distinguishable from V4
    WINDOWS = 2


def determine_path_type(path: str | pathlib.Path) -> PathType:
    has_backslash = "\\" in str(path)
    has_forwardslash = "/" in str(path)

    if has_backslash and has_forwardslash:
        return PathType.UNRESOLVABLE
    elif has_backslash:
        return PathType.WINDOWS
    elif has_forwardslash:
        return PathType.POSIX
    else:
        return PathType.AMBIVALENT


class AnchoredPathMixin(abc.ABC):
    storage_path: pathlib.Path
    path: pathlib.PurePath

    @property
    def full_path(self) -> pathlib.Path:
        """Calculate the full path by combining storage_path and path."""
        return self.storage_path / self.path


@dataclasses.dataclass
class AnchoredPath(AnchoredPathMixin):
    storage_path: pathlib.Path
    path: pathlib.PurePath
