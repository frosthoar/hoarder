from abc import ABC, abstractmethod
import os
import typing
from pathlib import Path

class ContentsHasher(ABC):
    def __init__(self, path: str | Path):
        """Appropriate docstring."""
        
        self._path: Path = Path(path)
 
    def hash_dir_contents(self) -> dict[str, bytes]:
        """Appropriate docstring."""

        ret: dict[str, bytes] = {}
        for dirpath, _ , filenames in os.walk(self._path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                with open(filepath, "rb") as f:
                    ret[filepath] = self._hash_file(f)
        return ret
    
    def _file_chunks(self, file: typing.IO[bytes], chunksize:int=2**16):
        """Appropriate docstring."""

        with file:
            chunk = file.read(chunksize)
            while len(chunk) > 0:
                yield chunk
                chunk = file.read(chunksize)

    def _hash_file(self, file: typing.IO[bytes]) -> bytes:
        """Appropriate docstring."""
        
        for chunk in self._file_chunks(file):
            self.update(chunk)
        return self.digest()

    @abstractmethod
    def update(self, chunk: bytes) -> None:
        """Appropriate docstring."""

    @abstractmethod
    def digest(self) -> bytes:
        """Appropriate docstring."""
