"""Tests for resolve_passwords()."""

from pathlib import Path, PurePath

import pytest
from hoarder.archives import RarArchive, SfvArchive
from hoarder.passwords import PasswordStore
from hoarder.phases import resolve_passwords
from hoarder.utils import AnchoredPath

RAR_ROOT = Path("test_files/rar")
ENCRYPTED_FIXTURE = RAR_ROOT / "v4_encrypted.rar"
CORRECT_PASSWORD = "secret"
TITLE = "some-release"


@pytest.fixture()
def password_stub():
    assert (
        ENCRYPTED_FIXTURE.exists()
    ), f"Committed RAR fixture missing: {ENCRYPTED_FIXTURE}"
    scope = AnchoredPath(RAR_ROOT, PurePath(ENCRYPTED_FIXTURE.name))
    stub = RarArchive.discover(scope)[0]
    assert stub.requires_password is True
    return stub


def test_resolve_passwords_replaces_stub_when_a_candidate_works(password_stub) -> None:
    store = PasswordStore()
    store.add_password(TITLE, "wrong-1")
    store.add_password(TITLE, CORRECT_PASSWORD)
    store.add_password(TITLE, "wrong-2")

    resolved = resolve_passwords([password_stub], store, TITLE)

    assert len(resolved) == 1
    archive = resolved[0]
    assert archive is not password_stub
    assert archive.password == CORRECT_PASSWORD
    assert archive.requires_password is True
    assert len(archive.files) > 0


def test_resolve_passwords_leaves_stub_untouched_when_nothing_works(
    password_stub,
) -> None:
    store = PasswordStore()
    store.add_password(TITLE, "wrong-1")
    store.add_password(TITLE, "wrong-2")

    resolved = resolve_passwords([password_stub], store, TITLE)

    assert resolved == [password_stub]
    assert resolved[0].password is None
    assert resolved[0].files == set()


def test_resolve_passwords_ignores_titles_with_no_candidates(password_stub) -> None:
    store = PasswordStore()
    store.add_password("a-different-release", CORRECT_PASSWORD)

    resolved = resolve_passwords([password_stub], store, TITLE)

    assert resolved == [password_stub]


def test_resolve_passwords_passes_through_archives_that_do_not_need_a_password() -> (
    None
):
    sfv_root = Path("test_files/sfv")
    assert sfv_root.exists(), f"Committed test fixture missing: {sfv_root}"
    archive = SfvArchive.from_path(sfv_root, PurePath("files.sfv"))
    store = PasswordStore()
    store.add_password(TITLE, CORRECT_PASSWORD)

    resolved = resolve_passwords([archive], store, TITLE)

    assert resolved == [archive]
