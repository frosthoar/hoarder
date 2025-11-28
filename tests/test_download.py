from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from hoarder.archives import HashArchive
from hoarder.downloads import Download, RealFile

FROZEN_TS = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)


def test_download_creation() -> None:
    """Test basic Download creation."""
    download = Download(
        title="test download",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="test comment",
        processed=False,
        real_files=[],
    )

    assert download.title == "test download"
    assert download.first_seen == FROZEN_TS
    assert download.last_seen == FROZEN_TS
    assert download.comment == "test comment"
    assert download.processed is False
    assert download.real_files == []
    assert download.hash_archives == []


def test_download_with_real_files() -> None:
    """Test Download with associated RealFiles."""
    storage_path = Path("/test/storage")
    real_file1 = RealFile(
        storage_path=storage_path,
        path=Path("file1.dat"),
        size=100,
        is_dir=False,
    )
    real_file2 = RealFile(
        storage_path=storage_path,
        path=Path("file2.bin"),
        size=200,
        is_dir=False,
    )

    download = Download(
        title="download with files",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment=None,
        processed=True,
        real_files=[real_file1, real_file2],
    )

    assert len(download.real_files) == 2
    assert download.real_files[0] == real_file1
    assert download.real_files[1] == real_file2
    assert download.processed is True
    assert download.comment is None
    assert download.hash_archives == []


def test_download_with_hash_archives() -> None:
    """Test Download with associated HashArchives."""
    # Note: This test doesn't create actual HashArchive instances
    # since they require file system access. We just test the field exists.
    download = Download(
        title="download with archives",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment=None,
        processed=True,
        real_files=[],
        hash_archives=[],
    )

    assert len(download.hash_archives) == 0
    assert download.processed is True


def test_download_equality() -> None:
    """Test Download equality comparison."""
    download1 = Download(
        title="test download",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    download2 = Download(
        title="test download",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    assert download1 == download2


def test_download_inequality() -> None:
    """Test Download inequality when attributes differ."""
    download1 = Download(
        title="download 1",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    download2 = Download(
        title="download 2",
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    assert download1 != download2


def test_download_title_cannot_be_empty() -> None:
    """Test that Download title cannot be empty."""
    with pytest.raises(ValueError, match="Download title cannot be empty"):
        Download(
            title="",
            first_seen=FROZEN_TS,
            last_seen=FROZEN_TS,
            processed=False,
        )

