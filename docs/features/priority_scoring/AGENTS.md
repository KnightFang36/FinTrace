# Explainable priority scoring contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/scoring/`. Fixed-family scoring and immutable priority ledgers are implemented.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
