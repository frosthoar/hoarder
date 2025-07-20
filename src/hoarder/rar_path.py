import collections.abc
import enum
import re
import typing
from pathlib import Path

from typing_extensions import override

try:
    from typing import override # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

class RarScheme(enum.IntEnum):
    AMBIGUOUS = 0
    DOT_RNN = 3  # not easily distinguishable from V4
    PART_N = 5


DOT_RNN_PAT = re.compile(
    r"""(?x)
    ^       # start
    (?P<stem>
        .+  # require a stem of at least one character
    )
    \.      # suffix separator dot
    (?P<suffix>
        rar |  # first literal 'rar' suffix
        r(?P<volume_index>
            \d\d  # two-digit volume index
        )
    )
    $  # end
"""
)

PART_N_PAT = re.compile(
    r"""(?x)
    ^       # start
    (?P<stem>
        .+  # require a stem of at least one character
    )
    \.part   # beginning of first suffix component
    (?P<volume_index>
        \d+  # at least one digit
    )
    \.       # beginning of last suffix component
    (?P<suffix>
        rar  # last suffix component
    )
    $        # end
"""
)

T = typing.TypeVar("T", bound="RARPath")


class RARPath(typing.NamedTuple):
    volume_index: int  # type: ignore[assignment]
    path: str
    stem: str
    suffix: str

    @classmethod
    def from_match(cls: type[T], match: re.Match[str] | None) -> T:
        if match is None:
            raise ValueError("match is None")
        return cls(
            volume_index=-1
            if match["volume_index"] is None
            else int(match["volume_index"]),
            path=match.string,
            stem=match["stem"],
            suffix=match["suffix"],
        )

    @override
    def __str__(self) -> str:
        return self.path


def parse_rar_list(
    paths: collections.abc.Sequence[str | Path],
) -> tuple[RarScheme, list[RARPath]]:
    if len(paths) == 0:
        # Since there is no non-indexed .rar, this must be interpreted as an "empty PART_N"
        return RarScheme.PART_N, []

    matches = [PART_N_PAT.match(str(p)) for p in paths]

    if any(m is None for m in matches):
        matches = [DOT_RNN_PAT.match(str(p)) for p in paths]
        scheme = RarScheme.DOT_RNN

        for path, match in zip(paths, matches):
            if match is None:
                raise ValueError(f'"{path}" does not match the scheme-3 pattern')
    elif len(paths) > 1:
        scheme = RarScheme.PART_N
    else:
        scheme = RarScheme.AMBIGUOUS

    parsed = [RARPath.from_match(match) for match in matches]

    stem = parsed[0].stem
    for rp in parsed[1:]:
        if getattr(rp, "stem", None) != stem:
            raise ValueError(f"{rp} has an inconsistent stem")

    actual = {match.volume_index for match in parsed}

    match scheme:
        case RarScheme.DOT_RNN:
            base = -1
        case RarScheme.PART_N:
            base = 1
        case RarScheme.AMBIGUOUS:
            # It's only possible for this to be a valid PART_N if the only volume index is 1
            if actual == {1}:
                return scheme, parsed
            scheme = RarScheme.DOT_RNN
            base = -1

            # This started as an ambiguous case where the volume index might have been part of a PART_N suffix.
            # Since we've ruled that out, the actual volume index set is reinterpreted as the base only (-1).
            actual = {-1}

    if scheme == RarScheme.DOT_RNN:
        n_unnumbered = sum(1 for match in parsed if match.suffix == "rar")
        if n_unnumbered != 1:
            raise ValueError(
                f"{n_unnumbered} paths have a non-indexed suffix; must be exactly one"
            )

    expected = set(range(base, base + len(paths)))
    spurious = actual - expected
    if spurious:
        raise ValueError(
            "The following indices are unexpected: "
            + ", ".join(str(i) for i in spurious)
        )
    missing = expected - actual
    if missing:
        raise ValueError(
            "The following indices are missing: " + ", ".join(str(i) for i in missing)
        )

    return scheme, parsed


def rar_sort(rar_paths: typing.Sequence[str | Path]) -> tuple[RarScheme, list[str]]:
    scheme, parsed = parse_rar_list(rar_paths)
    return scheme, [rar_path.path for rar_path in sorted(parsed)]


def find_rar_files(
    directory: Path | str, seek_stem: str | None = None
) -> dict[str, tuple[RarScheme, list[Path]]]:
    directory = Path(directory)
    rar_dict: dict[str, list[Path]] = {}
    for path in directory.iterdir():
        if match := PART_N_PAT.match(str(path.name)):
            stem = str(Path(match["stem"]))
            if seek_stem and stem != seek_stem:
                continue
            if rar_dict.get(stem):
                rar_dict[stem].append(path)
            else:
                rar_dict[stem] = [path]
        elif match := DOT_RNN_PAT.match(str(path.name)):
            if seek_stem and seek_stem != match["stem"]:
                continue
            stem = str(Path(match["stem"]))
            if rar_dict.get(stem):
                rar_dict[stem].append(path)
            else:
                rar_dict[stem] = [path]
    ret_dict = {}
    for k, v in rar_dict.items():
        scheme, rar_volumes = rar_sort(v)
        ret_dict[k] = (scheme, [Path(p) for p in rar_volumes])
    return ret_dict
