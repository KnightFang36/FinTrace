# IBM ingestion implementation instructions

## Purpose
Own the source service described in `docs/features/ingestion/README.md`. Source provenance/header verification in manifest.py is implemented; the CSV normalization adapter remains pending. Follow data/README.md for the manifest and CLI contract.

## Inputs
- Immutable IBM CSV with verified positional header, dataset manifest and parsing policy.
- Explicit decimal precision, timezone interpretation and chunk size; optional benchmark annotations are handled separately.

## Outputs
- Detection-facing transactions and observed account registry in Parquet.
- Separate benchmark-label artifact, completed provenance manifest, row lineage and ingestion statistics.

## Functionality
- Verify the duplicated Account columns by position; preserve identifiers as strings and raw source values.
- Assign stable IDs using dataset/file/record identity. Identical transfer values do not imply duplicate events.
- Stream chunks and coordinate validation before committing a completed dataset version.
- Extract laundering labels into a physically separate evaluation artifact; never return them in detector records.

## Module responsibilities
- `audit.py`: Read-only source inventory, supplemental headers/checksums, record counts and evaluation-only pattern-block diagnostics. Never infer timezone, acquisition date or complete coverage.
- `ibm.py`: Positional IBM CSV normalization and source-label separation.
- `manifest.py`: Source hashes, provenance, timestamp interpretation and observation coverage.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. This adapter may extract source labels only into the separate evaluation artifact; its detection-facing outputs must remain label-free. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
