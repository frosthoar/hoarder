"""Password store module for managing title-password associations."""
from __future__ import annotations

import copy
from collections import defaultdict


class PasswordStore:
    """A store that associates titles with multiple passwords using sets."""

    def __init__(self) -> None:
        self._store: dict[str, set[str]] = defaultdict(set)

    def __getitem__(self, title: str) -> set[str]:
        """Get all passwords for the specified title."""
        return self._store[title].copy()

    def __contains__(self, title: str) -> bool:
        return title in self._store

    def __len__(self) -> int:
        return len(self._store)

    def add_password(self, title: str, password: str) -> None:
        """Add a password to the specified title."""
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

    def __iter__(self):
        for title, passwords in self._store.items():
            yield title, passwords

    def __or__(self, p: PasswordStore) -> PasswordStore:
        self_copy = copy.deepcopy(self)
        for title, passwords in p:
            for password in passwords:
                self_copy.add_password(title, password)
        return self_copy

    def clear_passwords(self, title: str) -> None:
        """Clear all passwords for the specified title."""
        if title in self._store:
            del self._store[title]

    def pretty_print(self) -> str:
        """Return a pretty-formatted string representation of the password store."""
        if not self._store:
            return "PasswordStore (empty)"

        MAX_COL_WIDTH: int = 83

        # Calculate column widths
        max_title_length = min(
            MAX_COL_WIDTH, max(len(title) for title in self._store.keys())
        )
        max_password_length = max(
            max(len(password) for password in passwords)
            for passwords in self._store.values()
        )

        title_width = max(max_title_length, len("Title"))
        password_width = max(max_password_length, len("Password"))

        top_line = f"┏━{'━' * title_width}━┳━{'━' * password_width}━┓"
        header_line = (
            f"┃ {'Title'.ljust(title_width)} ┃ {'Password'.ljust(password_width)} ┃"
        )
        header_separator_line = f"┣━{'━' * title_width}━╇━{'━' * password_width}━┫"
        separator_line = f"┠─{'─' * title_width}─┼─{'─' * password_width}─┨"
        bottom_line = f"┗━{'━' * title_width}━┷━{'━' * password_width}━┛"

        lines = [top_line, header_line, header_separator_line]

        first_entry = True
        for title in sorted(self._store.keys()):
            if len(title) > MAX_COL_WIDTH:
                display_title = title[0 : (MAX_COL_WIDTH - 3)] + "..."
            else:
                display_title = title
            passwords = sorted(self._store[title])
            if not first_entry:
                # no need to add a separator for the first line
                lines.append(separator_line)
            for i, password in enumerate(passwords):
                if i == 0:
                    # First password for this title:
                    line = f"┃ {display_title.ljust(title_width)} │ {password.ljust(password_width)} ┃"
                else:
                    # Additional passwords for same title:
                    line = f"┃ {' ' * title_width} │ {password.ljust(password_width)} ┃"
                lines.append(line)
            first_entry = False

        lines.append(bottom_line)
        return "\n".join(lines)
