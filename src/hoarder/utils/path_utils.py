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


@dataclasses.dataclass(frozen=True, slots=True)
class AnchoredPath:
    """A relative_path anchored to a storage_path.

    Guarantees at construction (and on every replacement) that the combination
    cannot resolve outside storage_path.
    """

    storage_path: pathlib.Path
    relative_path: pathlib.PurePath

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "storage_path", pathlib.Path(self.storage_path).resolve()
        )
        parts = pathlib.PurePath(self.relative_path).parts
        object.__setattr__(self, "relative_path", pathlib.PurePosixPath(*parts))
        resolved = (self.storage_path / self.relative_path).resolve()
        if not resolved.is_relative_to(self.storage_path):
            raise ValueError(
                f"Path '{self.relative_path}' escapes storage root '{self.storage_path}'"
            )

    @property
    def full_path(self) -> pathlib.Path:
        return self.storage_path / self.relative_path

    def with_storage_path(self, storage_path: pathlib.Path | str) -> "AnchoredPath":
        """Return a new, revalidated AnchoredPath with a different storage_path."""
        return dataclasses.replace(self, storage_path=pathlib.Path(storage_path))

    def with_relative_path(
        self, relative_path: pathlib.PurePath | str
    ) -> "AnchoredPath":
        """Return a new, revalidated AnchoredPath with a different relative_path."""
        return dataclasses.replace(self, relative_path=pathlib.PurePath(relative_path))

    @classmethod
    def from_absolute_path(
        cls, storage_path: pathlib.Path | str, absolute_path: pathlib.Path | str
    ) -> "AnchoredPath":
        sp = pathlib.Path(storage_path).resolve()
        ap = pathlib.Path(absolute_path).resolve()
        return cls(sp, ap.relative_to(sp))
