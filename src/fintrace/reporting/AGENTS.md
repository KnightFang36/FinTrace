# Evidence reporting and exports implementation instructions

## Purpose
Own the source service described in `docs/features/reporting/README.md`. Modules are placeholders until implemented.

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

## Module responsibilities
- `export.py`: Snapshot exports, fixed evidence templates and artifact manifests.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
