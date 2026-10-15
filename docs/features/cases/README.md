# Case management and audit

**Status: implementation pending.** Owner: `src/fintrace/cases/`.

## Proposed interface
```text
apply_case_action(case_id, action, actor, reason, expected_version) -> CaseResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Reject invalid transitions and stale expected versions.
- Unknown alert/evidence IDs cannot be attached silently.
- No automatic submission, external notification or account restriction occurs.

## Acceptance criteria
- Closing a case retains its notes, evidence and previous states.
- A stale update is rejected without overwriting the latest case.
- Reopening creates a new event and preserves the original closure.

## Data availability
Core local workflow; requires persistence. Production authentication is a separate deployment concern.
