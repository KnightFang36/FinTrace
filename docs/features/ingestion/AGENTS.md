# IBM ingestion contract instructions

## Purpose
Maintain the authoritative contract in README.md for src/fintrace/ingestion/. Source auditing, versioned manifests, chunked normalization, label isolation and publisher-account link diagnostics are implemented. Keep actual callable interfaces and command limitations synchronized with the source services.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
