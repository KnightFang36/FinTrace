# Evidence reporting and exports

**Status: implementation pending.** Owner: `src/fintrace/reporting/`.

## Proposed interface
```text
export_evidence(snapshot_id, formats, export_policy) -> ReportManifest
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Escape untrusted HTML and neutralize spreadsheet formula-prefixed text.
- Reject unsupported formats and path traversal outside the configured export root.
- Export failures identify partial artifacts; no incomplete manifest is marked complete.

## Acceptance criteria
- Every exported finding resolves to its source transactions.
- Exported totals match the frozen snapshot by currency.
- Text beginning with spreadsheet formula characters is safely represented.

## Data availability
Core feature; formats and safeguards are planned, not implemented.
