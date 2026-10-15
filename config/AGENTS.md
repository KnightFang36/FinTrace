# config instructions

## Purpose
Maintain explicit versioned TOML policies for application limits, rules and fixed priority weights.

## Inputs
Reviewed demonstration thresholds, graph budgets, source interpretation and enabled capability choices.

## Outputs
app.toml, rules.toml and scoring.toml consumed by future services.

## Functionality
app.toml controls storage, graph limits and timestamp policy. rules.toml defines eligibility/windows/thresholds. scoring.toml defines capped rule families and bands. Changes must be recorded with analysis runs.

## Constraints
data-requirements.txt pins the data/test environment verified for this branch. It does not install the unimplemented dashboard stack and contains no excluded predictive dependencies. Update it from an actually verified environment, not guessed version numbers.

Demo thresholds are not legal requirements or validated performance. UNSET timezone must block time analysis. Keep optional enrichment/screening disabled without input. Weights remain explicit, not fitted.
