# IBM ingestion implementation instructions

## Purpose
Own the source service described in `docs/features/ingestion/README.md`. Source auditing, manifest verification and chunked CSV-to-Parquet normalization are implemented. Follow data/README.md for the manifest and CLI contract. Keep dataset publication atomic and completed imports idempotent with artifact verification.

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
- For more than 250,000 accepted records, summarize exact account keys and duplicate hashes in 32 scratch partitions within the existing 512 MB DuckDB budget. Keep all endpoints for each key together, sort the final account registry, and preserve the small-input summary semantics.
- Keep the large endpoint/hash projections lazy via the source relation; parameterized DuckDB sql() eagerly materializes result sets before partitioned writes.
- Extract laundering labels into a physically separate evaluation artifact; never return them in detector records.

## Module responsibilities
- `audit.py`: Read-only source inventory, supplemental headers/checksums, record counts and evaluation-only pattern-block diagnostics. Never infer timezone, acquisition date or complete coverage.
- `ibm.py`: Positional IBM CSV normalization and source-label separation.
- `manifest.py`: Source hashes, provenance, timestamp interpretation and observation coverage.
- `publisher.py`: Preserve separately supplied synthetic publisher entities and emit review-only account link candidates. Zero-padding equivalence never rewrites observed account identity; conflicting candidates remain ambiguous.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. This adapter may extract source labels only into the separate evaluation artifact; its detection-facing outputs must remain label-free. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
