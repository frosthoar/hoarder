"""Abstract base class for password extraction plugins."""

import abc
import typing

from .password_store import PasswordStore


class PasswordPlugin(abc.ABC):
    """Abstract base class for password extraction plugins."""

    @abc.abstractmethod
    def __init__(self, config: dict[str, typing.Any]):
        pass

    @abc.abstractmethod
    def extract_passwords(self) -> PasswordStore:
        """Extract passwords from the file, returning a mapping of title -> passwords."""
        pass
