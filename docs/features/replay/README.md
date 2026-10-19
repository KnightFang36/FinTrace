# Chronological transaction replay

**Status: implemented bounded historical cutoff replay, isolated alert persistence, checkpoint/resume, CLI and Streamlit progress workspace.** Owner: `src/fintrace/replay/engine.py`.

## Implemented interface

```python
replay_transactions(transactions, rule_policy, scoring_policy, alert_policy,
                    output_root, *, start, end, step_minutes, actor, at,
                    graph_policy=None, checkpoint=None, max_steps=None) -> dict
read_checkpoint(path) -> dict
list_replays(output_root) -> dict
```

Example: run from `start='2022-09-03T06:00:00Z'` to `end='2022-09-03T07:00:00Z'` with `step_minutes=30` and `max_steps=1`, then repeat with the returned `checkpoint.json` and identical input/policy/audit arguments. There are at most 100 scheduled cutoffs, including the final endpoint; a shorter final step is allowed. Steps are 1–1,440 minutes. `max_steps` (1–100) limits one invocation without discarding progress.

CLI: `python scripts/run_replay.py TRANSACTIONS --start START_WITH_OFFSET --end END_WITH_OFFSET --step-minutes 30 --actor OPERATOR --at AUDIT_TIME_WITH_OFFSET --max-steps 1`. Reuse those arguments with `--checkpoint PATH` to resume. Graphs are enabled by default in the CLI; `--no-graph` explicitly produces rule-only coverage. Policy/output paths are selectable. The Replay page starts a run or processes one more cutoff per explicit action.

## Inputs

A completed immutable financial dataset, explicit inclusive schedule of exclusive watermarks, fixed rule/graph/scoring/alert policy files, operator, actual audit instant and optional checkpoint. `start <= end <= audit time` is required. The same existing batch rule/graph runners are called at every cutoff; their transaction/node/search budgets remain in force.

## Outputs

Immutable rule/graph runs, incremental deduplicated priorities/alerts in a separate replay-local `alerts.duckdb`, per-cutoff counts and measured local elapsed seconds, and atomic checksummed checkpoints. Checkpoints retain dataset/configuration/engine identity, audit context, source/policy hashes, watermark, cumulative source-record count, last event ordering key and completed run/priority identities. The first step counts all source records before its watermark; later steps count records newly available since the previous watermark.

## Functionality

Events are made available by event time at ordered exclusive cutoffs. All equal-time events enter together at the next eligible cutoff; underlying temporal algorithms continue to require strictly increasing transfer times. Source file/record identity and transaction ID define stable ordering for the progress watermark, never fabricated transfer order.

Replay recomputes the existing bounded batch windows and accumulates audited alerts across those windows; it is not a new fitted detector or a live bank integration. Unknown complete-history coverage remains unknown. Optional independently dated context is still unavailable. Replay alerts are isolated from the ordinary investigation queue; the UI can inspect the frozen summary/alerts for each replay step.

Commit detector artifacts and idempotent alert updates before advancing the checkpoint. Resume verifies identity, policy/source bytes, completed detector inventories and priority hashes. If interrupted after alert commit but before checkpoint advancement, rerunning the step reuses its immutable artifacts and imports no duplicate incident/event. Earlier frozen steps are not overwritten by later cutoffs.

## Errors and edge cases

Changed inputs, late source additions, policy bytes, audit context or unsupported engine versions reject checkpoint resume rather than silently changing history. Use a new run for changed data/configuration; original frozen outputs remain retained. Corrupt checkpoints/detector artifacts/priorities fail visibly. A per-replay lock rejects concurrent execution; after a killed process, confirm it has stopped before removing the named stale lock. A failed step leaves the prior watermark intact. Oversized input windows fail without sampling. Replay catalog reads create no directories and are bounded to 200 runs.

## Acceptance criteria

Graph-enabled replay matches batch evidence at the same cutoff. Equal timestamps never become artificial chronological chains. Interrupted/resumed and uninterrupted runs produce the same logical alerts and audit events. Invalid policy/source changes cannot resume an old checkpoint. Repeated completed replay adds no events. Evidence before a watermark stays unchanged after later steps.

## Data availability

Requires the implemented deterministic batch services and completed local data. Benchmark labels and pattern annotations are not inputs. Event time is the declared availability model for this historical simulation, not a claim about real-world observation or live arrival timestamps.
