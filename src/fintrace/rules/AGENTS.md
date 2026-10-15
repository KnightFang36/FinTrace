# Deterministic transaction rules implementation instructions

## Purpose
Own the source service described in `docs/features/transaction_rules/README.md`. Modules are placeholders until implemented.

## Inputs
- Validated, label-free transactions available before the analysis cutoff.
- Versioned rules, known observation intervals and optional verified context.

## Outputs
- Findings with affected account roles, rule measurements, thresholds, transaction IDs and limitations.
- A per-rule coverage result, including disabled, unavailable and evaluated-with-no-finding.

## Functionality
- Evaluate pass-through with an explicitly declared FIFO allocation of observed same-currency inflows; never allocate an inflow more than once within one account/window evaluation.
- Count distinct counterparties for fan-in/out; record each payment separately for frequency.
- Compare bursts with eligible complete historical windows, excluding the active window; reject a zero or unavailable baseline instead of dividing by it.
- Require sufficient prior observation for inactivity indicators; first appearance alone is not reactivation.
- Identify repeated splitting patterns without assuming a legal reporting threshold or proving intentional evasion.

## Module responsibilities
- `engine.py`: Rule eligibility, invocation and finding aggregation.
- `pass_through.py`: FIFO-based observed-inflow forwarding evidence.
- `fan_in.py`: Distinct-sender collection patterns.
- `fan_out.py`: Distinct-recipient dispersal patterns.
- `burst.py`: Fixed-policy transaction-frequency comparison against complete historical windows.
- `dormant_activation.py`: Observed inactivity followed by renewed transaction activity.
- `repeated_splitting.py`: Repeated directed payments and explicitly qualified splitting evidence.
- `cash_out.py`: Optional exit-channel evidence with verified channel mappings.
- `profile_mismatch.py`: Optional activity-versus-profile comparison with verified customer context.
- `known_exposure.py`: Optional independent-reference exposure rule delegated to graph services.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
