# Case management and audit implementation instructions

## Purpose
Own the source service described in `docs/features/cases/README.md`. The feature service is implemented; keep its callable interface and limits synchronized with the feature contract.

## Inputs
- Selected alerts/evidence snapshots, analyst notes, assignment and explicit actions.
- Expected record version for concurrency checks.

## Outputs
- Persisted cases, notes, assignment/disposition history and immutable audit events.
- Links to source runs, accounts, alerts and report snapshots.

## Functionality
- Support open, investigating, escalated and closed cases; require an explicit audited reopen.
- Group alerts across related accounts without declaring each participant a suspect.
- Require actor identity and rationale for transitions and disposition.
- Append corrections and notes; keep prior evidence snapshots accessible.

## Module responsibilities
- `service.py`: Version-checked case actions and append-only audit history.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.

Case actions require request IDs and expected versions; identical requests reuse the stored response. Storage is owned by storage/case_store.py; catalog/history reads must not create tables. Attachments project immutable snapshot evidence, not the mutable latest alert evidence.
