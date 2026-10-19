# Checked Streamlit frontend

The current workspace also contains the verified HI-Medium snapshot at exclusive cutoff `2022-09-03T06:00:00Z`: 269 scored accounts, 270 review alerts and 280 findings. Its graph source has 83,047 account nodes and 94,774 non-self transfer edges. The previous HI-Small snapshot below remains available. See [HI-Medium verification](hi_medium_validation.md) for ingestion, policies, scope and limitations.

The workspace now uses the dark operations theme, including metrics, widgets, tables, captions and a matching dark PyVis canvas. All 158 tests and 46 subtests passed, including all four Streamlit routes and graph isolation/limits. Headless Chrome verified the dark overview, alert review, account evidence and live network canvas without JavaScript errors; screenshots were inspected locally. The current default seed renders three nodes and eight edges, graph zoom responds, displayed overview totals match the stored HI-Medium snapshot, and the 390px mobile page has no horizontal overflow. Browser checks do not submit analyst review actions.

The Streamlit workspace was verified against isolated handcrafted test stores and the existing local IBM synthetic workspace. Default reads use read-only DuckDB connections; no dataset or source-label files are opened by the UI. Browser checks did not submit any review action against the uploaded-data workspace.

The actual local snapshot displays 279 scored accounts, 287 review alerts and 413 findings, matching the imported service outputs. Pages include overview, filtered alert review with evidence and priority ledgers, account evidence/graph-window transfers, and a bounded interactive network explorer. The live browser network canvas rendered 39 accounts and 76 transfer edges for the default seed, with the 78,002-account/90,140-edge graph scope visibly disclosed.

Automated checks cover:

- Missing database shows setup instructions and creates no database or fake metrics.
- Immutable snapshot selection excludes later finding IDs, transaction IDs and scores while identifying current workflow state separately.
- Queue filters, missing-graph account/network states and actual displayed totals.
- Review forms require an explicit actor/reason and submit one version-checked transition; rerender appends no duplicate event. These writes use isolated fixtures only.
- Exact per-currency totals, different bank/account identities, parallel graph transfers, directional expansion, display caps, missing seeds and evidence highlight completeness.
- Escaped account/transaction labels and inline graph resources with no remote script/style source.

Streamlit AppTest exercised all four routes. Headless Chromium loaded the actual overview, alert table and PyVis canvas without JavaScript errors. Desktop screenshots were inspected locally; a fresh 390px mobile viewport was checked for responsive layout. Temporary screenshots/browser tooling are not source artifacts and are not committed.

The earlier HI-Small frontend check passed with 142 tests and 31 subtests; the latest suite count is recorded above. Structural/documentation checks run separately. Runtime frontend versions are pinned in `config/frontend-requirements.txt`; browser tooling is optional and excluded from runtime pins.

Limits remain explicit: snapshot-only investigation, graph-window totals, current rather than historical workflow status, bounded catalog/tables/graph, and no verified customer context. The local app has no authentication or public deployment configuration. Versioned cases, verified local reports and checkpointed replay are implemented on separate pages; benchmark evaluation remains pending. Selected finding JSON downloads are evidence copies, not regulatory reports.

Start with `.venv/bin/python -m streamlit run app/streamlit_app.py` after following [the dashboard setup](features/dashboard/README.md).


## Case, report and replay extension

The seven-page workspace now includes versioned case management, verified local report downloads and isolated historical replay with progress/resume. The full suite passed 171 tests and 46 subtests. New Streamlit fixture checks cover explicit case creation, report generation, replay start/continue and no repeated writes on rerender. Headless Chrome verified the three new pages and mobile layout without JavaScript errors; browser checks submitted no analyst actions. See [workflow service verification](workflow_services_validation.md) for source resolution, export safety, checkpoint recovery and measured HI-Medium checks. Earlier counts above describe the initial four-page verification.
