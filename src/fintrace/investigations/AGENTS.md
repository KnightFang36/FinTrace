# Account investigation implementation instructions

## Purpose
Own the source service described in `docs/features/account_investigation/README.md`. Also follow docs/features/network_investigation/README.md for network.py. dashboard.py, account.py and network.py implement snapshot-scoped read models and bounded evidence investigation. Full-history querying and verified profile context remain pending.

## Inputs
- Structured account identity, time range, analysis run and supported filters.
- Label-free transactions, findings, priority snapshots and optional verified context.

## Outputs
- Account summary, incoming/outgoing timeline, counterparties, currency-specific totals and observed activity changes.
- Linked alerts, evidence, coverage limitations and explanations.

## Functionality
- Preserve original evidence references while providing filterable views.
- Display first observed activity distinctly from verified account opening date.
- Explain each priority contribution using measurements and the underlying transactions.
- Use only analysis-run data available at the selected cutoff; disclose filtered and omitted records.

## Module responsibilities
- `account.py`: Account dossier, timeline and traceable finding drill-through.
- `network.py`: Bounded directed neighbourhoods and highlighted graph evidence.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.

Dashboard reads use read-only connections, validated immutable priorities and finding IDs. Later alert evidence is excluded from earlier snapshot read models; current state/version/audit are separately identified as workflow metadata. Account totals are exact per currency within the selected graph window. Neighbourhoods enforce 3-hop/200-node/500-edge hard caps.
