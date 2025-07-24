# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hoarder is a Python library for handling hash-based archives and file collections. It provides classes to work with various archive formats including SFV files, RAR archives, and hash-name archives, with a unified interface for reading file metadata and hash information.

## Architecture

The codebase follows a modular design centered around hash archives:

- **Core Abstraction**: `HashArchive` (src/hoarder/hash_archive.py) is the base abstract class that all archive types inherit from
- **Archive Implementations**:
  - `SfvArchive` - handles Simple File Verification (.sfv) files
  - `RarArchive` - processes RAR archive metadata using 7-zip
  - `HashNameArchive` - works with hash-based filename collections
- **Repository Layer**: `HashArchiveRepository` provides SQLite-based persistence for all archive types
- **Supporting Modules**:
  - `FileEntry` represents individual files with hash/metadata
  - `RarPath`/`RarScheme` handle RAR-specific path parsing
  - `path_utils` and `shared` provide common utilities

Key data flow: Archive files → Parsed into FileEntry objects → Stored/retrieved via Repository → Unified HashArchive interface

## Development Commands

### Running Tests
```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_repository.py -v

# Run tests with typeguard checking (configured in pyproject.toml)
python -m pytest
```

### Python Environment
- Python 3.13+ required
- Uses pytest with typeguard for runtime type checking
- Test configuration in pyproject.toml with pythonpath="src"

## Key Implementation Details

- All archive classes must implement the abstract methods from `HashArchive`
- `FileEntry` objects use path-based identity and hashing - don't mix entries from different containers
- Repository uses SQLite with foreign key enforcement via `Sqlite3FK` context manager  
- RAR processing requires 7-zip external dependency (referenced in `shared.SEVENZIP`)
- Test files are located in `test_files/` with sample archives for each format
- Password-protected RAR archives are supported via the `password` field

## File Structure
- `src/hoarder/` - Main package source
- `tests/` - Pytest test suite  
- `test_files/` - Sample archive files for testing
- `pyproject.toml` - Project configuration including pytest settings
