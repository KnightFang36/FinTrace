# Financial data validation implementation instructions

## Purpose
Own the source service described in `docs/features/validation/README.md`. Financial source-row validation is implemented in transactions.py; complete analysis-window eligibility remains a later service concern. Keep the benchmark label outside the validator's inputs.

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

## Module responsibilities
- `transactions.py`: Financial record validation, quarantine and quality reporting.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
