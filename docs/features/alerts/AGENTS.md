# Alert generation and lifecycle contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/alerts/`. Local alert grouping, verified imports, audited transitions and transactional persistence are implemented.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
