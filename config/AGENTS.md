# config instructions

## Purpose
Maintain explicit versioned TOML policies for application limits, rules and fixed priority weights.

## Inputs
Reviewed demonstration thresholds, graph budgets, source interpretation and enabled capability choices.

## Outputs
app.toml, rules.toml and scoring.toml consumed by future services.

## Functionality
app.toml controls storage, graph limits and timestamp policy. rules.toml defines eligibility/windows/thresholds for the six core rules; its graph-rule and optional-rule sections accept `enabled` alone, because those thresholds live in graph.toml or are not implemented yet. scoring.toml defines capped rule families and bands. Changes must be recorded with analysis runs.

## Constraints
data-requirements.txt pins the verified data/graph/test environment. frontend-requirements.txt extends it with the verified Streamlit/PyVis runtime stack; no predictive dependencies are included. Update it from an actually verified environment, not guessed version numbers.

Demo thresholds are not legal requirements or validated performance. UNSET timezone must block time analysis. Keep optional enrichment/screening disabled without input. Weights remain explicit, not fitted.

graph.toml is the strict implemented temporal graph policy: input/node limits fail instead of sampling; seed, traversal, result and visualization limits disclose partial coverage. Centrality/community computations have separate conservative size caps.

scoring.toml is consumed by the strict fixed-family priority implementation; alerts.toml versions incident-window grouping and the minimum priority required to create a review record. Alert policy changes create distinct incident identities. No weights are fitted.
