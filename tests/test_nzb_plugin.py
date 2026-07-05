"""Tests for the NZB password plugin."""

import logging
import os
import pathlib

import pytest
from hoarder.passwords import NzbPasswordPlugin, PasswordStore
from hoarder.utils import TableFormatter
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
    password_store: PasswordStore = nzb_plugin.extract_passwords()
    formatter = TableFormatter(merge_first_column=True)
    logger.info(formatter.format_presentable(password_store))
    assert len(password_store) == 4

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


def test_nzb_plugin_requires_list_nzb_paths(tmp_path: pathlib.Path) -> None:
    with pytest.raises(KeyError, match="nzb_paths"):
        NzbPasswordPlugin({})

    with pytest.raises(ValueError, match="nzb_paths"):
        NzbPasswordPlugin({"nzb_paths": []})


@suppress_type_checks
def test_nzb_plugin_rejects_non_list_nzb_paths(tmp_path: pathlib.Path) -> None:
    """A bare string is iterable char-by-char; it must be rejected."""
    with pytest.raises(TypeError, match="nzb_paths"):
        NzbPasswordPlugin({"nzb_paths": str(tmp_path)})  # type: ignore[arg-type]


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
