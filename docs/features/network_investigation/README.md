# Network investigation

**Status: bounded source service and interactive Streamlit/PyVis view implemented.** Owner: `src/fintrace/investigations/`.

## Implemented interface

```python
get_network_view(graph, seed, *, hops=1, direction="both", max_nodes=60,
                 max_edges=150, finding=None) -> dict
```

## Inputs

Verified graph JSON linked to the selected immutable priority snapshot, one exact bank/account seed, direction (incoming/outgoing/both), 1–3 hops, display budgets and an optional selected Finding mapping. `load_graph_evidence` verifies graph artifacts and dataset/cutoff identity before use. No full raw benchmark or evaluation file is opened by the frontend.

## Outputs

Deterministic node IDs, account mappings, directed parallel transaction edges with complete paid/received amounts, currencies, timestamps and references; highlighted selected-finding IDs; source graph counts, missing-seed/partial flags, evidence completeness and display bounds.

## Functionality

Build a NetworkX MultiDiGraph from stored edges. Give selected evidence display precedence, then expand neighbours breadth-first with deterministic IDs. Direction controls neighbour expansion; the induced edges between selected accounts retain both directions as context. Enforce a maximum of 200 nodes/500 edges and preserve parallel IDs. The frontend uses a 40-node/150-edge default and a seeded inline PyVis layout. Orange edges denote selected evidence, not an independent suspicion calculation.

Static full-snapshot PNG generation remains the separate graph CLI capability. Interactive/static exports and general case-report manifests are not added by this page.

## Errors and edge cases

Invalid direction/hop/budget settings fail. Seeds absent from the graph report missing and do not fabricate nodes. Selected evidence outside the graph or display budget sets evidence_complete false. A partial neighbourhood does not alter findings, coverage or priorities. Structural reachability is never presented as a chronological path; only the detector's ordered finding references establish its observed timing pattern.

## Acceptance criteria

Highlighted edges match exact finding transaction IDs. Parallel transfers remain accessible in the table/hover details. Display caps and omitted graph scope are visible. Stable source identities/settings produce stable node IDs and layout seed. Account and transaction text is escaped before embedding; no remote script/style source is needed for the network.

## Data availability

Requires a linked completed temporal graph artifact. Rule-only snapshots show an actionable unavailable state. Source timestamp precision and the limited observation interval remain those declared by the selected graph run.
