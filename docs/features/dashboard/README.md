# Streamlit investigation dashboard

**Status: overview, alert review, account evidence and interactive network pages implemented.** Cases, general report exports, evaluation and replay remain pending and are not routed as working pages. Owner: `app/`.

## Implemented interface

Run `.venv/bin/python -m streamlit run app/streamlit_app.py` from the repository root after installing `config/frontend-requirements.txt`.

The app reads service models through `fintrace.investigations.dashboard`. Financial calculations, snapshot isolation, repository reads and network expansion live in source services. Presentation modules live under `app/views/`; `app/components/` contains labels, coverage tables and bounded PyVis rendering. `.streamlit/config.toml` defines the local theme and disables usage telemetry.

## Inputs

An existing local `data/processed/alerts.duckdb` populated by `scripts/manage_alerts.py import`, immutable priority snapshots and the optional graph run linked by the selected snapshot. `FINTRACE_PROCESSED_ROOT` and `FINTRACE_ALERT_DATABASE` may select alternate local fixture/workspace paths. No datasets are downloaded, imported or analyzed automatically. The dashboard never opens benchmark labels or supplied pattern annotations.

## Outputs

- Overview: actual account, alert and finding totals, fixed-priority bands, evidence-family counts, highest-priority accounts and coverage.
- Alert review: account/alert search, status/family/band/currency filters, exact evidence IDs, measurements, thresholds, contribution ledgers and current audit history. Reference lists show at most 200 IDs with a complete selected-finding JSON download.
- Account evidence: subject findings, score contributions, explicit missing-context state and optional exact currency-specific totals/timeline from the selected graph window.
- Network explorer: directed bounded neighbourhoods, selected-finding edge highlights, parallel transfer references, source-window identity and visible omitted scope.

All pages label IBM data as synthetic. Cutoff, scoring policy and snapshot identity remain accessible in the sidebar. Finding windows are exclusive at the end. Date/time scope is selected through the snapshot selector rather than an invented full-history date filter.

## Functionality

Dashboard reads use read-only DuckDB connections. Findings and scores come only from the selected immutable snapshot. Alerts may have accumulated later evidence in storage; the read model restricts IDs/transactions/scores to the selected snapshot before display. Workflow state/version and audit history are explicitly current and may postdate the analysis cutoff. Refreshing clears cached read models; normal reads create no database and perform no writes.

Review transitions require an explicit form submission, reviewer, reason and expected version. Closing follows the implemented review lifecycle; reopening additionally requires an explicit checkbox. Writes delegate to AlertStore and append an audit event. Rerenders do not resubmit the action. The local app does not provide authentication or multi-user hosting; the reviewer text is an audit identifier, not a verified login.

The network panel uses inline PyVis resources, escaped account/transaction labels and a deterministic layout seed. Default display is 40 nodes/150 edges; controls permit 10–100 nodes and 1–3 hops. Source service hard limits are 200 nodes/500 edges. Structural reachability is not temporal transfer evidence. Highlighted edges identify selected evidence, with an explicit warning when references lie outside the graph or exceed display limits. No evaluation ground truth appears in these pages.

## Errors and edge cases

A missing/empty store shows setup instructions and no fabricated metrics; reads never create it. Missing graph evidence leaves rule findings available. Corrupt snapshots or graph artifacts fail visibly; a graph run directory that is absent under the processed root raises a `ValueError` that names the remedy, not a raw filesystem error. Table/timeline/network display limits are disclosed. The catalog is limited to 200 snapshots; oversized models fail rather than silently sample (10,000 accounts, 20,000 findings/alerts, 250 MiB graph artifact). Snapshot lists use a bounded ID prefix before sorting by cutoff; this is not a promise to show the latest 200 of a larger catalog. A paginated repository is required beyond these limits.

Changed review versions fail rather than overwrite another action. Cache TTLs are 30 seconds for dashboard models and 60 seconds for graph evidence; explicit refresh or successful writes clear them. No workflow action is run on behalf of an investigator during normal rendering.

## Acceptance criteria

Displayed totals reconcile to stored service outputs. Snapshot selection cannot expose later finding IDs or scores. Missing historical/graph coverage is displayed as unavailable/truncated, not zero suspicious activity. Filters produce explicit empty states. Review submissions require fields and append one event; rerender adds none. Parallel graph transfers remain individually accessible. External strings cannot inject HTML/scripts into the embedded graph.

## Data availability

The checked local IBM workspace contains 279 scored accounts, 287 alerts and 413 findings at cutoff `2022-09-02T12:00:00Z`. These are snapshot counts, not hardcoded UI values or confirmed crime counts. See [frontend validation](../../frontend_validation.md), [account view](../account_investigation/README.md) and [network view](../network_investigation/README.md).
