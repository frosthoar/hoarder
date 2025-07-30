"""Abstract base class for password extraction plugins."""

import abc
import typing

import hoarder.password_store

class PasswordPlugin(abc.ABC):
    """Abstract base class for password extraction plugins."""
    @abc.abstractmethod
    def __init__(self, config: dict[str, typing.Any]):
        pass

    @abc.abstractmethod
    def extract_passwords(self) -> hoarder.password_store.PasswordStore:
        """Extract passwords from the file, returning a mapping of title -> passwords."""
        pass
