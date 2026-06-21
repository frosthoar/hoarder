# Hoarder PUML Implementation Checklist

This checklist is derived from:

- `discovery_correlation.puml`
- `discovery_correlation_sequence.puml`
- `pipeline_execution_flow.puml`
- `discovery_correlation_plan.txt`
- `pipeline_implementation_order.txt`

The goal is to map each “box/arrow” from the diagrams to concrete code artifacts in this repo, and mark what is already implemented vs still missing.

---

## Legend

- [x] implemented (exists in repo and roughly matches intent)
- [~] partially implemented (core exists, but diagram-required API/behavior is missing or mismatched)
- [ ] not implemented

---

## A) Path-in-storage foundation (AnchoredPath*)

- [x] `AnchoredPathMixin` exists and provides `full_path`
  - **Code**: `src/hoarder/utils/path_utils.py` (`AnchoredPathMixin.full_path`)
- [x] `AnchoredPath` dataclass exists with containment validation
  - **Code**: `src/hoarder/utils/path_utils.py` (`AnchoredPath.__post_init__`)

---

## B) Domain objects from “Discovery and Correlation Architecture”

### B1) FileEntry / HashArchive hierarchy

- [x] `FileEntry` domain model (path, size, hash, algo)
  - **Code**: `src/hoarder/archives/hash_archive.py` (`FileEntry`, `Algo`)
- [~] `HashArchive` is anchored and has `from_path(AnchoredPath)`
  - **Code**: `src/hoarder/archives/hash_archive.py` (`HashArchive`, `HashArchive.from_path`)
  - **Missing vs PUML**:
    - [ ] `@classmethod discover(scope: AnchoredPath) -> list[Self]` on base class (abstract)

### B2) Archive types (parsing exists; discovery API missing)

- [~] `SfvArchive`
  - **Implemented**: parsing via `_from_path(...)`
    - **Code**: `src/hoarder/archives/sfv_archive.py` (`SfvArchive._from_path`)
  - **Missing**:
    - [ ] `SfvArchive.discover(scope: AnchoredPath) -> list[SfvArchive]` (non-recursive, `*.sfv`, accept file-or-dir scopes)

- [~] `RarArchive`
  - **Implemented**:
    - parsing via `_from_path(...)` (handles file/dir input)
      - **Code**: `src/hoarder/archives/rar_archive.py` (`RarArchive._from_path`)
    - RAR set detection helper
      - **Code**: `src/hoarder/archives/rar_path.py` (`find_rar_files`, `RarScheme`, regex)
    - volume list + file extraction
      - **Code**: `src/hoarder/archives/rar_archive.py` (`get_volumes`, `read_file`)
  - **Missing**:
    - [ ] `RarArchive.discover(scope: AnchoredPath) -> list[RarArchive]`
      - Must return **first volume only** per set, per PUML/plan

- [~] `HashNameArchive`
  - **Implemented**:
    - parsing hash from filename via `_from_path(...)`
      - **Code**: `src/hoarder/archives/hash_name_archive.py`
    - `DELETABLE = False`
      - **Code**: `src/hoarder/archives/hash_name_archive.py`
  - **Missing**:
    - [ ] `HashNameArchive.discover(scope: AnchoredPath) -> list[HashNameArchive]`
      - Should match filename patterns (`[hash]` or `(hash)`) as per PUML

### B3) RealFile + Verification

- [x] `RealFile` anchored model with filesystem inspection + hash calculation
  - **Code**: `src/hoarder/downloads/real_file.py` (`RealFile.from_path`, `RealFile.calculate_hash`)
- [x] `Verification` model and trust logic
  - **Code**: `src/hoarder/downloads/real_file.py` (`Verification`, `Verification.is_trusted`)

---

## C) Discovery & correlation phase (per ScanTarget)

These correspond to “Discovery and Correlation Sequence” and the plan’s “New files to create” under `src/hoarder/phases/`.

### C1) ScanTarget and discovery config

- [ ] `DiscoveryConfig` dataclass
  - **Target**: `src/hoarder/phases/scan_target.py`
  - **Required API** (per PUML/plan):
    - `search_parent: bool = True`
    - `additional_paths: list[AnchoredPath]`
- [ ] `ScanTarget` dataclass (anchored)
  - **Target**: `src/hoarder/phases/scan_target.py`
  - **Required methods**:
    - `get_archive_search_paths() -> list[AnchoredPath]`
    - `get_file_search_paths() -> list[AnchoredPath]`

### C2) Archive discovery (Orchestrator calling per-type discover)

- [ ] Implement archive discovery loop for each `ScanTarget`
  - **Target**: likely `src/hoarder/phases/discovery.py` or orchestrator module
  - **Uses**:
    - `ScanTarget.get_archive_search_paths()`
    - `SfvArchive.discover(scope)`
    - `RarArchive.discover(scope)`
    - `HashNameArchive.discover(scope)`

### C3) Collect archive volume paths for exclusion

- [ ] `collect_archive_paths(archives: list[HashArchive]) -> set[pathlib.Path]`
  - **Target**: `src/hoarder/phases/discovery.py`
  - **Behavior**:
    - include all archive volume paths (RAR sets have multiple volumes)
    - used as `exclude` set for real file scanning

### C4) Real file discovery (exclude archive volumes)

- [ ] `discover_real_files(scopes: list[AnchoredPath], exclude: set[Path] | None) -> list[RealFile]`
  - **Target**: `src/hoarder/phases/discovery.py`
  - **Behavior**:
    - if scope is file: return it (unless excluded)
    - if scope is dir: recursive scan (rglob) returning files (unless excluded)

### C5) Correlation phase

- [ ] `correlate_archives(archives, real_files, unit) -> list[HashArchive]`
  - **Target**: `src/hoarder/phases/correlator.py`
  - **Behavior**:
    - filter archives to those whose `FileEntry.path` intersects with `RealFile.relative_path` (or compatible path basis)
- [ ] `correlate_files_to_entries(real_files, relevant_archives) -> dict[RealFile, list[FileEntry]]`
  - **Target**: `src/hoarder/phases/correlator.py`
  - **Behavior**:
    - build path→entries lookup
    - allow multiple entries per file (SFV + HashName, etc.)

### C6) ProcessingResult (handoff object)

- [ ] `ProcessingResult` model for per-target discovery+correlation output
  - **Target**: `src/hoarder/phases/orchestrator.py` or `src/hoarder/phases/models.py`
  - **Contains** (per sequence diagram):
    - `unit` (`ScanTarget`)
    - `relevant_archives`
    - `real_files`
    - `matches` (`dict[RealFile, list[FileEntry]]`)

---

## D) Provider-based pipeline (“Pipeline Execution Flow”)

Nothing in this section exists yet as first-class pipeline code under `src/hoarder/phases/` (package is missing). Some *building blocks* already exist (hashing, verifications, RAR extraction).

### D1) Decision handling (user interaction)

- [ ] `DecisionHandler` protocol / interface
  - **Target**: `src/hoarder/phases/decision_handler.py`
  - **Methods** (from `pipeline_implementation_order.txt` / PUML):
    - `on_online_lookup_needed(file, service)`
    - `on_hash_mismatch(file, expected, actual)`
    - `on_extraction_needed(archive, missing_files)`
    - `on_cleanup_ready(archives, total_size)`
    - `on_error(unit, error)`

### D2) Verification providers

- [ ] `VerificationProvider` protocol / base class
  - **Target**: `src/hoarder/phases/verification_provider.py`
  - **Core API**:
    - `can_verify(file) -> bool`
    - `get_verification(file) -> Verification | None`
  - **Priority/trust**:
    - providers are ordered (Archive, Filename, Online, SelfHash)

### D3) Concrete providers

- [ ] `ArchiveVerificationProvider`
  - **Target**: `src/hoarder/phases/providers/archive_provider.py`
  - **Uses**: correlation matches (`RealFile` → `FileEntry`) to produce `Verification(source=ARCHIVE)`
- [ ] `FilenameVerificationProvider`
  - **Target**: `src/hoarder/phases/providers/filename_provider.py`
  - **Uses**: `HashNameArchive` expectations (CRC in filename)
- [ ] `OnlineVerificationProvider`
  - **Target**: `src/hoarder/phases/providers/online_provider.py`
  - **Requires**:
    - privacy gate via `DecisionHandler`
    - response cache to `.hoarder/online_cache/{service}/{query_hash}.json`
- [ ] `SelfHashProvider` (fallback, untrusted)
  - **Target**: `src/hoarder/phases/providers/self_hash_provider.py`
  - **Uses**: `RealFile.calculate_hash` (or `ContentsHasher`) to produce `Verification(source=SELF_HASH)`

### D4) Hash computation and mismatch decisions

- [~] Hash computation primitive exists
  - **Implemented**: `RealFile.calculate_hash()` and `CRC32Hasher`
    - **Code**: `src/hoarder/downloads/real_file.py`, `src/hoarder/downloads/contents_hasher.py`
- [ ] Pipeline-level “hash verifier” stage
  - **Target**: `src/hoarder/phases/verifier.py`
  - **Behavior**:
    - compute actual hash, compare against chosen `Verification.hash_value`
    - invoke `DecisionHandler.on_hash_mismatch(...)` on mismatch

### D5) Extraction phase

- [~] Primitive exists: `RarArchive.read_file()` returns bytes for an entry
  - **Code**: `src/hoarder/archives/rar_archive.py`
- [ ] Extraction stage orchestration
  - **Target**: `src/hoarder/phases/extractor.py`
  - **Behavior**:
    - detect missing files, ask via `DecisionHandler.on_extraction_needed(...)`
    - extract, then re-run scanner/correlator/providers for extracted files

### D6) Cleanup phase

- [~] Deletability signal exists: `HashArchive.DELETABLE`
  - **Code**: `src/hoarder/archives/hash_archive.py`, `src/hoarder/archives/hash_name_archive.py`
- [ ] Cleanup stage orchestration
  - **Target**: `src/hoarder/phases/cleanup.py`
  - **Behavior**:
    - only when all files verified & trusted
    - ask via `DecisionHandler.on_cleanup_ready(...)`
    - delete archives respecting `DELETABLE`

### D7) Orchestrator

- [ ] `PhaseOrchestrator.run(...)`
  - **Target**: `src/hoarder/phases/orchestrator.py`
  - **Responsibilities** (per PUML):
    - enumerate scan targets in storage path
    - per target: discovery → correlation → provider chain → hash compare → extraction → cleanup
    - error handling via `DecisionHandler.on_error(...)`

---

## E) Tests / evidence of current state

- [x] Existing tests cover archive parsing + repositories + filename hash parsing:
  - `tests/test_sfv_file.py`
  - `tests/test_rar_archive.py`, `tests/test_rar_path.py`, `tests/test_rar_file.py`
  - `tests/test_hnf_file.py`, `tests/test_real_file.py`
  - `tests/test_hash_archive_repository.py`, `tests/test_real_file_repository.py`, etc.
- [ ] No tests exist yet for:
  - scan-target scoped discovery/correlation
  - provider chain behavior
  - orchestrator end-to-end pipeline execution


