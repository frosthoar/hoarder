from hoarder.archives import RarScheme
from hoarder.archives.rar_path import RarArchiveSet


def test_parse() -> None:
    assert (
        RarArchiveSet.parse_rar_list(("a.part1.rar", "a.part2.rar")).rar_scheme == RarScheme.PART_N
    ), "Simple PART_N"

    assert (
        RarArchiveSet.parse_rar_list(("a.rar", "a.r00", "a.r01")).rar_scheme == RarScheme.DOT_RNN
    ), "Simple DOT_RNN"

    assert (
        RarArchiveSet.parse_rar_list(("a.rar",)).rar_scheme == RarScheme.DOT_RNN
    ), "Almost ambiguous but cannot be PART_N"

    assert (
        RarArchiveSet.parse_rar_list(("a.part1.rar",)).rar_scheme == RarScheme.AMBIGUOUS
    ), "Actually ambiguous even though it is likely PART_N"

    assert (
        RarArchiveSet.parse_rar_list(("a.part2.rar",)).rar_scheme == RarScheme.DOT_RNN
    ), "Invalid index forces this to be interpreted as DOT_RNN"

    assert (
        RarArchiveSet.parse_rar_list(()).rar_scheme == RarScheme.PART_N
    ), "Empty input is only interpretable as a PART_N"

    try:
        RarArchiveSet.parse_rar_list(("",))
        raise AssertionError("Bad format")
    except ValueError as e:
        assert str(e) == '"" does not match the scheme-3 pattern'

    try:
        RarArchiveSet.parse_rar_list(("a.rar", "b.r00"))
        raise AssertionError("Disparate stems")
    except ValueError as e:
        assert str(e) == "b.r00 has an inconsistent stem"

    try:
        RarArchiveSet.parse_rar_list(("a.r00", "a.r01"))
        raise AssertionError("Missing non-indexed suffix")
    except ValueError as e:
        assert str(e) == "0 paths have a non-indexed suffix; must be exactly one"

    try:
        RarArchiveSet.parse_rar_list(("a.rar", "a.rar"))
        raise AssertionError("Duplicate non-indexed suffixes")
    except ValueError as e:
        assert str(e) == "2 paths have a non-indexed suffix; must be exactly one"

    try:
        RarArchiveSet.parse_rar_list(("a.part0.rar", "a.part1.rar"))
        raise AssertionError("PART_N indexed from wrong base value")
    except ValueError as e:
        assert str(e) == "The following indices are unexpected: 0"

    try:
        RarArchiveSet.parse_rar_list(("a.part1.rar", "a.part1.rar"))
        raise AssertionError("PART_N missing an index")
    except ValueError as e:
        assert str(e) == "The following indices are missing: 2"


if __name__ == "__main__":
    test_parse()
