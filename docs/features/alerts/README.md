# Alert generation and lifecycle

**Status: implementation pending.** Owner: `src/fintrace/alerts/`.

## Proposed interface
```text
build_alerts(findings, priorities, existing_alerts, alert_policy) -> AlertChanges
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Repeated runs do not create duplicate alerts for the same incident.
- Illegal transitions or closing without a reason fail validation.
- A context-only centrality measure cannot create an alert without a configured eligible finding.

## Acceptance criteria
- The same analysis imported twice creates one alert and no duplicate evidence.
- New evidence for an existing incident appends an event.
- An alert explanation can be reconciled against its transaction IDs and score ledger.

## Data availability
Core feature; requires implemented findings, scoring and persistence.
