import collections.abc
import enum
import re
import typing
from pathlib import Path

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override


class RarScheme(enum.IntEnum):
    AMBIGUOUS = 0
    DOT_RNN = 3  # not easily distinguishable from V4
    PART_N = 5


DOT_RNN_PAT = re.compile(r"""(?x)
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
""")

PART_N_PAT = re.compile(r"""(?x)
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
""")

T = typing.TypeVar("T", bound="RARPath")


def get_match_fallback(match: re.Match, key: str, fallback: str) -> str:
    ret = match.groupdict().get(key)
    if ret is None:
        return fallback
    else:
        return ret


class RARPath(typing.NamedTuple):
    volume_index: int  # type: ignore[assignment]
    path: str
    stem: str
    suffix: str
    scheme: RarScheme

    @classmethod
    def from_path(cls: type[T], path: Path | str) -> T:
        p = Path(path)

        name = p.name
        match_dot_rnn = DOT_RNN_PAT.match(name)
        match_part_n = PART_N_PAT.match(name)

        scheme: RarScheme
        stem: str
        suffix: str
        volume_index: int

        if match_dot_rnn is None and match_part_n is None:
            raise ValueError(f'"{path}" does not match the scheme-3 pattern')
        elif match_dot_rnn is not None and match_part_n is None:
            scheme = RarScheme.DOT_RNN
            stem = match_dot_rnn["stem"]
            suffix = match_dot_rnn["suffix"]
            volume_index = int(get_match_fallback(match_dot_rnn, "volume_index", "-1"))
        elif match_dot_rnn is None and match_part_n is not None:
            scheme = RarScheme.PART_N
            stem = match_part_n["stem"]
            suffix = match_part_n["suffix"]
            volume_index = int(get_match_fallback(match_part_n, "volume_index", "-1"))
        elif match_dot_rnn is not None and match_part_n is not None:
            stem = match_part_n["stem"]
            suffix = match_part_n["suffix"]
            volume_index = int(get_match_fallback(match_part_n, "volume_index", "-1"))
            scheme = RarScheme.AMBIGUOUS

        else:
            raise RuntimeError()

        return cls(
            volume_index=volume_index,
            path=str(p),
            stem=stem,
            suffix=suffix,
            scheme=scheme,
        )

    @override
    def __str__(self) -> str:
        return self.path


def parse_rar_list(
    paths: collections.abc.Sequence[str | Path],
):  # -> //tuple[RarScheme, list[RARPath]]:
    if len(paths) == 0:
        # Since there is no non-indexed .rar, this must be interpreted as an "empty PART_N"
        return RarScheme.PART_N, []

    parsed = [RARPath.from_path(p) for p in paths]

    stem = parsed[0].stem
    scheme: RarScheme = parsed[0].scheme

    if scheme == RarScheme.AMBIGUOUS and len(parsed) > 1:
        scheme = RarScheme.PART_N

    print("+++", parsed, scheme)

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
        print("actual", actual)
        print("expected", expected)
        print("paths", paths)
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
