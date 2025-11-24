#!/usr/bin/env python3
"""Generate an example SQLite database using HashArchiveRepository.

This script creates a small example database with sample archives from the test_files directory.
"""

import pathlib
import sys

from hoarder.archives import (
    HashArchiveRepository,
    HashNameArchive,
    RarArchive,
    SfvArchive,
)


def main() -> None:
    """Generate example database with sample archives."""
    # Determine script location and project root
    script_dir = pathlib.Path(__file__).parent.resolve()
    db_path = script_dir / "example_hoarder.db"
    test_files_dir = script_dir / "test_files"

    print(f"Creating example database at: {db_path}")
    print(f"Using test files from: {test_files_dir}\n")

    # Remove existing database if it exists
    if db_path.exists():
        print(f"Removing existing database: {db_path}")
        db_path.unlink()

    # Create repository
    repo = HashArchiveRepository(db_path)
    print(f"Created repository with database: {db_path}\n")

    archives_created = 0

    # Add SFV archive
    sfv_file = test_files_dir / "sfv" / "files.sfv"
    if sfv_file.exists():
        print(f"Adding SFV archive: {sfv_file.name}")
        storage_path = sfv_file.parent
        path = pathlib.PurePath(sfv_file.name)
        try:
            sfv_archive = SfvArchive.from_path(storage_path, path)
            repo.save(sfv_archive)
            print(f"  ✓ Saved SFV archive with {len(sfv_archive.files)} file entries")
            archives_created += 1
        except Exception as e:
            print(f"  ✗ Failed to add SFV archive: {e}")
    else:
        print(f"  ⚠ SFV file not found: {sfv_file}")

    # Add HashNameArchive files
    hnf_dir = test_files_dir / "hnf"
    if hnf_dir.exists():
        hnf_files = list(hnf_dir.glob("*.mkv"))
        for hnf_file in hnf_files[:2]:  # Limit to first 2 for small example
            print(f"Adding HashNameArchive: {hnf_file.name}")
            storage_path = hnf_file.parent
            path = pathlib.PurePath(hnf_file.name)
            try:
                hnf_archive = HashNameArchive.from_path(storage_path, path)
                repo.save(hnf_archive)
                print(f"  ✓ Saved HashNameArchive with {len(hnf_archive.files)} file entry")
                archives_created += 1
            except Exception as e:
                print(f"  ✗ Failed to add HashNameArchive: {e}")
    else:
        print(f"  ⚠ HNF directory not found: {hnf_dir}")

    # Try to add a RAR archive (if available and not password protected)
    rar_dir = test_files_dir / "rar"
    if rar_dir.exists():
        rar_files = sorted(rar_dir.glob("*.rar"))
        # Look for a simple RAR file (not .part or .rNN)
        for rar_file in rar_files:
            if ".part" not in rar_file.name and not any(
                rar_file.name.endswith(f".r{i:02d}") for i in range(100)
            ):
                print(f"Adding RAR archive: {rar_file.name}")
                storage_path = rar_file.parent
                path = pathlib.PurePath(rar_file.name)
                try:
                    rar_archive = RarArchive.from_path(storage_path, path, password=None)
                    repo.save(rar_archive)
                    print(
                        f"  ✓ Saved RAR archive with {len(rar_archive.files)} file entries"
                    )
                    archives_created += 1
                    break  # Only add one RAR archive for the example
                except Exception as e:
                    print(f"  ✗ Failed to add RAR archive: {e}")
                    # Continue to next RAR file
                    continue

    print(f"\n{'='*60}")
    print(f"Example database created successfully!")
    print(f"Database location: {db_path}")
    print(f"Total archives saved: {archives_created}")
    print(f"{'='*60}")

    # Verify by loading one archive
    if archives_created > 0:
        print("\nVerifying database by loading archives...")
        # Try to load the SFV archive if it was added
        if sfv_file.exists():
            try:
                storage_path = sfv_file.parent
                path = pathlib.PurePath(sfv_file.name)
                loaded_archive = repo.load(storage_path, path)
                print(f"  ✓ Successfully loaded: {loaded_archive.__class__.__name__}")
                print(f"    Storage path: {loaded_archive.storage_path}")
                print(f"    Path: {loaded_archive.path}")
                print(f"    Files: {len(loaded_archive.files)}")
            except Exception as e:
                print(f"  ✗ Failed to load archive: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        sys.exit(1)

