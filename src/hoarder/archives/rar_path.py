import collections.abc
import enum
import logging
import re
import typing
from pathlib import Path, PurePath

from ..utils.path_utils import AnchoredPath

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.archives.rar_path")


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
            volume_index=(
                -1 if match["volume_index"] is None else int(match["volume_index"])
            ),
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
        # Since there is no non-indexed .rar, this must be interpreted as an
        # "empty PART_N"
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
            # It's only possible for this to be a valid PART_N if the only
            # volume index is 1
            if actual == {1}:
                return scheme, parsed
            scheme = RarScheme.DOT_RNN
            base = -1

            # This started as an ambiguous case where the volume index might
            # have been part of a PART_N suffix. Since we've ruled that out,
            # the actual volume index set is reinterpreted as the base only
            # (-1).
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


class RarVolumeSet(typing.NamedTuple):
    """The result of locating a RAR archive's volumes on disk."""

    main_volume: Path
    main_volume_path: PurePath
    scheme: RarScheme
    n_volumes: int
    # Digit width of the volume index in a PART_N archive's file names (e.g.
    # 2 for "archive.part01.rar"), or None for other schemes. Not derivable
    # from n_volumes alone: a 5-volume archive can still be zero-padded to
    # two digits.
    part_n_padding: int | None


def locate_main_volume(anchor: AnchoredPath) -> RarVolumeSet | None:
    """Locate the main RAR volume and its sibling volumes for a given file.

    `anchor` guarantees its relative_path cannot resolve outside
    storage_path, so callers no longer need to check that themselves.

    Returns:
        A RarVolumeSet where main_volume is the absolute path to the first
        volume and main_volume_path is that same path relative to
        storage_path, or None if the file doesn't match any RAR naming
        scheme.

    Raises:
        FileNotFoundError: path does not refer to an existing file.
    """
    storage_path = anchor.storage_path
    path = anchor.relative_path
    full_path = anchor.full_path

    if not full_path.is_file():
        logger.debug("Path %s is not a file", full_path)
        raise FileNotFoundError(f"{full_path} could not be found")

    logger.debug("A file %s was given, trying to find RAR files", full_path)
    if match := PART_N_PAT.match(str(path.name)):
        logger.debug("Path %s matches a PART_N_PAT pattern", path)
    elif match := DOT_RNN_PAT.match(str(path.name)):
        logger.debug("Path %s matches a DOT_RNN_PAT pattern", path)

    if not match:
        return None

    seek_stem = match["stem"]
    search_dir = storage_path / path.parent
    logger.debug(
        "Finding RAR files with stem %s in directory %s", seek_stem, search_dir
    )
    rar_dict: dict[str, tuple[RarScheme, list[Path]]] = find_rar_files(search_dir, seek_stem)
    if not rar_dict:
        return None
    logger.info(rar_dict)
    scheme, rar_volumes = rar_dict[seek_stem]
    n_volumes = len(rar_volumes)
    logger.debug("Found %d volumes in %s", n_volumes, search_dir)
    main_volume = rar_volumes[0]
    logger.debug("Main volume is %s", main_volume)

    main_volume_path = main_volume.relative_to(storage_path)

    part_n_padding: int | None = None
    if scheme == RarScheme.PART_N:
        # parse_rar_list only assigns RarScheme.PART_N when every path in the
        # group, main_volume included, already matched PART_N_PAT - so this
        # cannot fail without find_rar_files/parse_rar_list itself being broken.
        padding_match = PART_N_PAT.match(main_volume.name)
        assert padding_match is not None, (
            f"{main_volume} was classified as PART_N but its name no longer "
            "matches PART_N_PAT"
        )
        part_n_padding = len(padding_match["volume_index"])

    return RarVolumeSet(
        main_volume, main_volume_path, scheme, n_volumes, part_n_padding
    )
