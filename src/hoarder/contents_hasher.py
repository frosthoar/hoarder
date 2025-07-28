import logging
import typing
import zlib
from abc import ABC, abstractmethod
from pathlib import Path

try:
    from typing import override  # type: ignore [attr-defined]
except ImportError:
    from typing_extensions import override

logger = logging.getLogger("hoarder.contents_hasher")

class ContentsHasher(ABC):
    def __init__(self, path: str | Path):
        self._path: Path = Path(path)

    def hash_contents(self) -> bytes:
        if self._path.is_dir():
            logger.debug("Hashing directory yields empty hash")
            return self.empty_hash()
        else:
            logger.debug(f"Opening {self._path}")
            with open(self._path, "rb") as f:
                return self._hash_file(f)

    def _file_chunks(self, file: typing.IO[bytes], chunksize: int = 2**16):
        with file:
            chunk = file.read(chunksize)
            while len(chunk) > 0:
                yield chunk
                chunk = file.read(chunksize)

    def _hash_file(self, file: typing.IO[bytes]) -> bytes:
        for chunk in self._file_chunks(file):
            self.update(chunk)
        return self.digest()

    @abstractmethod
    def update(self, chunk: bytes) -> None:
        pass

    @abstractmethod
    def digest(self) -> bytes:
        pass

    @abstractmethod
    def empty_hash(self) -> bytes:
        pass


class CRC32Hasher(ContentsHasher):
    crc32: int

    def __init__(self, path: str | Path):
        super().__init__(path)
        self.crc32 = 0

    @override
    def update(self, chunk: bytes) -> None:
        self.crc32 = zlib.crc32(chunk, self.crc32)

    @override
    def digest(self) -> bytes:
        return self.crc32.to_bytes(4, "big")

    @override
    def empty_hash(self) -> bytes:
        return (0).to_bytes(4, "big")
