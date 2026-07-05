from pathlib import Path, PurePath

import pytest
from hoarder.archives import RarScheme
from hoarder.archives.rar_path import (
    PART_N_PAT,
    locate_main_volume,
    parse_rar_list,
    rar_sort,
)

RAR_TEST_DIR = Path("test_files/rar")


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
        assert str(e) == '"" does not match the scheme-3 pattern'

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


def test_part_n_pat_extracts_full_stem_despite_embedded_part_substring() -> None:
    """The stem may itself legitimately contain ".part" (e.g. "archive.part").

    A naive `name.split(".part")[0]` would truncate at the first occurrence
    and silently produce the wrong stem; the regex is anchored on the
    trailing `.part<N>.rar` suffix instead, so it must find the correct,
    full stem.
    """
    match = PART_N_PAT.match("archive.part.part01.rar")
    assert match is not None
    assert match["stem"] == "archive.part"
    assert match["volume_index"] == "01"


def test_sort() -> None:
    assert rar_sort(("a.r00", "a.rar", "a.r01")) == (
        RarScheme.DOT_RNN,
        [
            "a.rar",
            "a.r00",
            "a.r01",
        ],
    ), "Simple DOT_RNN sort"

    assert rar_sort(("a.part2.rar", "a.part1.rar")) == (
        RarScheme.PART_N,
        [
            "a.part1.rar",
            "a.part2.rar",
        ],
    ), "Simple PART_N sort"


def test_locate_main_volume_part_n_padding_not_derivable_from_volume_count() -> None:
    """A real 5-volume archive, renamed to force two-digit padding.

    Demonstrates that padding cannot be inferred from n_volumes alone: rar
    itself would have named this "part1.rar".."part5.rar" (one digit), but
    real-world archives are sometimes renamed/repackaged with wider padding
    than their volume count strictly requires.
    """
    if not (RAR_TEST_DIR / "locate_forced_padding.part01.rar").exists():
        pytest.skip("RAR fixture files not found")

    volumes = locate_main_volume(
        RAR_TEST_DIR, PurePath("locate_forced_padding.part01.rar")
    )

    assert volumes.scheme == RarScheme.PART_N
    assert volumes.n_volumes == 5
    assert volumes.part_n_padding == 2


def test_locate_main_volume_part_n_no_padding() -> None:
    """A real 3-volume archive with rar's natural, unpadded part numbering."""
    if not (RAR_TEST_DIR / "locate_padding.part1.rar").exists():
        pytest.skip("RAR fixture files not found")

    volumes = locate_main_volume(RAR_TEST_DIR, PurePath("locate_padding.part1.rar"))

    assert volumes.scheme == RarScheme.PART_N
    assert volumes.n_volumes == 3
    assert volumes.part_n_padding == 1


def test_locate_main_volume_dot_rnn_has_no_part_n_padding() -> None:
    """A real old-style (.rar/.rNN) multi-volume archive."""
    main_volume = RAR_TEST_DIR / "v4_split_headers_unencrypted.rar"
    if not main_volume.exists():
        pytest.skip("RAR fixture files not found")

    volumes = locate_main_volume(
        RAR_TEST_DIR, PurePath("v4_split_headers_unencrypted.rar")
    )

    assert volumes.scheme == RarScheme.DOT_RNN
    assert volumes.n_volumes == 18
    assert volumes.part_n_padding is None


if __name__ == "__main__":
    test_parse()
    test_sort()
