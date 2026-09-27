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
    return SabnzbdPasswordPlugin(
        {
            "history_paths": [str(history_db_path)],
            "auto_detect_history_paths": False,
        }
    )


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


def test_sabnzbd_plugin_requires_history_paths_when_auto_detect_disabled() -> None:
    with pytest.raises(KeyError, match="history_paths"):
        SabnzbdPasswordPlugin({"auto_detect_history_paths": False})

    with pytest.raises(ValueError, match="history_paths"):
        SabnzbdPasswordPlugin({"history_paths": [], "auto_detect_history_paths": False})


def test_sabnzbd_plugin_rejects_non_list_history_paths(
    history_db_path: pathlib.Path,
) -> None:
    """A bare string is iterable char-by-char; it must be rejected, not silently
    treated as a one-path list of nonsense single-character paths."""
    with pytest.raises(TypeError, match="history_paths"):
        SabnzbdPasswordPlugin({"history_paths": str(history_db_path)})


def test_sabnzbd_plugin_raises_on_missing_file(tmp_path: pathlib.Path) -> None:
    missing = tmp_path / "does_not_exist.db"
    with pytest.raises(FileNotFoundError):
        SabnzbdPasswordPlugin({"history_paths": [str(missing)]})


def test_sabnzbd_plugin_skips_unreadable_database_and_continues(
    tmp_path: pathlib.Path, history_db_path: pathlib.Path
) -> None:
    """One corrupt/unreadable database must not discard results from the rest."""
    broken_db = tmp_path / "broken.db"
    broken_db.write_bytes(b"not a sqlite database")

    plugin = SabnzbdPasswordPlugin(
        {
            "history_paths": [str(broken_db), str(history_db_path)],
            "auto_detect_history_paths": False,
        }
    )

    password_store = plugin.extract_passwords()

    assert "archlinux-2025.07.01-x86_64.iso" in password_store
    assert password_store["archlinux-2025.07.01-x86_64.iso"] == {"letmein"}


def test_default_admin_dirs_on_posix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    assert SabnzbdPasswordPlugin._default_admin_dirs() == [
        tmp_path / ".config" / "sabnzbd" / "admin",
        tmp_path / ".sabnzbd" / "admin",
    ]


def test_default_admin_dirs_on_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert SabnzbdPasswordPlugin._default_admin_dirs() == [
        tmp_path / "sabnzbd" / "admin"
    ]


def test_default_admin_dirs_on_windows_without_localappdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert SabnzbdPasswordPlugin._default_admin_dirs() == []


@pytest.fixture
def fake_posix_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> pathlib.Path:
    """Point _default_admin_dirs()'s POSIX branch at an empty tmp_path home."""
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    return tmp_path


def test_sabnzbd_plugin_autodetects_default_history_db(
    fake_posix_home: pathlib.Path, history_db_path: pathlib.Path
) -> None:
    admin_dir = fake_posix_home / ".config" / "sabnzbd" / "admin"
    admin_dir.mkdir(parents=True)
    (admin_dir / "history1.db").write_bytes(history_db_path.read_bytes())

    plugin = SabnzbdPasswordPlugin({})

    password_store = plugin.extract_passwords()
    assert "archlinux-2025.07.01-x86_64.iso" in password_store


def test_sabnzbd_plugin_merges_explicit_and_autodetected_paths_by_default(
    fake_posix_home: pathlib.Path, history_db_path: pathlib.Path
) -> None:
    admin_dir = fake_posix_home / ".config" / "sabnzbd" / "admin"
    admin_dir.mkdir(parents=True)
    (admin_dir / "history1.db").write_bytes(history_db_path.read_bytes())

    plugin = SabnzbdPasswordPlugin({"history_paths": [str(history_db_path)]})

    assert len(plugin._history_paths) == 2


def test_sabnzbd_plugin_deduplicates_autodetected_path_already_given_explicitly(
    fake_posix_home: pathlib.Path, history_db_path: pathlib.Path
) -> None:
    admin_dir = fake_posix_home / ".config" / "sabnzbd" / "admin"
    admin_dir.mkdir(parents=True)
    default_db = admin_dir / "history1.db"
    default_db.write_bytes(history_db_path.read_bytes())

    plugin = SabnzbdPasswordPlugin({"history_paths": [str(default_db)]})

    assert len(plugin._history_paths) == 1


def test_sabnzbd_plugin_rejects_non_bool_auto_detect_flag(
    history_db_path: pathlib.Path,
) -> None:
    with pytest.raises(TypeError, match="auto_detect_history_paths"):
        SabnzbdPasswordPlugin(
            {
                "history_paths": [str(history_db_path)],
                "auto_detect_history_paths": "true",
            }
        )


def test_sabnzbd_plugin_falsey_non_bool_flag_reports_type_error() -> None:
    """A falsey-but-wrong-type flag (e.g. 0, []) with no history_paths should
    still report the type error, not a misleading "history_paths not set" -
    `not 0` and `not []` are both True, so a naive presence check evaluates
    the flag as "disabled" before ever validating its type."""
    with pytest.raises(TypeError, match="auto_detect_history_paths"):
        SabnzbdPasswordPlugin({"auto_detect_history_paths": 0})


def test_sabnzbd_plugin_default_auto_detect_raises_when_nothing_found(
    fake_posix_home: pathlib.Path,
) -> None:
    with pytest.raises(ValueError, match="history_paths"):
        SabnzbdPasswordPlugin({})
