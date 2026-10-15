# Checked priority and alert snapshot

The verified IBM HI-Small rule and graph runs at exclusive cutoff `2022-09-02T12:00:00Z` were imported into the local DuckDB alert store. Both runs declare the same input transaction and quality hashes. The detector outputs were verified before scoring; no labels or supplied pattern annotations were opened. IBM data is synthetic.

| Measure | Checked result |
| --- | --- |
| Rule findings | 244 |
| Graph findings | 169 |
| Accounts with explicit finding subject roles | 279 |
| Priorities by band | 226 low; 53 medium; 0 high; 0 critical |
| Local review alerts | 287 |
| Initial audit events | 287 creation events |
| Repeat import | 0 changed alerts; 0 appended events; 287 unchanged incidents |
| Retained state | All open, version 1; no analyst decisions fabricated |

The fixed scoring policy applies each evidence family once per account, preserving correlated findings as suppressed contributions. Alerts group by dataset, account, family, versioned incident policy and final analysis-window bucket. Accounts may have multiple family incidents, so alert counts differ from account counts.

Every alert's transaction-ID union was independently reconciled to its retained findings. Each finding explicitly names the alert subject. All retained priority IDs resolve to matching account ledgers, and every capped score matches its contribution sum. Each incident has exactly one creation event after repeat import. Fixture tests additionally cover changed evidence, retained earlier scores, stale updates, legal close/reopen actions, corrupted snapshots/databases, recomputed-hash arithmetic tampering and complete transaction rollback on interrupted imports.

Priority snapshot: `priorities-eb02f9dd4fb5295299b643ca68761542ae34067fb409d21b9b5a55cc83e1a8c3`.

Source rules: `rules-80b9cff57faaa73d5f0d409e94fa8157c52ee0725a6e0f883e3b30e5554d61c8`.

Source graphs: `graphs-4f7ae249aae6eddeb9a4a23bd66eaf2fb80e349f50623d85349ff76506298146`.

The local store is `data/processed/alerts.duckdb`; database contents and generated outputs remain ignored by Git. No external notification, account restriction or regulatory filing was performed. Lifecycle transitions were tested only with handcrafted fixtures.

This is review prioritization, not a crime probability, an accuracy result or confirmed mule identification. Unknown historical coverage and limited graph-origin searches remain visible in retained priority coverage. Alert first/last observed fields represent finding analysis-window bounds, not exact first/last transfer times. See [rules](rule_validation.md), [graphs](graph_validation.md), [scoring](features/priority_scoring/README.md) and [alerts](features/alerts/README.md) for the policy and limits.

Final verification: 133 tests and 31 subtests passed. Scaffold checks passed for 49 required directories, 15 feature contracts, 89 Python files, TOML and local links. Git whitespace checks passed separately.
