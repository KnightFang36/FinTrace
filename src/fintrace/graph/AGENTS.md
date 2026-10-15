# Temporal graph analysis implementation instructions

## Purpose
Own the source service described in `docs/features/temporal_graphs/README.md`. Modules are placeholders until implemented.

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

## Module responsibilities
- `builder.py`: Directed transaction MultiDiGraph and currency-specific account summaries.
- `temporal_paths.py`: Bounded strictly chronological multi-hop transfer paths.
- `cycles.py`: Bounded chronological circular-transfer evidence.
- `communities.py`: Descriptive account communities with declared projection and deterministic settings.
- `metrics.py`: Descriptive connectivity, volume and approximate centrality metrics.
- `coordinated_groups.py`: Explicit repeated-window and shared-counterparty group criteria.
- `exposure.py`: Directional temporal exposure to independent dated reference intelligence.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
