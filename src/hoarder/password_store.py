"""Password store module for managing title-password associations."""

import typing
from collections import defaultdict


class PasswordStore:
    """A store that associates titles with multiple passwords using sets."""

    def __init__(self) -> None:
        self._store: dict[str, set[str]] = defaultdict(set)

    def __getitem__(self, title: str) -> set[str]:
        """Get all passwords for the specified title."""
        return self._store[title].copy()

    def add_password(self, title: str, password: str) -> None:
        """Add a password to the specified title."""
        self._store[title].add(password)

    def remove_password(self, title: str, password: str) -> bool:
        """Remove a password from the specified title. Returns True if removed, False if not found."""
        if title in self._store and password in self._store[title]:
            self._store[title].remove(password)
            if not self._store[title]:
                del self._store[title]
            return True
        return False

    def clear_passwords(self, title: str) -> None:
        """Clear all passwords for the specified title."""
        if title in self._store:
            del self._store[title]
