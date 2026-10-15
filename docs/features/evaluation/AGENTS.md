# Benchmark evaluation contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/evaluation/`. Implementation is pending.

## Inputs
- Frozen rule/graph outputs and alert priorities.
- Separately loaded IBM transaction laundering labels, optional source pattern annotations and declared matching policy.

## Outputs
- Transaction-level precision, recall and false-positive counts; optional explicitly named endpoint-participation metrics.
- Per-rule coverage, alerts per review budget, recall/precision at fixed review counts and rule-only versus graph-enhanced comparisons.

## Functionality
- Join ground truth only after detection is frozen; disclose unlabelled or unmatched records.
- Declare how finding evidence maps to flagged transactions before calculating counts.
- Keep transaction laundering evaluation distinct from confirmed mule-account evaluation.
- Use a fixed policy on a later chronological period for final reporting; disclose any earlier manual threshold adjustments.
- Count overlapping findings once per transaction in aggregate metrics; report unavailable features separately.

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
