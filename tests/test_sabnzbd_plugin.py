"""Tests for the SABnzbd history password plugin."""

import os
import pathlib

import pytest
from hoarder.passwords import PasswordStore, SabnzbdPasswordPlugin


@pytest.fixture
def history_db_path() -> pathlib.Path:
    return (
        pathlib.Path(os.path.abspath(__file__)).parent
        / ".."
        / "test_files"
        / "sabnzbd"
        / "history1.db"
    )


@pytest.fixture
def sabnzbd_plugin(history_db_path: pathlib.Path) -> SabnzbdPasswordPlugin:
    return SabnzbdPasswordPlugin({"history_paths": [str(history_db_path)]})


def test_sabnzbd_plugin_extracts_passwords(
    sabnzbd_plugin: SabnzbdPasswordPlugin,
) -> None:
    password_store: PasswordStore = sabnzbd_plugin.extract_passwords()

    assert len(password_store) == 2

    assert "archlinux-2025.07.01-x86_64.iso" in password_store
    assert password_store["archlinux-2025.07.01-x86_64.iso"] == {"letmein"}

    assert "ubuntu-25.04-desktop-x64" in password_store
    assert password_store["ubuntu-25.04-desktop-x64"] == {"monkey"}


def test_sabnzbd_plugin_skips_entries_without_password(
    sabnzbd_plugin: SabnzbdPasswordPlugin,
) -> None:
    password_store = sabnzbd_plugin.extract_passwords()

    assert "debian-12.11.0-amd64-netinst.iso" not in password_store
    assert "no-password-download" not in password_store


def test_sabnzbd_plugin_requires_history_paths() -> None:
    with pytest.raises(KeyError, match="history_paths"):
        SabnzbdPasswordPlugin({})

    with pytest.raises(ValueError, match="history_paths"):
        SabnzbdPasswordPlugin({"history_paths": []})


def test_sabnzbd_plugin_raises_on_missing_file(tmp_path: pathlib.Path) -> None:
    missing = tmp_path / "does_not_exist.db"
    with pytest.raises(FileNotFoundError):
        SabnzbdPasswordPlugin({"history_paths": [str(missing)]})
