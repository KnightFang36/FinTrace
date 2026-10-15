# Benchmark evaluation implementation instructions

## Purpose
Own the source service described in `docs/features/evaluation/README.md`. Modules are placeholders until implemented.

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

## Module responsibilities
- `benchmark.py`: Post-detection joining of frozen evidence with isolated benchmark labels.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service's detection dependencies; evaluation alone may join them after detection. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
