"""Tests for the NZB password plugin."""

import logging
import os
import pathlib

import pytest
from hoarder.passwords import NzbPasswordPlugin, PasswordStore
from hoarder.utils import TableFormatter

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

    assert password_store.add_password
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
