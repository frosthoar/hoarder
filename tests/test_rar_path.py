from hoarder.rar_path import RarScheme, parse_rar_list, rar_sort


def test_parse() -> None:
    assert (
        parse_rar_list(("a.part1.rar", "a.part2.rar"))[0] == RarScheme.PART_N
    ), "Simple PART_N"

    assert (
        parse_rar_list(("a.rar", "a.r00", "a.r01"))[0] == RarScheme.DOT_RNN
    ), "Simple DOT_RNN"

    assert (
        parse_rar_list(("a.rar",))[0] == RarScheme.DOT_RNN
    ), "Almost ambiguous but cannot be PART_N"

    assert (
        parse_rar_list(("a.part1.rar",))[0] == RarScheme.AMBIGUOUS
    ), "Actually ambiguous even though it is likely PART_N"

    assert (
        parse_rar_list(("a.part2.rar",))[0] == RarScheme.DOT_RNN
    ), "Invalid index forces this to be interpreted as DOT_RNN"

    assert (
        parse_rar_list(())[0] == RarScheme.PART_N
    ), "Empty input is only interpretable as a PART_N"

    try:
        parse_rar_list(("",))
        raise AssertionError("Bad format")
    except ValueError as e:
        assert str(e) == '"" does not match the version-3 pattern'

    try:
        parse_rar_list(("a.rar", "b.r00"))
        raise AssertionError("Disparate stems")
    except ValueError as e:
        assert str(e) == "b.r00 has an inconsistent stem"

    try:
        parse_rar_list(("a.r00", "a.r01"))
        raise AssertionError("Missing non-indexed suffix")
    except ValueError as e:
        assert str(e) == "0 paths have a non-indexed suffix; must be exactly one"

    try:
        parse_rar_list(("a.rar", "a.rar"))
        raise AssertionError("Duplicate non-indexed suffixes")
    except ValueError as e:
        assert str(e) == "2 paths have a non-indexed suffix; must be exactly one"

    try:
        parse_rar_list(("a.part0.rar", "a.part1.rar"))
        raise AssertionError("PART_N indexed from wrong base value")
    except ValueError as e:
        assert str(e) == "The following indices are unexpected: 0"

    try:
        parse_rar_list(("a.part1.rar", "a.part1.rar"))
        raise AssertionError("PART_N missing an index")
    except ValueError as e:
        assert str(e) == "The following indices are missing: 2"


def test_sort() -> None:
    assert rar_sort(("a.r00", "a.rar", "a.r01")) == [
        "a.rar",
        "a.r00",
        "a.r01",
    ], "Simple DOT_RNN sort"

    assert rar_sort(("a.part2.rar", "a.part1.rar")) == [
        "a.part1.rar",
        "a.part2.rar",
    ], "Simple PART_N sort"


if __name__ == "__main__":
    test_parse()
    test_sort()
