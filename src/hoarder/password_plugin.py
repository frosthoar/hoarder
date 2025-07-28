"""Abstract base class for password extraction plugins."""

import abc
import pathlib


class PasswordPlugin(abc.ABC):
    """Abstract base class for password extraction plugins."""

    @abc.abstractmethod
    def can_handle(self, file_path: pathlib.Path) -> bool:
        """Check if this plugin can handle the given file type."""
        pass

    @abc.abstractmethod
    def extract_passwords(self, file_path: pathlib.Path) -> dict[str, set[str]]:
        """Extract passwords from the file, returning a mapping of title -> passwords."""
        pass
