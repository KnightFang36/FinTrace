# Temporal graph analysis contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/graph/`. Implementation is pending.

## Inputs
- Validated label-free transfers, account keys, explicit time interval and currency policy.
- Search limits, seed accounts, timestamp-tie policy and algorithm configuration.

## Outputs
- Transaction MultiDiGraph, aggregated account graphs, descriptive metrics and candidate communities.
- Chronological path/cycle/group findings, exact edge references and search-completeness metadata.

## Functionality
- Retain every transaction as a separate directed edge; use aggregation only for summaries.
- Use strongly connected components to narrow cycle candidates; verify each returned cycle against actual chronological transfers.
- Find bounded forward paths with strictly increasing source timestamps; source order alone does not establish order for tied times.
- Return community membership and degree/betweenness as context; a central or highly connected account is not independently suspicious.
- Detect coordinated groups only when explicit repeated timing/counterparty criteria are satisfied.

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
