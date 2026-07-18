"""Retry password-protected archives against known candidate passwords."""

from ..archives import AbstractRarArchive, HashArchive, RarPasswordError
from ..passwords import PasswordStore


def resolve_passwords(
    archives: list[HashArchive], password_store: PasswordStore, title: str
) -> list[HashArchive]:
    """Replace password-protected placeholder archives with working ones.

    discover() already returns encrypted RAR archives it couldn't open as
    placeholders (requires_password=True, no files, no password) instead of
    dropping them - see AbstractRarArchive.discover(). This tries every
    password known for `title` against each such placeholder and swaps in
    the first one that actually opens the archive. A placeholder for which
    no candidate works is left untouched, so it stays visible for a later
    retry (e.g. once a new password is learned) rather than silently lost.
    """
    if title not in password_store:
        return archives

    resolved: list[HashArchive] = []
    for archive in archives:
        if not (isinstance(archive, AbstractRarArchive) and archive.requires_password):
            resolved.append(archive)
            continue

        working: HashArchive | None = None
        for candidate in password_store[title]:
            try:
                working = type(archive).from_path(
                    archive.anchor.storage_path,
                    archive.anchor.relative_path,
                    password=candidate,
                )
                break
            except RarPasswordError:
                continue
        resolved.append(working if working is not None else archive)
    return resolved
