"""Retry password-protected archives against known candidate passwords."""

import logging

from ..archives import AbstractRarArchive, HashArchive, RarPasswordError
from ..passwords import PasswordStore

logger = logging.getLogger("hoarder.phases.password_resolution")


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
        logger.debug(
            "No known passwords for title %r; leaving %d archive(s) as-is",
            title,
            len(archives),
        )
        return archives

    candidates = password_store[title]
    logger.debug(
        "Resolving passwords for title %r against %d known candidate(s)",
        title,
        len(candidates),
    )

    resolved: list[HashArchive] = []
    for archive in archives:
        if not (isinstance(archive, AbstractRarArchive) and archive.requires_password):
            resolved.append(archive)
            continue

        logger.debug(
            "%s requires a password; trying %d candidate(s) for title %r",
            archive.full_path,
            len(candidates),
            title,
        )
        working: HashArchive | None = None
        for candidate in candidates:
            try:
                working = type(archive).from_path(
                    archive.anchor.storage_path,
                    archive.anchor.relative_path,
                    password=candidate,
                )
                logger.debug("Found a working password for %s", archive.full_path)
                break
            except RarPasswordError:
                continue
        if working is None:
            logger.warning(
                "None of %d known password(s) for title %r worked for %s",
                len(candidates),
                title,
                archive.full_path,
            )
        resolved.append(working if working is not None else archive)
    return resolved
