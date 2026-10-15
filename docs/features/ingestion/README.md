# IBM ingestion

**Status: implementation pending.** Owner: `src/fintrace/ingestion/`.

## Proposed interface
```text
ingest_ibm(source_path, manifest, policy) -> IngestionResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Missing header fields or unset timestamp interpretation stop the affected import.
- Malformed rows go to quarantine. Partial imports must not appear complete.
- Reimporting the same source identity is idempotent.

## Acceptance criteria
- Two equal account strings at different banks produce different account identities.
- Two identical-valued source payments remain two transactions.
- Source laundering labels are absent from normalized transaction columns.

## Data availability
Supported by IBM transaction exports after schema and source interpretation are verified.
