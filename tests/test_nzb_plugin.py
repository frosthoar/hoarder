"""Tests for the NZB password plugin."""

import logging
import os
import pathlib

import pytest
from hoarder.passwords import NzbPasswordPlugin, PasswordStore
from hoarder.utils import pformat
from typeguard import suppress_type_checks

logger = logging.getLogger("hoarder.tests.test_nzb_plugin")


@pytest.fixture
def nzb_plugin() -> NzbPasswordPlugin:
    nzb_path = (
        pathlib.Path(os.path.abspath(__file__)).parent / ".." / "test_files" / "nzb"
    )
    nzb_paths = [str(nzb_path)]
    return NzbPasswordPlugin({"nzb_paths": nzb_paths})


def test_nzb_plugin(nzb_plugin: NzbPasswordPlugin) -> None:
    """Covers plain NZBs, an unencrypted RAR wrapping NZBs, and an
    encrypted RAR wrapping NZBs opened via its filename's {{password}}.

    Also proves a RAR whose filename password doesn't actually open it
    (linux-isos-locked{{wrongguess}}.rar) is skipped rather than aborting
    the directory walk - the entries above and below it still show up.
    """
    password_store: PasswordStore = nzb_plugin.extract_passwords()
    logger.info(pformat(password_store))
    assert len(password_store) == 5

    assert "archlinux-2025.07.01-x86_64.iso" in password_store
    assert password_store["archlinux-2025.07.01-x86_64.iso"] == set(["letmein"])

    assert "ubuntu-25.04-desktop-x64" in password_store
    assert password_store["ubuntu-25.04-desktop-x64"] == set(["monkey"])

    assert "Leap-16.0-offline-installer-x86_64-Build143.1.install.iso" in password_store
    assert password_store[
        "Leap-16.0-offline-installer-x86_64-Build143.1.install.iso"
    ] == set(["qwerty"])

    assert "debian-12.11.0-amd64-netinst.iso" in password_store
    assert password_store["debian-12.11.0-amd64-netinst.iso"] == set(["guessme"])

    assert "fedora-42-x86_64-dvd.iso" in password_store
    assert password_store["fedora-42-x86_64-dvd.iso"] == set(["letmein2"])


def test_nzb_plugin_requires_list_nzb_paths(tmp_path: pathlib.Path) -> None:
    with pytest.raises(KeyError, match="nzb_paths"):
        NzbPasswordPlugin({})

    with pytest.raises(ValueError, match="nzb_paths"):
        NzbPasswordPlugin({"nzb_paths": []})


@suppress_type_checks
def test_nzb_plugin_rejects_non_list_nzb_paths(tmp_path: pathlib.Path) -> None:
    """A bare string is iterable char-by-char; it must be rejected."""
    with pytest.raises(TypeError, match="nzb_paths"):
        NzbPasswordPlugin({"nzb_paths": str(tmp_path)})  # type: ignore[dict-item]


def test_nzb_plugin_skips_unreadable_nzb_and_continues(
    tmp_path: pathlib.Path,
) -> None:
    """A file that can't be read/decoded must not stop extraction of the rest."""
    good_nzb = tmp_path / "good-download{{secret123}}.nzb"
    good_nzb.write_text("<nzb></nzb>")

    # No {{password}} in the name, so extraction falls through to reading the
    # file content, which is where the invalid UTF-8 bytes blow up.
    broken_nzb = tmp_path / "broken-download.nzb"
    broken_nzb.write_bytes(b"\xff\xfe not valid utf-8")

    plugin = NzbPasswordPlugin({"nzb_paths": [str(tmp_path)]})
    password_store = plugin.extract_passwords()

    assert "good-download" in password_store
    assert password_store["good-download"] == set(["secret123"])
    assert "broken-download" not in password_store


def test_nzb_plugin_repr_shows_configured_paths(tmp_path: pathlib.Path) -> None:
    plugin = NzbPasswordPlugin({"nzb_paths": [str(tmp_path)]})
    assert repr(plugin) == f"NzbPasswordPlugin(nzb_paths=['{tmp_path}'])"


def test_nzb_plugin_extract_passwords_logs_what_it_loaded(
    nzb_plugin: NzbPasswordPlugin, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="hoarder.passwords.nzb_password_plugin"):
        nzb_plugin.extract_passwords()

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "Reading NZB directory" in m and str(next(iter(nzb_plugin._nzb_paths))) in m
        for m in messages
    )
    assert any("Found 5 entries across 1 NZB director" in m for m in messages)


def test_nzb_plugin_reports_vanished_directory_instead_of_empty(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A directory that disappears or becomes unreadable after construction
    must be reported as a failed scan, not silently treated as a successfully
    scanned empty directory - os.walk's default onerror swallows the listing
    failure, which would otherwise be indistinguishable from a directory that
    is simply empty."""
    nzb_dir = tmp_path / "nzbs"
    nzb_dir.mkdir()
    plugin = NzbPasswordPlugin({"nzb_paths": [str(nzb_dir)]})
    nzb_dir.rmdir()

    with caplog.at_level(logging.INFO, logger="hoarder.passwords.nzb_password_plugin"):
        password_store = plugin.extract_passwords()

    assert len(password_store) == 0
    assert plugin._nzb_paths == {nzb_dir: False}

    messages = [record.getMessage() for record in caplog.records]
    assert any("Failed to list part of NZB directory" in m for m in messages)
    assert any(
        "Found 0 entries across 1 NZB directories (0 fully scanned, 1 partially scanned)"
        in m
        for m in messages
    )


def test_nzb_plugin_counts_partially_scanned_directory_with_entries(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A directory with one unreadable subdirectory but a readable NZB
    elsewhere in it is only partially scanned, but it did contribute an
    entry - the summary must say so, not report it as one of "0 NZB
    directories" alongside the entries it actually produced."""
    nzb_dir = tmp_path / "nzbs"
    nzb_dir.mkdir()
    (nzb_dir / "good-download{{secret123}}.nzb").write_text("<nzb></nzb>")
    locked = nzb_dir / "locked"
    locked.mkdir()
    locked.chmod(0o000)

    plugin = NzbPasswordPlugin({"nzb_paths": [str(nzb_dir)]})
    try:
        with caplog.at_level(
            logging.INFO, logger="hoarder.passwords.nzb_password_plugin"
        ):
            password_store = plugin.extract_passwords()
    finally:
        locked.chmod(0o755)

    assert "good-download" in password_store
    assert plugin._nzb_paths == {nzb_dir: False}

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "Found 1 entries across 1 NZB directories (0 fully scanned, 1 partially scanned)"
        in m
        for m in messages
    )
