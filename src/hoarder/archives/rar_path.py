"""Utilities for parsing and handling RAR archive volume paths."""

import collections.abc
import dataclasses
import enum
import re
import typing
from pathlib import Path

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override


class RarScheme(enum.IntEnum):
    """RAR volume naming scheme (e.g., .r00/.r01 vs .part1.rar/.part2.rar)."""

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

T = typing.TypeVar("T", bound="RarPath")


@dataclasses.dataclass(frozen=True, order=True)
class RarPath():
    """Parsed RAR volume path with extracted scheme and volume index."""

    volume_index: int  # type: ignore[assignment]
    path: str
    stem: str
    suffix: str
    scheme: RarScheme

    @classmethod
    def from_path(cls: type[T], path: Path | str) -> T:
        """Parse a RAR volume path and extract its components."""
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
            volume_index = int(match_dot_rnn["volume_index"] or "-1")
        elif match_dot_rnn is None and match_part_n is not None:
            scheme = RarScheme.PART_N
            stem = match_part_n["stem"]
            suffix = match_part_n["suffix"]
            volume_index = int(match_part_n["volume_index"] or "-1")
        elif match_dot_rnn is not None and match_part_n is not None:
            # choosing match_dot_rnn or match_part_n does not change the extracted matches
            stem = match_part_n["stem"]
            suffix = match_part_n["suffix"]
            volume_index = int(match_part_n["volume_index"] or "-1")
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


@dataclasses.dataclass
class RarArchiveSet:
    stem: str
    rar_scheme: RarScheme
    volumes: list[RarPath]

    @property
    def sorted_volume_paths(self) -> list[str]:
        """Return volume paths sorted by volume index."""
        return [rp.path for rp in sorted(self.volumes)]

    @classmethod
    def parse_rar_list(
        cls,
        paths: collections.abc.Sequence[str | Path],
    ) -> typing.Self:
        """Parse and validate a list of RAR volume paths."""
        if len(paths) == 0:
            # Since there is no non-indexed .rar, this must be interpreted as an "empty PART_N"
            return cls(stem="", rar_scheme=RarScheme.PART_N, volumes=[])

        parsed = [RarPath.from_path(p) for p in paths]

        stem = parsed[0].stem
        scheme: RarScheme = parsed[0].scheme

        if scheme == RarScheme.AMBIGUOUS and len(parsed) > 1:
            scheme = RarScheme.PART_N

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
                    return cls(stem=stem, rar_scheme=RarScheme.AMBIGUOUS, volumes=parsed)
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

        return cls(stem=stem, rar_scheme=scheme, volumes=parsed)

    
    @classmethod
    def find_rar_files(
        cls, directory: Path | str, seek_stem: str | None = None
    ) -> dict[str, typing.Self]:
        """Find and group RAR archives in a directory by stem."""
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
        return {stem: cls.parse_rar_list(paths) for stem, paths in rar_dict.items()}
