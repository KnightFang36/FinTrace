# Explainable priority scoring

**Status: implementation pending.** Owner: `src/fintrace/scoring/`.

## Proposed interface
```text
score_accounts(findings, coverage, scoring_policy, window) -> PriorityResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Unknown rule IDs or families require explicit configuration resolution.
- Reject negative weights, overlapping band boundaries or inconsistent policy versions.
- Optional context findings contribute no score until configured under an explicit policy.

## Acceptance criteria
- Pass-through 25 + collection 15 + temporal-network 30 yields 70/high under demo-v1.
- Fan-in and fan-out together contribute 15, not 30, under the shared family.
- Repeated execution on identical inputs produces identical contribution ordering and score.

## Data availability
Supported without any benchmark labels.
