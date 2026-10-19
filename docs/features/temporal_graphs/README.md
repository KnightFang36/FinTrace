# Temporal graph analysis

**Status: core analysis, verified snapshot CLI and bounded PNG visualization implemented.** Independent dated-reference exposure remains pending and disabled. Owner: `src/fintrace/graph/`.

## Implemented interfaces

```python
analyze_graph(transactions, seed_accounts, graph_policy, cutoff, *, dataset_id=None) -> GraphAnalysisResult
build_transaction_graph(transactions, graph_policy, cutoff, *, dataset_id=None) -> nx.MultiDiGraph
build_account_summary(graph, currency) -> nx.DiGraph
find_temporal_paths(graph, seeds, graph_policy) -> (paths, coverage)
find_temporal_cycles(graph, seeds, graph_policy) -> (cycles, coverage)
find_coordinated_groups(graph, graph_policy) -> (groups, coverage)
find_communities(summary, policy) -> dict
compute_metrics(summary, policy) -> dict
run_graph_snapshot(transactions_path, policy_path, cutoff, output_root, *, seed_accounts=()) -> dict
render_graph_png(graph, path, policy) -> dict
```

## Inputs

Inputs are normalized label-free transaction mappings (or revalidated Transaction objects), exact bank/account keys, a complete `config/graph.toml` policy, and a timezone-aware exclusive cutoff. An explicit dataset ID is required for empty in-memory inputs. Snapshot inputs must be completed, checksum-verified detection Parquet artifacts. No evaluation files or supplied pattern annotations are read.

## Outputs

The analysis result retains a transaction MultiDiGraph, shared Finding records and a JSON-serializable artifact. Every transfer has its own transaction-ID edge; self-transfers are counted separately and excluded from movement analysis. Currency-specific account summaries retain exact paid/received totals, counts and transaction IDs separately. Conversion edges stay visible but are excluded from patterns and summaries; no FX rate or exact fund attribution is inferred.

## Functionality and evidence

- Paths use bounded DFS over actual transfer edges, strictly increasing timestamps and one currency. Evidence records ordered transaction IDs/times. Only intermediaries are finding subjects; endpoints remain contextual.
- Cycles first narrow candidates using strongly connected components, then check actual strictly chronological return transfers. Findings report participating accounts, the returning account, initial paid and final received values without claiming the same funds returned.
- Coordination requires an identical participant set of at least three accounts sharing a directed counterparty in a minute bucket, repeated in at least two distinct complete 60-minute windows. Windows/buckets align to the UTC epoch. Partial boundary windows are withheld. Varying participant sets are outside this conservative rule; counterparties alone are not flagged. The policy can change these counts/window sizes within strict bounds.
- Descriptive communities use seeded asynchronous label propagation over an unweighted undirected projection of same-currency account pairs. Directed unweighted sampled betweenness and distinct sender/recipient counts provide context. These algorithms create no findings independently. Context computations exceeding node/edge caps report unavailable.
- Optional dated-reference exposure reports disabled; it never substitutes benchmark annotations for intelligence.

## Errors and edge cases

Input transaction/node overflows raise ValueError rather than sampling. Duplicate conflicting IDs, mixed datasets, labels/unrecognized fields, invalid policies and implicit timezones fail validation. Repeated identical IDs are deduplicated; distinct transaction IDs survive even with identical content.

Explicit seeds constrain path/cycle origins only; they do not filter input edges, coordination or metric scope. Without seeds, origins are ranked by outgoing transfer count, then exact bank/account identity up to `max_seed_accounts`; omitted origins produce truncated coverage. Cycle origins are selected after narrowing to eligible strongly connected components, with an independent seed budget. All requested seeds, missing seeds and actual origins are recorded. Expansion counts include rejected edge candidates. Hop/cycle bounds, per-feature result limits, expansion limits and cooperative wall-clock deadlines bound DFS/group work. Context algorithms use separate hard input-size limits; they are not subject to DFS deadlines. Coverage distinguishes evaluated, truncated, unavailable and disabled. Runtime exhaustion may change partial output across machines; completed persisted artifacts remain checksum-verified and are reused without replacement.

PNG views use a seeded layout and sorted node/edge prefix with separate display limits. Titles show displayed/total counts and partial status. A full display does not imply exhaustive detection or known observation completeness.

## CLI and outputs

```bash
.venv/bin/python scripts/run_graphs.py PATH/transactions.parquet \
  --cutoff 2022-09-02T12:00:00Z \
  --seed BANK_ID ACCOUNT_ID
```

`--seed` may repeat up to the policy limit; omit it for bounded automatic origin selection. `--policy` selects the complete graph policy. Default output is `data/processed/graph_runs/<run_id>/`:

- `graph.json`: source edges, findings, search coverage, descriptive context and source timestamp/observation assumptions.
- `network.png`: bounded relationship visualization.
- `run.json`: dataset/cutoff/policy identity, input hashes, artifact hashes and summary counts.

Existing artifacts are verified before reuse; changed or incomplete outputs fail instead of being overwritten. A malformed `completion.json` inventory is reported by field, for example a `detection_artifacts` entry that is not an object or a missing required file, and the CLI exits with status 2 and no traceback. Rendering is headless; the command keeps its Matplotlib cache under ignored `.cache/`. Generated artifacts stay outside Git. The standalone rule CLI reports graph analysis as separately required rather than pretending it has run.

## Acceptance criteria

A->B at 10:10 followed by B->C at 10:00 is not a chronological path. Equal-minute edges do not establish order. Parallel transfers remain independent edges. A truncated search is visibly partial. Changes in future records do not change earlier cutoff findings. Centrality/community membership cannot create an alert.

Run `.venv/bin/python -m pytest tests/unit/test_temporal_graphs.py tests/integration/test_graph_runner.py -q`. See [the graph snapshot report](../../graph_validation.md) for an actual checked IBM run. All findings are review candidates, not confirmed illicit activity or confirmed mule identities.

Algorithm references: [NetworkX MultiDiGraph](https://networkx.org/documentation/stable/reference/classes/multidigraph.html), [strongly connected components](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.strongly_connected_components.html), [sampled betweenness](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html), [asynchronous label propagation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.label_propagation.asyn_lpa_communities.html).

## Data availability

IBM transaction exports support these observed patterns at source timestamp precision. Independent exposure references are absent; observation completeness remains unknown.
