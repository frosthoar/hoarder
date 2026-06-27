# Discovery and Correlation Plan

## Overview

The pipeline processes scan targets sequentially. Archive discovery must be
scoped to each scan target, not the entire storage path. Archives may be
located inside the target, beside it, or the target itself may be an archive.

A `ScanTarget` is the input/work item for the pipeline (path-based), while
`Download` is the output/domain entity (title-based, persisted).

## Separation of Concerns

| Concern            | Responsibility                  |
|--------------------|---------------------------------|
| WHAT to find       | Archive class (discover method) |
| WHERE to search    | ScanTarget / config             |
| WHICH are relevant | Correlation phase               |

## Component Design

### 0. AnchoredPathMixin and AnchoredPath (path-in-storage pattern)

- Mixin provides the `full_path` property
- Works with both regular classes and dataclasses
- Concrete `AnchoredPath` class for direct use
- Located in `src/hoarder/utils/path_utils.py`

```python
class AnchoredPathMixin:
    """Mixin providing full_path for classes with storage_path and path."""
    storage_path: Path      # type hint only, subclass defines field
    path: PurePath          # type hint only, subclass defines field

    @property
    def full_path(self) -> Path:
        """Resolve to concrete path for filesystem I/O."""
        return self.storage_path / self.path

@dataclass
class AnchoredPath(AnchoredPathMixin):
    """Concrete class for direct use."""
    storage_path: Path
    path: PurePath
```

Used as mixin by:
- `HashArchive` (existing, regular class - to be refactored)
- `RealFile` (existing, dataclass - to be refactored)
- `ScanTarget` (new, dataclass)

> Note: Existing `full_path` properties will be inherited from mixin (no code change needed).

### 1. Archive Discovery (classmethod on each archive type)

- Receives `AnchoredPath` scope for consistent API
- No knowledge of scan targets
- Non-recursive by default

```python
class HashArchive(AnchoredPathMixin, ABC):
    @classmethod
    def from_path(cls, location: AnchoredPath, **kwargs) -> Self:
        """Create archive from location. Refactored to use AnchoredPath."""
        ...

    @classmethod
    @abstractmethod
    def discover(cls, scope: AnchoredPath) -> list[Self]:
        """Find archives of this type within scope."""
        ...

class SfvArchive(HashArchive):
    @classmethod
    def discover(cls, scope: AnchoredPath) -> list[SfvArchive]:
        search_path = scope.full_path
        if search_path.is_file():
            if search_path.suffix.lower() == ".sfv":
                return [cls.from_path(scope)]
            return []
        results = []
        for p in search_path.glob("*.sfv"):
            relative = p.relative_to(scope.storage_path)
            results.append(cls.from_path(AnchoredPath(scope.storage_path, relative)))
        return results

class RarArchive(HashArchive):
    @classmethod
    def discover(cls, scope: AnchoredPath) -> list[RarArchive]:
        search_path = scope.full_path
        # Uses existing find_rar_files() logic from rar_path.py
        rar_sets = find_rar_files(search_path)
        results = []
        for first_vol in rar_sets:
            relative = first_vol.relative_to(scope.storage_path)
            results.append(cls.from_path(AnchoredPath(scope.storage_path, relative)))
        return results

class HashNameArchive(HashArchive):
    @classmethod
    def discover(cls, scope: AnchoredPath) -> list[HashNameArchive]:
        search_path = scope.full_path
        results = []
        candidates = [search_path] if search_path.is_file() else search_path.iterdir()
        for p in candidates:
            if p.is_file() and cls._matches_hash_pattern(p.name):
                relative = p.relative_to(scope.storage_path)
                results.append(cls.from_path(AnchoredPath(scope.storage_path, relative)))
        return results
```

### 2. ScanTarget (determines search scope)

- Represents a single unit to process (file or directory)
- Inherits from `AnchoredPathMixin` (gets `full_path` property)
- Returns `AnchoredPath` from search methods for consistent API
- Provides configurable search paths for archive discovery

```python
@dataclass
class DiscoveryConfig:
    search_parent: bool = True          # look in parent directory
    additional_paths: list[AnchoredPath] = field(default_factory=list)

@dataclass
class ScanTarget(AnchoredPathMixin):
    storage_path: Path
    path: PurePath
    config: DiscoveryConfig = field(default_factory=DiscoveryConfig)

    def get_archive_search_paths(self) -> list[AnchoredPath]:
        """Where to look for archives related to this unit."""
        paths = [AnchoredPath(self.storage_path, self.path)]
        if self.config.search_parent and self.path != PurePath("."):
            paths.append(AnchoredPath(self.storage_path, self.path.parent))
        paths.extend(self.config.additional_paths)
        return paths

    def get_file_search_paths(self) -> list[AnchoredPath]:
        """Where to look for real files belonging to this unit."""
        return [AnchoredPath(self.storage_path, self.path)]
```

### 3. Real File Discovery (simple function)

- Receives `AnchoredPath` scopes for consistent API
- Excludes known archive files

```python
def discover_real_files(
    scopes: list[AnchoredPath],
    exclude: set[Path] | None = None
) -> list[RealFile]:
    """Scan for real files, excluding archive paths."""
    exclude = exclude or set()
    results = []
    for scope in scopes:
        search_path = scope.full_path
        if search_path.is_file():
            if search_path not in exclude:
                results.append(RealFile.from_path(scope))
        else:
            for p in search_path.rglob("*"):
                if p.is_file() and p not in exclude:
                    relative = p.relative_to(scope.storage_path)
                    results.append(RealFile.from_path(
                        AnchoredPath(scope.storage_path, relative)
                    ))
    return results
```

### 4. Correlation (filters archives to relevant ones)

- Matches archives to real files by path
- Creates verification links

```python
def correlate_archives(
    archives: list[HashArchive],
    real_files: list[RealFile],
    unit: ScanTarget
) -> list[HashArchive]:
    """Filter archives to those relevant to this unit's files."""
    real_paths = {rf.path for rf in real_files}
    relevant = []
    for archive in archives:
        # FileEntry.path is relative to the archive file itself (bare filename
        # from SFV, etc.), so resolve it to storage_path-relative before
        # comparing against RealFile.path which is already storage_path-relative.
        archive_paths = {archive.path.parent / fe.path for fe in archive.files}
        if archive_paths & real_paths:  # has intersection
            relevant.append(archive)
    return relevant

def correlate_files_to_entries(
    real_files: list[RealFile],
    archives: list[HashArchive]
) -> dict[RealFile, list[FileEntry]]:
    """Match real files to their corresponding FileEntry records."""
    # Build lookup: storage_path-relative path -> list of FileEntry
    path_to_entries: dict[PurePath, list[FileEntry]] = defaultdict(list)
    for archive in archives:
        for entry in archive.files:
            resolved = archive.path.parent / entry.path
            path_to_entries[resolved].append(entry)

    # Match real files
    matches = {}
    for rf in real_files:
        if rf.path in path_to_entries:
            matches[rf] = path_to_entries[rf.path]
    return matches
```

### 5. Orchestrator Integration

- Coordinates discovery and correlation per scan target
- All methods use `AnchoredPath` for consistent API

```python
ARCHIVE_TYPES: list[type[HashArchive]] = [SfvArchive, RarArchive, HashNameArchive]

def process_target(target: ScanTarget) -> ProcessingResult:
    # 1. Discover archives from all search scopes
    archives: list[HashArchive] = []
    for scope in target.get_archive_search_paths():
        for archive_cls in ARCHIVE_TYPES:
            archives.extend(archive_cls.discover(scope))

    # 2. Discover real files
    archive_volume_paths = collect_archive_paths(archives)
    real_files = discover_real_files(
        target.get_file_search_paths(),
        exclude=archive_volume_paths
    )

    # 3. Correlate - filter to relevant archives
    relevant_archives = correlate_archives(archives, real_files, target)

    # 4. Match files to entries
    file_matches = correlate_files_to_entries(real_files, relevant_archives)

    # Continue to verification phase...
    return ProcessingResult(
        target=target,
        archives=relevant_archives,
        real_files=real_files,
        matches=file_matches
    )
```

## Edge Cases Handled

| Scenario                     | Unit Path               | Search Paths         | Result                      |
|------------------------------|-------------------------|----------------------|-----------------------------|
| Dir with internal SFV        | `downloads/Movie/`      | `[Movie/, downloads/]` | Finds `Movie/*.sfv`       |
| SFV beside directory         | `downloads/Movie/`      | `[Movie/, downloads/]` | Finds `downloads/Movie.sfv` |
| HashName file                | `downloads/file[ABC].mkv` | `[downloads/]`     | `HashNameArchive` matches it |
| RAR set in directory         | `downloads/Movie/`      | `[Movie/, downloads/]` | Finds first volume only   |
| Parent-level SFV             | `downloads/Movie/`      | `[Movie/, downloads/]` | Finds `downloads/release.sfv` |
| Unit is single file          | `downloads/video.mkv`   | `[downloads/]`       | Scans parent for archives   |

## File Locations

New files to create:

```text
src/hoarder/phases/
├── scan_target.py          # ScanTarget, DiscoveryConfig
├── discovery.py            # discover_real_files(), collect_archive_paths()
└── correlator.py           # correlate_archives(), correlate_files_to_entries()
```

Modifications to existing files:

| File | Change |
|------|--------|
| `src/hoarder/utils/path_utils.py` | Add `AnchoredPathMixin` and `AnchoredPath` |
| `src/hoarder/archives/hash_archive.py` | Inherit from `AnchoredPathMixin`, add `discover()` |
| `src/hoarder/archives/sfv_archive.py` | Implement `discover()` |
| `src/hoarder/archives/rar_archive.py` | Implement `discover()` |
| `src/hoarder/archives/hash_name_archive.py` | Implement `discover()` |
| `src/hoarder/downloads/real_file.py` | Inherit from `AnchoredPathMixin`, remove `full_path` |
