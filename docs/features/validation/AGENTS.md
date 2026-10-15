# Financial data validation contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/validation/`. Implementation is pending.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
