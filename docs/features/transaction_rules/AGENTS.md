# Deterministic transaction rules contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/rules/`. Implementation is pending.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
