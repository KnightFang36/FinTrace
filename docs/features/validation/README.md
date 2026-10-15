# Financial data validation

**Status: financial source-row validation is implemented.** Owner: `src/fintrace/validation/`.

Available: `validate_transaction_fields(fields, *, timezone_policy, timestamp_precision) -> RowValidation`. It accepts only the ten financial fields, excluding the benchmark label. It preserves exact identifier and currency strings, validates positive fixed-point amounts exactly representable by decimal(38,8), rejects ambiguous/nonexistent local times, and returns either a normalized record or field-specific errors. Unmapped payment formats are preserved with a warning. It does not infer account balances or history completeness.

## Proposed interface
```text
validate_transactions(batch, schema_policy, coverage) -> ValidationResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

## Inputs
- Normalized candidate transactions with source references.
- Required schema, amount precision, timestamp policy and observation coverage.

## Outputs
- Accepted transaction batch; quarantine rows with codes and source references.
- Quality report with counts, duplicate-content warnings and eligibility/coverage diagnostics.

## Functionality
- Validate non-empty endpoint IDs, parseable declared timestamps and positive supported amounts.
- Keep paid and received amounts and currencies distinct. Never silently convert currencies or infer fees.
- Report missing/unknown payment formats and duplicate content according to policy.
- Check that analysis requests lie within known observation coverage; preserve legitimate self-transfers.

## Errors and edge cases
- Incompatible file-level schema aborts ingestion; row errors preserve original content in quarantine.
- Unknown coverage is explicit, not interpreted as uninterrupted account history.
- A missing optional field disables dependent features without dropping otherwise valid transactions.

## Acceptance criteria
- An invalid amount yields a quarantined record with its original record number.
- A self-transfer is retained and annotated.
- Accepted plus rejected source-record counts reconcile with the ingested batch.

## Data availability
Required for all imports.
