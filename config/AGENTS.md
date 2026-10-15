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
Demo thresholds are not legal requirements or validated performance. UNSET timezone must block time analysis. Keep optional enrichment/screening disabled without input. Weights remain explicit, not fitted.
