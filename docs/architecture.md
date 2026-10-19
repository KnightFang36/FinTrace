# Architecture

## Status and execution boundary
Data ingestion/validation and deterministic cutoff rule snapshots are implemented. Temporal graph analysis and bounded PNG rendering are implemented through scripts/run_graphs.py. Fixed-policy priorities and transactional alert persistence are implemented through scripts/manage_alerts.py. Snapshot-scoped account/network read models and the seven-page Streamlit workspace are implemented. Case services use transactional version/audit storage; reports resolve verified financial rows and publish locally; historical cutoff replay uses isolated alerts and durable checkpoints. General orchestration, full-history account querying and benchmark evaluation remain pending. scripts/run_rules.py is the working rule CLI.

## Layers
1. Ingestion verifies source headers and provenance; validation separates acceptable records from quarantine.
2. Storage exposes normalized tables and immutable run-scoped evidence snapshots.
3. Rules and temporal graph services consume only transactions available at an explicit analysis cutoff.
4. Priority scoring accounts for each eligible rule family once; alerts reference findings and score contributions.
5. Investigation, cases and reporting use service read models, never independent dashboard calculations.
6. Evaluation joins frozen outputs with separately stored benchmark labels after detection.
7. Replay invokes the same detection services against increasing event cutoffs.

## Dependency direction
`app -> investigations/cases/reporting -> alerts/scoring -> rules/graph/context -> storage/contracts`.

Ingestion writes normalized records and a physically separate benchmark-label artifact. Evaluation may read both artifacts. Rules, graphs, context, scoring, alerts, investigations and replay must never read benchmark labels. Keep raw labels out of ordinary storage queries and dashboard data.

contracts.py defines exact account/transaction records, findings, feature coverage and rule results. rules/engine.py evaluates six core rules and explicit capability gates; rules/runner.py verifies and projects completed detection Parquet before publishing snapshot artifacts. pipeline.py remains reserved for later combined orchestration. All deterministic operations use stable ordering and reproducible identifiers.

## Storage and identity
Use Parquet for normalized datasets and DuckDB for local queryable evidence and case tables. Source data is immutable. Dataset versions are content-addressed by source hashes plus normalization configuration. Derive stable transaction IDs from dataset ID, relative source-file identity and source record number; do not hash only the transfer values, because identical-valued payments can be separate events.

Account identity is the structured pair of source bank and account strings. In serializations, encode it unambiguously as a JSON array or dedicated fields; do not concatenate with an ambiguous delimiter.

## Time, value and observation coverage
Every run declares a cutoff, timestamp precision, timezone policy, window boundaries and source coverage. Default windows are half-open `[start, end)`. Calendar horizons use the declared analysis timezone. Preserve source precision: a stable row order resolves display/replay ordering, but does not prove temporal order between equal timestamps.

The implemented rule runner is a cutoff snapshot, not a full-history scan. Historical comparison days are explicitly fixed 24-hour UTC offsets, rather than local calendar-day arithmetic. Burst windows cannot exceed that offset. Equal-time inflows cannot fund equal-time outflows under the FIFO pass-through policy.

Use Decimal or declared scaled integers for money. A decimal string is the external representation. Preserve amount paid and amount received with their respective currencies. Do not treat a difference as a fee without supporting data.

Historical comparisons require complete prior observation intervals. A source file's minimum timestamp alone does not establish coverage. Record known gaps and source-boundary limitations. No activity before an account's first observation is not evidence of dormancy.

## Graph execution
Keep an account MultiDiGraph with a distinct keyed edge per transfer. Build a separate account DiGraph for currency-specific summaries and bounded topology analysis. Graph outputs retain mappings to contributing transaction IDs. Structural algorithms nominate candidates; temporal validation produces evidence.

Apply depth, edge, expansion and runtime budgets before unbounded exploration. Results state whether they are complete, truncated, skipped or unavailable. Charts use deterministic layouts and bounded neighbourhoods; graph statistics are descriptive context rather than standalone crime conclusions.

## Optional context
External entity links and reference intelligence carry provenance, effective dates and observed-at dates. Use only information available at the cutoff. Sanctions/PEP candidate screening is independent from transaction-pattern detection and is disabled by default.

## Audit and analyst actions
Persist run ID, dataset hash, configuration hash, software version, cutoff and coverage with outputs. Case actions append actor, timestamp, previous state, new state and reason. Corrections append events rather than erasing history. Investigator review never automatically changes configured thresholds.
