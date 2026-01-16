"""Password store module for managing title-password associations."""
from __future__ import annotations

import copy
from collections import defaultdict
from collections.abc import Iterator

from hoarder.utils.presentation import PresentationSpec, ScalarValue


class PasswordStore:
    """A store that associates titles with multiple passwords using sets."""

    def __init__(self, data: dict[str, set[str]] | None = None) -> None:
        """Initialize the password store, optionally from existing data.

        Args:
            data: Optional dictionary mapping titles to sets of passwords.
        """
        self._store: dict[str, set[str]] = defaultdict(set)
        if data is not None:
            for title, passwords in data.items():
                self._store[title] = set(passwords)

    def __getitem__(self, title: str) -> set[str]:
        """Get all passwords for the specified title."""
        return self._store[title].copy()

    def __contains__(self, title: str) -> bool:
        return title in self._store

    def __len__(self) -> int:
        return len(self._store)

    def add_password(self, title: str, password: str) -> None:
        """Add a password to the specified title."""
        if not isinstance(title, str):
            raise TypeError(f"title must be str, got {type(title).__name__}")
        if not isinstance(password, str):
            raise TypeError(f"password must be str, got {type(password).__name__}")
        if title == "":
            raise ValueError("Empty title")
        if password == "":
            raise ValueError("Empty password")
        self._store[title].add(password)

    def remove_password(self, title: str, password: str) -> bool:
        """Remove a password from the specified title.
        Returns True if removed, False if not found."""
        if title in self._store and password in self._store[title]:
            self._store[title].remove(password)
            if not self._store[title]:
                del self._store[title]
            return True
        return False

    def __iter__(self) -> Iterator[tuple[str, set[str]]]:
        for title, passwords in self._store.items():
            yield title, passwords.copy()

    def __ior__(self, p: PasswordStore) -> PasswordStore:
        for title, passwords in p:
            for password in passwords:
                self.add_password(title, password)
        return self

    def __or__(self, p: PasswordStore) -> PasswordStore:
        self_copy = copy.deepcopy(self)
        self_copy |= p
        return self_copy

    def clear_passwords(self, title: str) -> None:
        """Clear all passwords for the specified title."""
        if title in self._store:
            del self._store[title]

    def to_presentation(self) -> PresentationSpec:
        """Convert this password store to a presentation specification.

        Returns:
            A PresentationSpec with store metadata as scalars and title-password pairs as collection rows.
        """
        scalar: dict[str, ScalarValue] = {
            "type": "PasswordStore",
            "entries": len(self._store),
        }

        collection: list[dict[str, ScalarValue]] = []
        for title in sorted(self._store.keys()):
            passwords = sorted(self._store[title])
            for password in passwords:
                row: dict[str, ScalarValue] = {
                    "title": title,
                    "password": password,
                }
                collection.append(row)

        return PresentationSpec(scalar=scalar, collection=collection)
