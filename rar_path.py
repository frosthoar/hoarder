import enum
import re
import typing
from pathlib import Path


class RarVersion(enum.IntEnum):
    AMBIGUOUS = 0
    V3 = 3
    V5 = 5


V3_PAT = re.compile(
r'''(?x)
    ^       # start
    (?P<stem>
        .+  # require a stem of at least one character
    )
    \.      # suffix separator dot
    (?P<suffix>
        rar |  # first literal 'rar' suffix
        r(?P<index>
            \d\d  # two-digit index
        )
    )
    $  # end
''')

V5_PAT = re.compile(
r'''(?x)
    ^       # start
    (?P<stem>
        .+  # require a stem of at least one character
    )
    \.part   # beginning of first suffix component
    (?P<index>
        \d+  # at least one digit
    )
    \.       # beginning of last suffix component
    (?P<suffix>
        rar  # last suffix component
    )
    $        # end
''')


class RARPath(typing.NamedTuple):
    index: int  # type: ignore[assignment]
    path: str
    stem: str
    suffix: str

    @classmethod
    def from_match(cls, match: re.Match | None ) -> typing.Self:
        if match is None:
            raise ValueError('match is None')
        return cls(
            index=-1 if match['index'] is None else int(match['index']),
            path=match.string,
            stem=match['stem'],
            suffix=match['suffix'],
        )

    def __str__(self) -> str:
        return self.path


def parse_rar_list(paths: typing.Sequence[str | Path]) -> tuple[RarVersion, list[RARPath]]:
    if len(paths) == 0:
        # Since there is no non-indexed .rar, this must be interpreted as an "empty V5"
        return RarVersion.V5, []

    matches = [V5_PAT.match(str(p)) for p in paths]

    if any(m is None for m in matches):
        matches = [V3_PAT.match(str(p)) for p in paths]
        version = RarVersion.V3

        for path, match in zip(paths, matches):
            if match is None:
                raise ValueError(f'"{path}" does not match the version-3 pattern')
    elif len(paths) > 1:
        version = RarVersion.V5
    else:
        version = RarVersion.AMBIGUOUS

    parsed = [RARPath.from_match(match) for match in matches]

    stem = parsed[0].stem
    for rp in parsed[1:]:
        if getattr(rp, "stem", None) != stem:
            raise ValueError(f'{rp} has an inconsistent stem')

    actual = {match.index for match in parsed}

    match version:
        case RarVersion.V3:
            base = -1
        case RarVersion.V5:
            base = 1
        case RarVersion.AMBIGUOUS:
            # It's only possible for this to be a valid V5 if the only index is 1
            if actual == {1}:
                return version, parsed
            version = RarVersion.V3
            base = -1

            # This started as an ambiguous case where the index might have been part of a V5 suffix.
            # Since we've ruled that out, the actual index set is reinterpreted as the base only (-1).
            actual = {-1}

    if version == RarVersion.V3:
        n_unnumbered = sum(
            1 for match in parsed
            if match.suffix == 'rar'
        )
        if n_unnumbered != 1:
            raise ValueError(f'{n_unnumbered} paths have a non-indexed suffix; must be exactly one')

    expected = set(range(base, base + len(paths)))
    spurious = actual - expected
    if spurious:
        raise ValueError(
            'The following indices are unexpected: '
            + ', '.join(str(i) for i in spurious)
        )
    missing = expected - actual
    if missing:
        raise ValueError(
            'The following indices are missing: '
            + ', '.join(str(i) for i in missing)
        )

    return version, parsed


def rar_sort(rar_paths: typing.Sequence[str | Path]) -> list[str]:
    _, parsed = parse_rar_list(rar_paths)
    return [rar_path.path for rar_path in sorted(parsed)]

def find_rar_files(directory: Path | str) -> dict[str, list[Path]]:
    directory = Path(directory)
    rar_dict: dict[str, list[Path]] = {}
    for path in directory.iterdir():
        if match := V5_PAT.match(str(path.name)):
            stem = str(Path(match["stem"]))
            if rar_dict.get(stem):
                rar_dict[stem].append(path)
            else:
                rar_dict[stem] = [path]
        elif match := V3_PAT.match(str(path.name)):
            stem = str(Path(match["stem"]))
            if rar_dict.get(stem):
                rar_dict[stem].append(path)
            else:
                rar_dict[stem] = [path]
    return {k: [Path(p) for p in rar_sort(v)] for k, v in rar_dict.items()}


def test_parse() -> None:
    assert parse_rar_list(
        ('a.part1.rar', 'a.part2.rar')
    )[0] == RarVersion.V5, 'Simple V5'

    assert parse_rar_list(
        ('a.rar', 'a.r00', 'a.r01')
    )[0] == RarVersion.V3, 'Simple V3'

    assert parse_rar_list(
        ('a.rar',)
    )[0] == RarVersion.V3, 'Almost ambiguous but cannot be V5'

    assert parse_rar_list(
        ('a.part1.rar',)
    )[0] == RarVersion.AMBIGUOUS, 'Actually ambiguous even though it is likely V5'

    assert parse_rar_list(
        ('a.part2.rar',)
    )[0] == RarVersion.V3, 'Invalid index forces this to be interpreted as V3'

    assert parse_rar_list(())[0] == RarVersion.V5, 'Empty input is only interpretable as a V5'

    try:
        parse_rar_list(('',))
        raise AssertionError('Bad format')
    except ValueError as e:
        assert str(e) == '"" does not match the version-3 pattern'

    try:
        parse_rar_list(('a.rar', 'b.r00'))
        raise AssertionError('Disparate stems')
    except ValueError as e:
        assert str(e) == 'b.r00 has an inconsistent stem'

    try:
        parse_rar_list(('a.r00', 'a.r01'))
        raise AssertionError('Missing non-indexed suffix')
    except ValueError as e:
        assert str(e) == '0 paths have a non-indexed suffix; must be exactly one'

    try:
        parse_rar_list(('a.rar', 'a.rar'))
        raise AssertionError('Duplicate non-indexed suffixes')
    except ValueError as e:
        assert str(e) == '2 paths have a non-indexed suffix; must be exactly one'

    try:
        parse_rar_list(('a.part0.rar', 'a.part1.rar'))
        raise AssertionError('V5 indexed from wrong base value')
    except ValueError as e:
        assert str(e) == 'The following indices are unexpected: 0'

    try:
        parse_rar_list(('a.part1.rar', 'a.part1.rar'))
        raise AssertionError('V5 missing an index')
    except ValueError as e:
        assert str(e) == 'The following indices are missing: 2'


def test_sort() -> None:
    assert rar_sort(('a.r00', 'a.rar', 'a.r01')) == (
        'a.rar', 'a.r00', 'a.r01',
    ), 'Simple v3 sort'

    assert rar_sort(('a.part2.rar', 'a.part1.rar')) == (
        'a.part1.rar', 'a.part2.rar',
    )


if __name__ == '__main__':
    test_parse()
    test_sort()
