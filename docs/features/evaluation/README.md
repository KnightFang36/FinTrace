# Benchmark evaluation

**Status: implementation pending.** Owner: `src/fintrace/evaluation/`.

## Proposed interface
```text
evaluate_benchmark(frozen_detection_run, benchmark_labels, evaluation_policy) -> EvaluationReport
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Reject a run whose detection inputs include benchmark labels.
- Zero denominators return an explicit unavailable value.
- No claim of confirmed mule accuracy is allowed without appropriate independent account labels.

## Acceptance criteria
- Changing labels after freezing detections changes metrics but never findings or priorities.
- Overlapping findings do not inflate the count of flagged transactions.
- Reports include evaluation unit, label coverage, time interval and review-budget definition.

## Data availability
IBM labels support laundering-transaction evaluation, not confirmed mule identification.
