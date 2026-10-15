# Financial data validation

**Status: implementation pending.** Owner: `src/fintrace/validation/`.

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
