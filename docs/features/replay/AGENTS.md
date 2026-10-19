# Chronological transaction replay contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/replay/`. The local service, CLI and workspace integration are implemented.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
