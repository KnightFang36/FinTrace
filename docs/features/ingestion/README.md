# IBM ingestion

**Status: source provenance, upload auditing, transaction normalization and evaluation-label extraction are implemented.** Owner: `src/fintrace/ingestion/`.

Available now in `manifest.py`: `inspect_source`, `create_manifest`, `validate_manifest`, `write_manifest`, `load_manifest`, and `verify_manifest`. The CLI and exact input/output semantics are documented in [the data workflow](../../../data/README.md). These functions inspect headers and bytes, not financial rows.

## Proposed interface
```text
ingest_ibm(source_path, manifest, policy) -> IngestionResult
```
Implemented interface: `ingest_ibm(manifest_path, raw_root, processed_root, *, batch_size=25000, progress=None) -> dict`. The return value is a completion inventory or an integrity-verified reuse result. It publishes detection artifacts under datasets/<dataset_id>/ and benchmark artifacts under evaluation/<dataset_id>/, with separate quality reports.

The adapter streams CSV batches into decimal(38,8) Parquet, validates timestamps under the manifest policy, derives exact-key observed accounts, and retains duplicate financial records. Invalid financial rows are quarantined without their label column. A quarantined row keeps its ten financial fields, its issue codes, the observed source width and any unexpected trailing columns beyond the label, so a widened or misquoted source is diagnosable. Missing/invalid labels are recorded only in evaluation artifacts and do not reject otherwise valid financial rows. Irrecoverable CSV quoting errors abort the import without publishing a completed dataset. Manifest, source and artifact integrity are checked before completed data can be reused.

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
- A stale ingest lock from a killed process fails with a message naming the lock path and the recovery step, rather than a bare `FileExistsError`.
- Reimporting the same source identity is idempotent.

## Acceptance criteria
- Two equal account strings at different banks produce different account identities.
- Two identical-valued source payments remain two transactions.
- Source laundering labels are absent from normalized transaction columns.

## Data availability
Supported by IBM transaction exports after schema and source interpretation are verified.

Separately supplied HI-Small_accounts.csv may be preserved by reconcile_publisher_accounts. Its Bank ID strings can differ in zero padding from transaction bank IDs. The output records exact matches, explicit numeric zero-padding candidates, ambiguities and missing links. Synthetic source entity metadata is retained separately and is not inferred from transaction IDs. Publisher pattern files remain evaluation-only.
