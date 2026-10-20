# Service contracts

All services run locally. Inputs must be label-free financial records or explicit analyst actions. Benchmark metrics, independently verified context/screening, general pipeline orchestration and full-history account queries are outside scope. See [setup and commands](../README.md), [shared schemas](data_contracts.md) and [validation records](validation.md).

## Ingestion and validation

`fintrace.ingestion.manifest` provides `inspect_source`, `create_manifest`, `validate_manifest`, `write_manifest`, `load_manifest` and `verify_manifest`. These validate positional headers, provenance and source bytes. `scripts/prepare_data.py` exposes `audit`, `create`, `verify`, `ingest` and `accounts`; use `--help` for required flags. Manifest destinations are immutable.

```python
ingest_ibm(manifest_path, raw_root, processed_root,
           *, batch_size=25000, progress=None) -> dict
validate_transaction_fields(fields, *, timezone_policy, timestamp_precision) -> RowValidation
```

`ingest_ibm` lives in `fintrace.ingestion.ibm`; row validation lives in `fintrace.validation.transactions`. The validator accepts only the ten financial source fields. Invalid rows retain financial source text and issue codes in quarantine; malformed CSV quoting aborts publication. Amounts must fit decimal(38,8) exactly, without rounding. Identical-valued records retain distinct source-row transaction IDs. Self-transfers are retained and annotated.

Completed detection artifacts live in `data/processed/datasets/<dataset_id>/`; label and label-issue artifacts remain separately under `evaluation/<dataset_id>/`. Missing/invalid labels do not reject otherwise valid financial records. Source labels are excluded from transaction hashes and financial quarantine. Completion inventories verify every artifact before reuse. Interrupted imports must not appear complete.

Larger imports hash-partition account and duplicate summaries into 32 scratch partitions under a 512 MB DuckDB budget. Summaries preserve exact bank/account keys, currencies, endpoint roles and timestamps. Scratch partitions disappear before publication. No observation completeness is inferred from file bounds.

`fintrace.ingestion.publisher.reconcile_publisher_accounts` preserves separately supplied synthetic account metadata and reports exact, zero-padding-candidate, ambiguous or missing links. Candidates do not rewrite bank strings or establish independently verified customer identities. Source patterns are structurally audited and kept separate; pattern matching and benchmark metrics are not implemented.

## Transaction rules

```python
evaluate_rules(transactions, history=None, *, policy, cutoff, context=None) -> RuleResult
run_rule_snapshot(transactions_path, policy_path, cutoff, output_root,
                  *, subject_accounts=()) -> dict
```

The engine is `fintrace.rules.engine`; the verified Parquet runner is `fintrace.rules.runner`. Inputs use normalized mappings, exact structured account identities and an exclusive timezone-aware cutoff. Unknown record/context fields are rejected. All money arithmetic uses 60-digit Decimal precision and keeps currencies separate. Self-transfers are excluded from movement indicators.

| Rule | Evidence condition |
| --- | --- |
| Pass-through | Explicit FIFO allocation of observed same-currency inflows to strictly later outflows; allocated inflow is never reused within an account/window. |
| Fan-in | Configured number of distinct sending bank/account pairs in the window. |
| Fan-out | Configured number of distinct receiving bank/account pairs in the window. |
| Repeated splitting | Repeated directed payments meeting the configured count; no legal threshold or intentional evasion is inferred. |
| Burst | Count compared with eligible complete historical windows, excluding the active window; zero/unavailable baseline is unavailable. |
| Dormant activation | Renewed activity after a sufficiently observed inactivity interval; first appearance is insufficient. |

Findings retain subject roles, evidence transaction IDs, measured values, thresholds, currency, policy version and limitations. Coverage distinguishes disabled, unavailable, evaluated and truncated results. Evidence budgets withhold incomplete findings instead of silently discarding their IDs. Historical days use fixed 24-hour UTC offsets.

The runner verifies transaction/quality hashes and label-free schema before scanning and rechecks input integrity before publication. It loads the largest active window, or the declared historical prefix when needed, within explicit input limits. Account scopes are exact. Findings/run metadata publish atomically; existing runs are integrity-verified on reuse. It never opens labels or pattern annotations.

`config/rules.toml` sets the six core rules. Graph entries accept `enabled` only; graph thresholds live in `config/graph.toml`. Legacy disabled cash-out/profile/exposure entries remain readable to preserve existing checkpoint policy bytes; enabling them fails explicitly.

## Temporal graphs

```python
analyze_graph(transactions, seed_accounts, graph_policy, cutoff,
              *, dataset_id=None) -> GraphAnalysisResult
run_graph_snapshot(transactions_path, policy_path, cutoff, output_root,
                   *, seed_accounts=()) -> dict
```

Use `fintrace.graph.engine` and `fintrace.graph.runner`. Every transfer is a distinct directed MultiDiGraph edge. Same-currency account summaries are separate from original evidence. Chains and cycles require strictly increasing timestamps; timestamp ties and structural reachability do not prove temporal transfer paths. Cycles use bounded strongly connected candidates; coordinated groups require explicit repeated timing/counterparty conditions.

Seeds restrict chain/cycle origins, while groups and descriptive metrics retain loaded-window scope. Centrality and community membership alone do not create findings. Input/node overflow fails without sampling. Expansion, seed, path, runtime and result limits disclose incomplete coverage. Independent-reference exposure is unsupported.

The verified snapshot publishes `graph.json`, `network.png` and a completed hash inventory. JSON retains ordered evidence IDs, exact money, currency, cutoff, source policy and budgets. PNG layouts are deterministic and bounded. Empty in-memory graphs require an explicit dataset ID. Corrupt, unrelated or future evidence must fail validation.

## Priorities and alerts

`fintrace.scoring.priority.score_accounts` applies `config/scoring.toml` fixed family weights once per eligible family, suppresses correlated contributions and caps priorities at 100. Scores are review ordering, never probabilities. Missing/unsupported evidence creates no invented contribution. Ledger identity includes policy, window, coverage and eligible findings.

```python
import_analysis(rule_run, graph_run, scoring_policy_path, alert_policy_path,
                database_path, *, actor, at) -> dict
```

`fintrace.alerts.runner` verifies frozen rule/graph artifact hashes, schema/engine versions, dataset, exclusive cutoff, evidence versions and identical input hashes before importing. `graph_run=None` supports explicit rule-only coverage. `scripts/manage_alerts.py` exposes import/list/transition.

`fintrace.storage.alert_store.AlertStore` transactionally persists immutable findings/priorities, stable incidents and append-only events. Incident identity includes dataset, exact subject, family, alert-policy hash and exclusive-window bucket. Repeated imports do not duplicate events. States are open, in_review, escalated and closed; closure requires a reason and reopening is explicit. Writes require actor, timezone-aware time and expected version. Stale/conflicting actions roll back. Store paths must be local `.duckdb` files outside raw/evaluation data.

## Account and network investigation

`fintrace.investigations.dashboard` provides `list_snapshots`, `load_dashboard` and `load_graph_evidence`. Reads use read-only connections and never create a missing store. Frozen evidence is isolated to the selected snapshot; current workflow status/version is identified separately. Catalogs show at most 200 snapshots and disclose omissions. Oversized read models fail visibly.

```python
get_account_dossier(account_key, model, graph=None) -> dict | None
```

`fintrace.investigations.account` returns priority contributions, subject findings, alerts and exact per-currency totals for graph-window transfers touching the exact bank/account pair. Unknown accounts return `None`; missing graphs return no invented totals. Source identifiers, parallel transfers and evidence IDs remain available. The UI displays up to 500 transfer rows with omitted counts. This is observed snapshot history, not a reconstructed balance or complete account history. Customer identities and opening dates remain unavailable.

`fintrace.investigations.network.get_alerted_network_view(graph, model, *, hops=6, direction='both', max_nodes=100, max_edges=150)` is the default combined view. It selects up to ten distinct accounts with open, in-review or escalated alerts, sorted by descending fixed-policy priority with exact bank/account string tie-breaking. It reserves every selected account before fair round-robin neighbour expansion and incident-edge selection. Orange nodes identify ranked accounts; teal nodes are observed counterparties. Scores/ranks and active-alert counts appear in tooltips and a table. Accounts absent from the graph window remain isolated, explicitly marked nodes; no transfers or connections are invented. Fewer than ten eligible subjects returns the available set; an empty set offers single-account exploration. A display budget smaller than the selected set fails. The UI also retains a Single account mode with exact finding highlights.

`fintrace.investigations.network` builds directed neighbourhoods and selected-evidence highlights from verified graph JSON. Hard caps are six hops, 200 nodes and 500 edges; the UI defaults to six hops and up to 100 nodes/150 edges. The top-ten ranked subjects remain the origins; observed neighbourhood expansion fills the available display budget, so smaller connected neighbourhoods show fewer than 100 accounts. Omitted/out-of-window evidence is disclosed. PyVis uses inline resources, escaped labels and a bounded, fixed-seed NetworkX layout computed separately for each connected component, followed by deterministic collision clearance and component packing. Adjacent nodes have at least 280 layout units of separation and all node pairs have at least 180; display physics stays disabled. Explicit node coordinates and disabled browser physics prevent automatic movement; manual dragging, zoom and hover remain available. The graph toolbar provides Full screen/Exit full screen and Fit graph controls; Escape exits browser full screen. The default readable camera centres the highest-ranked subject at 0.7 zoom so auto-fit cannot shrink the longer edges back into clutter. Pan/zoom to explore the 100-account selection; Fit graph provides the complete overview and Readable view returns to the inspection scale. Full-screen resizing preserves the current view rather than auto-fitting it again. The normal canvas is 720 pixels tall. Ordinary transfer strokes are three pixels wide, highlighted evidence is five pixels wide, and arrowheads use a 1.6 scale factor for visibility. The local dark theme applies in both sizes. Neighbourhood reachability is descriptive; only ordered finding paths are temporal evidence.

## Cases

```python
apply_case_action(database, case_id, action, *, actor, at, reason,
                  expected_version, request_id, payload=None) -> dict
read_cases(database, case_id=None, *, version=None) -> dict
```

Use `fintrace.cases.service` and `fintrace.storage.case_store`. Creation uses `case_id=None`, version 0 and payload `{"title": "Review", "snapshot_id": "priorities-...", "alert_ids": ["alert-..."]}`. Other actions: `attach` (snapshot/alerts), `note` (`text`), `assign` (`assignee`), `transition` (`state`, plus `disposition` for closure), and `reopen`. Actor/reason/time/request ID are required; unknown payload fields fail.

Open cases move to investigating or closed; investigating cases may escalate or close; escalated cases may return to investigating or close. Reopening returns a closed case to investigating. Closed cases accept appended correction notes. All previous versions, disposition and audit events remain retained.

Attachments freeze the selected snapshot's evidence. Limits: 1–100 alerts per attachment, 100 attachments and 1,000 versions per case; catalogs show at most 200 cases. No alert state changes merely because it is attached. Case/version/event/request response commit together. Identical retries return the original result; changed arguments with the same request ID, stale versions, unknown evidence and backwards timestamps fail without partial writes.

CLI: `python scripts/manage_cases.py --database PATH list` or `show CASE_ID --version VERSION`. Use `apply ACTION --payload-file JSON_FILE --request-id ID --expected-version VERSION --actor NAME --at TIME --reason TEXT`, with `--case-id` for existing cases.

## Reports

```python
export_evidence(database, processed_root, export_root, *, snapshot_id=None,
                alert_ids=(), case_id=None, case_version=None,
                formats=('json', 'csv', 'html', 'png'), at) -> dict
verify_report(directory) -> dict
report_archive(directory) -> bytes
```

`fintrace.reporting.export` accepts either an existing snapshot/alert selection or an explicit immutable case version. Every report has authoritative `evidence.json` and `manifest.json`; requested formats add transaction/finding CSV, escaped HTML and a bounded PNG. Source hashes, original lineage/timestamps, policy snapshots, filters, counts, exact currency totals and limitations are retained.

Resolve each finding transaction through verified detection-only Parquet, before the cutoff. Missing, duplicate or future evidence and changed source hashes fail publication. Count overlapping evidence transactions once in totals. HTML escapes source/analyst text; CSV neutralizes formula-prefixed/control text. JSON preserves literal source strings. No generated prose is used.

Limits: 10,000 findings, 1,000 alert references, 50,000 distinct evidence transfers; PNG 100 nodes/200 edges; ZIP 100 MiB. Exports stage then publish atomically. Same scope/formats/time verifies and reuses existing output. Reject symlink roots/ancestors, raw/evaluation destinations, unsupported formats and conflicting scope selectors. Reports remain local and are never submitted externally.

CLI: `python scripts/export_reports.py --snapshot ID --at TIME`, or `--case ID --case-version VERSION`. Optional local paths and format selections are available through `--help`.

## Historical replay

```python
replay_transactions(transactions, rule_policy, scoring_policy, alert_policy,
                    output_root, *, start, end, step_minutes, actor, at,
                    graph_policy=None, checkpoint=None, max_steps=None) -> dict
read_checkpoint(path) -> dict
list_replays(output_root) -> dict
```

`fintrace.replay.engine` reuses the existing bounded batch services. The schedule includes start/final exclusive cutoffs: `start <= end <= audit time`. Limits: 100 cutoffs, step 1–1,440 minutes, optional 1–100 steps per invocation, 200 catalog entries. It recomputes bounded snapshots and accumulates alerts in its own store; it is not a live bank integration or an unbounded full-history detector.

Equal-time events become available together at the next eligible cutoff and cannot form ordered chains. Progress counts all available source records; detector windows remain bounded. Checkpoints retain source/policy identities, audit context, watermark, completed artifact/priority references, source ordering key, counts and local timings.

Commit immutable detector artifacts and idempotent alert updates before atomic checkpoint advancement. Resume verifies completed outputs and rejects changed source/policy/audit identities or corrupt checkpoints. Retrying after alert commit but before checkpoint publication adds no duplicate events. Per-run locks reject concurrent work; stale-lock recovery requires confirming the old process has stopped. Failures retain the last completed watermark.

CLI: `python scripts/run_replay.py TRANSACTIONS --start TIME --end TIME --step-minutes 30 --actor NAME --at TIME --max-steps 1`. Repeat identical arguments with `--checkpoint PATH` to resume. CLI graphs are enabled by default; `--no-graph` explicitly requests rules only.

## Dashboard and acceptance checks

`app/streamlit_app.py` routes seven implemented pages. All presentation calls domain services; no labels, detector joins or inferred profiles belong in the UI. Explicit forms/buttons alone change alerts/cases, generate reports or run replay; rerendering does not repeat writes. The dark theme covers Streamlit and embedded graph frames. Authentication and public deployment are outside this local workspace.

The synthetic test suite covers temporal ties/reversal/cutoff isolation, duplicate lineage, exact amounts, distinct bank strings, currency separation, missing coverage, evidence budgets, artifact tampering, score suppression, alert idempotency, case stale-version rollback, safe exports, replay recovery and Streamlit explicit actions. Run `python scripts/check_scaffold.py` and `python -m pytest tests -q` after cross-cutting changes. Missing data must remain unavailable; partial searches must remain visibly partial.
