# Temporal graph analysis

**Status: implementation pending.** Owner: `src/fintrace/graph/`.

## Proposed interface
```text
analyze_graph(transactions, seed_accounts, graph_policy, cutoff) -> GraphAnalysisResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Apply maximum hop, cycle length, edge, expansion and runtime budgets; return truncation metadata on exhaustion.
- A structural path failing chronological validation cannot appear as layering evidence.
- Currency transitions require explicit treatment; no inferred conversion or exact provenance claims.

## Acceptance criteria
- A->B at 10:10 and B->C at 10:00 is not a chronological A->C chain.
- Parallel A->B transfers survive graph construction independently.
- A bounded interrupted search is visibly partial, never reported as exhaustive.

## Data availability
Supported by IBM transaction exports; granularity is limited by source timestamp precision.

## Algorithm and function contracts

| Proposed function | Inputs | Functionality | Outputs |
| --- | --- | --- | --- |
| build_transaction_graph | Transactions, interval, currency policy | NetworkX MultiDiGraph keyed by transaction ID | Directed parallel edges and lineage |
| build_account_summary | Transaction graph, currency | Aggregate compatible values and counts per account pair | DiGraph with contributing edge IDs |
| find_temporal_paths | Seeds, graph, 180-minute horizon, 3–4 hops, budgets | Expand only strictly increasing times and compatible currency paths | Ordered layering evidence; no automatic amount attribution |
| find_temporal_cycles | Graph, 2–5 edge cycle bound, 180-minute horizon | Narrow candidates using strongly connected components; validate chronological return paths | Cycle transfers, return account/value, search completeness |
| find_communities | Selected account summary and explicit algorithm settings | Deterministic descriptive community detection with declared directed-to-undirected projection | Membership and method metadata; no automatic alert |
| compute_metrics | Bounded graph, approximation policy | Distinct degree, volume, component membership and approximate betweenness | Context metrics with units and approximation metadata |
| find_coordinated_groups | Candidate accounts, transactions, comparable windows | Require at least 3 accounts in at least 2 distinct non-overlapping 60-minute windows that share directed counterparties and all transact in the same declared minute bucket | Participants, repeated windows, shared counterparties and synchronization evidence |
| find_known_exposure | Independent dated intelligence, graph, direction/hop policy | Trace observed incoming/outgoing links with timing and reference availability checks | Directional exposure paths with provenance; disabled without references |

Candidate ranking and incomplete searches must be recorded. Returning some cycles does not prove no other cycles exist. If the supported NetworkX version cannot enforce a requested bound directly, implement bounded exploration rather than materializing all simple cycles.
