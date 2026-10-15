# Explainable priority scoring implementation instructions

## Purpose
Own the source service described in `docs/features/priority_scoring/README.md`. Modules are placeholders until implemented.

## Inputs
- Evidence-backed findings with subject roles and versioned fixed scoring policy.
- Per-feature coverage, scoring time window and account identities.

## Outputs
- Integer priority from 0 to 100, configured band and full contribution ledger.
- Suppressed correlated findings, missing coverage and referenced policy version.

## Functionality
- For each account/window, select at most one configured contribution per evidence family.
- Sum eligible family weights and cap at 100; use only the role assigned by the finding, not every neighbouring account.
- Retain all findings for review even when their score contribution is suppressed.
- Report the score as investigation priority. Do not turn incomplete coverage into a clean-account statement.

## Module responsibilities
- `priority.py`: Fixed-family contribution ledger and capped account priority.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
