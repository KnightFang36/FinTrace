# Chronological transaction replay implementation instructions

## Purpose
Own the source service described in `docs/features/replay/README.md`. Modules are placeholders until implemented.

## Inputs
- Validated transactions ordered by event time and stable source identity.
- Explicit watermark, timestamp-tie handling, rule/configuration version and checkpoint.

## Outputs
- Incremental findings, priorities and alerts; replay progress and resumable checkpoints.
- Run-level latency measurements, coverage and deterministic event-processing statistics.

## Functionality
- Invoke the same rule and graph services as batch processing using only available records.
- Process equal-timestamp events as a declared group; do not infer within-group transfer ordering.
- Persist state before advancing a checkpoint; resume without duplicate alerts.
- Carry source/context observed-at restrictions through every historical cutoff.

## Module responsibilities
- `engine.py`: Cutoff-isolated chronological replay and resumable checkpoints.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
