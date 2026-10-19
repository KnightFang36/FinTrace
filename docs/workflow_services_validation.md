# Case, report and replay service verification

Versioned cases, local evidence exports and bounded historical replay are implemented in their domain services, CLI commands and the seven-page Streamlit workspace. No machine-learning functionality or new runtime dependency was added. Existing detection, scoring and graph policy files are unchanged.

## Automated checks

The service integration fixtures exercise exact bank/account strings, currency-separated totals, source record lineage and strict cutoff handling. They cover case creation, request idempotency, notes/corrections, assignment, required closure disposition, explicit reopen, immutable previous versions, stale-version rollback and unknown-evidence rejection. Reports are checked for source resolution, HTML escaping, CSV formula neutralization, complete artifact manifests, verified reuse and cleanup after a renderer fails during staged publication.

Replay tests compare uninterrupted execution with both ordinary resume and interruption after alert commit but before checkpoint advancement. Resulting alerts and audit events match without duplication. Graph-enabled replay matches batch findings, equal-time events enter together and cannot form ordered chains, earlier artifacts remain frozen, and changed policy/source bytes or corrupt checkpoints reject resume. Corrupting evaluation labels does not change replay or report results.

Streamlit tests visit the new pages without writes, create a fixture case through an explicit form, generate one local report, and start/continue a replay. Rerenders do not repeat those actions. These write tests use temporary synthetic fixtures, not the uploaded-data investigation store.

## HI-Medium local verification

A report was generated for one existing HI-Medium alert at the exclusive analysis cutoff `2022-09-03T06:00:00Z`. It contains one finding and five resolved evidence transfers, with US Dollar paid and received totals each exactly 1,177.45. Its PNG has three nodes and five edges. JSON, CSV, escaped HTML, PNG and the completed hash manifest remain local under `outputs/`; no report was transmitted.

Report ID: `report-180160b904de9278db509e7f84c9c1e18df00d18dfc182479989f387e8fa6eba`.

A graph-enabled replay at the same cutoff completed in its isolated store, producing the same rule run, graph run and priority snapshot IDs as batch processing: 280 findings, 269 scored accounts and 270 replay-local alerts. Its progress watermark counts 7,737,738 available source records; detection still uses the original bounded two-/three-hour rule/graph windows, not an unbounded full-history scan. Unknown historical coverage and graph search limitations remain visible.

Replay ID: `replay-ff2b240f44127ba6aab1ef6ac6ab2758da3f4b033712e55f1753ad23d035b0d4`. The actual local step measured 62.07375 seconds, including verification and artifact publication; this is not a live-processing latency guarantee. Its checkpoint and separate alert database remain under `data/processed/replays/`.

The ordinary investigation queue is unchanged. No analyst case, note, assignment, closure or reopen was fabricated in the uploaded-data store. Headless Chrome verified the new Cases, Reports and Replay pages without JavaScript errors, checked mobile overflow, and submitted no analyst actions. Generated screenshots/tooling remain local and ignored by Git.

## Usage and remaining scope

Use **Cases**, **Reports** and **Replay** in the workspace sidebar. The [case contract](features/cases/README.md), [report contract](features/reporting/README.md) and [replay contract](features/replay/README.md) provide callable interfaces, CLI examples, budgets and error behavior.

Benchmark evaluation, optional independently verified context/screening and full-history account querying remain pending. Historical replay recomputes the same bounded snapshot services; it does not connect to a live bank. Reports are internal investigation artifacts, not regulatory submissions. Production authentication remains a separate deployment concern.
