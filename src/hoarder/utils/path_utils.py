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
    relative_path: pathlib.PurePath

    @property
    def full_path(self) -> pathlib.Path:
        return self.storage_path / self.relative_path

    def _validate(self) -> None:
        resolved = self.full_path.resolve()
        if not resolved.is_relative_to(self.storage_path.resolve()):
            raise ValueError(
                f"Path '{self.relative_path}' escapes storage root '{self.storage_path}'"
            )
        if not resolved.exists():
            raise FileExistsError(f"Path '{self.relative_path}' does not exist")


@dataclasses.dataclass
class AnchoredPath(AnchoredPathMixin):
    storage_path: pathlib.Path = dataclasses.field(init=False)
    relative_path: pathlib.PurePath = dataclasses.field(init=False)

    _storage_path_in: dataclasses.InitVar[str | pathlib.Path]
    _relative_path_in: dataclasses.InitVar[str | pathlib.PurePath]

    def __post_init__(
        self,
        _storage_path_in: str | pathlib.Path,
        _relative_path_in: str | pathlib.PurePath,
    ) -> None:
        self.storage_path = pathlib.Path(_storage_path_in)
        self.relative_path = pathlib.PurePath(_relative_path_in)
        self._validate()

    @classmethod
    def from_absolute_path(
        cls: type, storage_path: pathlib.Path | str, absolute_path: pathlib.Path | str
    ) -> "AnchoredPath":
        ap: pathlib.Path = pathlib.Path(absolute_path).resolve()
        sp: pathlib.Path = pathlib.Path(storage_path).resolve()

        # This will raise ValueError if ap is not a subpath of sp
        # (i.e., if ap is not contained within sp in the directory tree)
        relative_path: pathlib.PurePath = pathlib.PurePath(ap.relative_to(sp))

        return cls(sp, relative_path)
