from __future__ import annotations

import datetime as dt
from pathlib import Path, PurePath

import pytest
from hoarder.downloads import Download, RealFile

FROZEN_TS = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)


def test_download_creation() -> None:
    """Test basic Download creation."""
    storage_path = Path("/test/storage")
    path = PurePath("test/path")
    download = Download(
        storage_path=storage_path,
        path=path,
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="test comment",
        processed=False,
        real_files=[],
    )

    assert download.storage_path == storage_path
    assert download.path == path
    assert download.first_seen == FROZEN_TS
    assert download.last_seen == FROZEN_TS
    assert download.comment == "test comment"
    assert download.processed is False
    assert download.real_files == []


def test_download_with_real_files() -> None:
    """Test Download with associated RealFiles."""
    storage_path = Path("/test/storage")
    real_file1 = RealFile(
        storage_path=storage_path,
        path=PurePath("file1.dat"),
        size=100,
        is_dir=False,
    )
    real_file2 = RealFile(
        storage_path=storage_path,
        path=PurePath("file2.bin"),
        size=200,
        is_dir=False,
    )

    download = Download(
        storage_path=storage_path,
        path=PurePath("download"),
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


def test_download_equality() -> None:
    """Test Download equality comparison."""
    storage_path = Path("/test/storage")
    path = PurePath("test/path")

    download1 = Download(
        storage_path=storage_path,
        path=path,
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    download2 = Download(
        storage_path=storage_path,
        path=path,
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    assert download1 == download2


def test_download_inequality() -> None:
    """Test Download inequality when attributes differ."""
    storage_path = Path("/test/storage")

    download1 = Download(
        storage_path=storage_path,
        path=PurePath("path1"),
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    download2 = Download(
        storage_path=storage_path,
        path=PurePath("path2"),
        first_seen=FROZEN_TS,
        last_seen=FROZEN_TS,
        comment="comment",
        processed=False,
        real_files=[],
    )

    assert download1 != download2

