# Case management and audit contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/cases/`. Implementation is pending.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
