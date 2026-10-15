# Checked temporal graph snapshot

The uploaded IBM HI-Small detection-only Parquet was analyzed at the exclusive cutoff `2022-09-02T12:00:00Z`, using the versioned 180-minute policy in `config/graph.toml`. No benchmark labels or pattern annotations were opened. IBM data is synthetic.

| Measure | Checked value |
| --- | --- |
| Input transfers | 92,028 |
| Excluded self-transfers | 1,888 |
| Transaction graph | 78,002 accounts; 90,140 directed transfer edges |
| Layering findings | 166 strictly chronological chains |
| Circular-flow findings | 3 strictly chronological return paths |
| Coordinated-group findings | 0 under the repeated identical-participant-set rule |
| Total findings | 169 review candidates |
| Layering coverage | Truncated: 20 origins ranked by outgoing transfer count, 12,117 examined edge candidates |
| Cycle coverage | Evaluated over eligible SCC origins, 12 examined edge candidates, with configured length/window bounds |
| Coordination coverage | Evaluated, 260,160 work steps |
| Reference exposure | Disabled; independent dated intelligence is absent |
| PNG view | Partial: 100/78,002 accounts; 15/90,140 edges |

Every returned path/cycle was independently reconciled to the graph's source edges: IDs, endpoint continuity, strict timestamp order, same currency and exclusion of cutoff/future transfers. The fixture suite also tests reverse-time paths, equal timestamps, parallel edges, exact totals, per-feature budget coverage, source/output corruption and unreadable evaluation artifacts.

This is a bounded snapshot, not an exhaustive whole-dataset scan. Structural cycles do not imply temporal return flows; descriptive communities/centrality do not create findings. Graph context computations above their independent size caps are marked unavailable, per currency. Source timestamps use the explicitly recorded UTC project convention and minute precision; source observation completeness remains unknown. Findings do not prove criminal intent, exact money provenance or confirmed mule status.

Run identity: `graphs-4f7ae249aae6eddeb9a4a23bd66eaf2fb80e349f50623d85349ff76506298146`.

Policy SHA-256: `70bcb4a670881708af3877a76ddbadf61516d23c6c0a34f0e48ed509778c4809`.

Graph JSON SHA-256: `9d27d4ad513f24fe203b70e2e055e761fde69affce5f93d3324b83a5b384054d`.

PNG SHA-256: `1952f262e48833ae35e3be1469c65ddf99c6515c80d70ef927ed294d2d8e80ad`.

The 109-test suite and 31 subtests passed before publication. The scaffold checker validates maintained folder instructions, feature contracts, Python syntax, TOML and local documentation links separately. Dataset and generated artifacts remain ignored by Git.

Repeat with the command in [the graph feature workflow](features/temporal_graphs/README.md); the run directory is under `data/processed/graph_runs/`. Existing completed outputs must pass checksum verification before reuse. Wall-clock exhaustion can produce machine-dependent partial outputs; persisted evidence is retained unchanged.
