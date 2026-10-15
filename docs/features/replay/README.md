# Chronological transaction replay

**Status: implementation pending.** Owner: `src/fintrace/replay/`.

## Proposed interface
```text
replay_transactions(dataset, replay_policy, checkpoint=None) -> ReplayResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Changed source hash or configuration invalidates a checkpoint.
- Late events require a documented reject/recompute policy; no silent historical mutation.
- Do not describe historical file replay as a live bank integration.

## Acceptance criteria
- Adding tomorrow's transaction cannot change yesterday's already frozen evidence.
- Interrupted and resumed replay produces the same completed alerts as an uninterrupted run.
- Equal timestamps never become artificial chronological chain evidence.

## Data availability
Core extension after deterministic batch services and persistence exist.
