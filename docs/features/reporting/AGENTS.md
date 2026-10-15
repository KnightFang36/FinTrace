# Evidence reporting and exports contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/reporting/`. Implementation is pending.

## Inputs
- Frozen account/alert/case snapshot, validated export formats and output destination.
- Run identity, policies, evidence transactions and optional graph layout.

## Outputs
- CSV transaction/evidence tables, structured JSON, escaped HTML summary and PNG graphs.
- Manifest with artifact hashes, filters, provenance and limitations.

## Functionality
- Generate explanations from fixed templates and measured evidence values.
- Keep account keys, decimal values, currencies and original source references intact.
- Show synthetic dataset provenance and investigation-only interpretation.
- Produce a reviewable internal case summary, not an automatically filed regulatory report.

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
