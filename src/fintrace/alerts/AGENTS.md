# Alert generation and lifecycle implementation instructions

## Purpose
Own the source service described in `docs/features/alerts/README.md`. engine.py and runner.py implement local review incidents, verified imports and audited lifecycle; the Streamlit review UI is implemented, and cases retain frozen alert references through the separate case service.

## Inputs
- Findings, priority snapshots, explicit grouping policy and persisted alert history.
- Analyst status transitions with actor, timestamp and reason.

## Outputs
- New/updated alerts, explanation text, linked evidence and append-only lifecycle events.
- Deduplication statistics and unresolved linkage diagnostics.

## Functionality
- Create stable deduplication keys from dataset, subject, rule family and policy-defined incident window.
- Merge overlapping evidence without hiding new transaction IDs or replacing prior score snapshots.
- Use measured-value templates for explanations; expose rule, window, threshold and limitations.
- Support open, in_review, escalated and closed states with audited explicit reopen actions.

## Module responsibilities
- `engine.py`: Evidence-backed alert deduplication, grouping and lifecycle changes.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.

runner.py consumes checksum-verified rule and optional graph run directories sharing dataset/cutoff/input identity. Alert incident buckets align to the epoch and contain the last instant of the finding analysis window. Closed alerts retain new evidence without implicit reopening. Audit actor/time are explicit; every transition needs reason and expected version.
