# Local validation records

Historical measurements from local verification. These are evidence counts and operational checks, not benchmark accuracy claims. The current regression suite must be rerun after code changes.


## Checked IBM HI-Small data snapshot

### Scope and status

The uploaded files were audited locally on 16 October 2026 in Asia/Kolkata (15 October in UTC). The complete transaction file was normalized successfully. A repeat import verified the source and every completed artifact checksum and returned reused. Publisher-account preservation and reconciliation also completed and passed verified reuse.

This report contains aggregate validation facts and source hashes, not transaction records. Actual source files, manifests, Parquet, quarantine and generated reports remain local and ignored by Git. No suspicious-account detector has been run.

### Uploaded source identity

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| HI-Small_Trans.csv | 475,664,283 | b19d39f515523373f991b689c07e11e7b0b95c17a2c27a87d91584ae16c5b040 |
| HI-Small_accounts.csv | 34,053,187 | 786808526e33cfc441212dd6fccda7edfc24172149bed59c6ef59b186836b014 |
| Pattern.txt | 323,844 | 2c546b5ce6009e73851f0139af053cf845f08bf92f3bc82fe1eb937dec2ef39b |

All original source hashes were checked again after processing and remained unchanged. These checks establish local file continuity, not independent publisher authenticity.

### Transaction validation

| Measurement | Result |
| --- | ---: |
| Source transaction records | 5,078,345 |
| Accepted normalized transactions | 5,078,345 |
| Quarantined financial records | 0 |
| Wrong-width source records in upload audit | 0 |
| Duplicate financial-content records, retained separately | 9 |
| Self-transfers, retained without asserting suspicion | 591,212 |
| Distinct observed (bank_id, account_id) keys | 515,088 |
| Payment formats | 7 |
| Payment currencies | 15 |

The observed source timestamp bounds are 2022/09/01 00:00 through 2022/09/18 16:18, with minute precision. These bounds do not establish complete observation coverage.

Monetary columns are exact decimal(38,8). Account and bank strings preserve their source formatting, including leading zeros. Transaction IDs retain source-record uniqueness even for duplicate-content payments. Normalized records retain source timestamp text, precision, source file identity and record number.

### Provenance declarations

- Dataset ID: ibm-d09512cc782ac4059163288737a35b3a948ab93d31888fb8da9c6c342b86cde4.
- Ingestion run: ingest-a3c8a7de57bc5df2bff20961.
- Manifest schema: version 2; acquisition time is unknown/null.
- Timezone: UTC as an explicit project convention, not an assertion about IBM's source timezone.
- Observation coverage: unknown; history-dependent rules must not assume an uninterrupted historical interval.
- Terms: the publisher repository identifies CDLA-Sharing-1.0; acquisition-specific terms were not separately supplied.

### Evaluation-only data

All 5,078,345 source labels were valid binary values. The separate evaluation artifact contains 5,073,168 transactions labelled 0 and 5,177 labelled 1. There were no benchmark-label errors.

These are synthetic transaction laundering labels, not detected alerts and not confirmed mule-account labels. They are stored outside detection-facing transaction/account artifacts and are never passed to financial validation or publisher-account reconciliation.

Pattern.txt contains 370 balanced laundering-attempt blocks and 3,209 annotated transfer rows. Structural auditing found no malformed blocks. Pattern matching and benchmark metrics are outside the maintained scope.

### Publisher account metadata

The supplied entity table has 518,581 records, with no malformed source rows and no publisher-row quarantine in this run.

Each of the 515,088 observed account keys has one numeric zero-padding link candidate to the publisher table. This run produced no exact-string key matches, ambiguous links or unmatched observed keys. For example, bank strings can be 010 versus 10; both values remain in the candidate ledger. No candidate is automatically applied to rewrite a transaction account identity.

Synthetic entity IDs/names are preserved as publisher metadata. They do not establish real customer identity, verified ownership, expected income, or source of wealth.

Supplemental snapshot ID: b013e9f42e2fac65065de99cfb8b347aa1f2a6a2f02158e644c61feee90694f5.

### Local artifacts and repeatable commands

Detection-facing artifacts are under data/processed/datasets/<dataset_id>/. Benchmark labels are under data/processed/evaluation/<dataset_id>/. Supplemental entity/link artifacts are under data/processed/supplemental/<snapshot_id>/.

```bash
.venv/bin/python scripts/prepare_data.py verify data/raw/ibm/manifest.json
.venv/bin/python scripts/prepare_data.py ingest data/raw/ibm/manifest.json
.venv/bin/python scripts/prepare_data.py accounts \
  data/processed/datasets/ibm-d09512cc782ac4059163288737a35b3a948ab93d31888fb8da9c6c342b86cde4/accounts.parquet

.venv/bin/python -m pytest tests -q
python3 scripts/check_scaffold.py
```

Verification passed with 48 tests and 21 subtests, plus Python syntax, folder instruction, TOML and local-link checks. Tests use handcrafted temporary fixtures. The full real-shaped benchmark run separately exercised file scale, artifact publication and verified reuse.

Account aggregation and publisher reconciliation both completed using a 512 MB DuckDB memory budget. That is a database execution budget, not a guarantee that total Python-process memory remains below 512 MB.

### Remaining scope

This historical report verifies the data preparation boundary. The later sections record the implemented graph, priority, dashboard and workflow checks. Independent reference intelligence and complete-history declarations are not fabricated.

## HI-Medium local dataset

The user supplied the HI-Medium transaction and account CSVs and pasted pattern annotations on 19 October 2026. Files remain local and excluded from Git. HI-Medium is imported independently of HI-Small; the earlier dataset, snapshots and analyst history are preserved. This report records measured local checks, not independent publisher authentication or benchmark accuracy.

### Source audit

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| HI-Medium_Trans.csv | 3,031,783,420 | 3126afb8155e7c8815d62bc5370549a7b5ae6bf7dfe872b3cd7813e66a3d7ff5 |
| HI-Medium_accounts.csv | 145,008,642 | 0fb441d31df9ca0868803eebce718b7e85a4e385334222427c400a5ba64475f9 |
| HI-Medium_Pattern.txt | 2,279,574 | d612cd7ed6f7761c0e36f3b788dfbae68aa0842c77145b192c777c22daba5c9f |

The transaction CSV has the expected eleven positional columns, including the two Account columns, and 31,898,238 records with no wrong-width rows. The five-column publisher account table has 2,087,786 records with no malformed rows in the source audit. There are seven payment formats and fifteen payment currencies.

Observed source timestamp strings range from `2022/09/01 00:00` through `2022/09/28 15:58`. These bounds do not establish complete historical coverage. The manifest retains UTC as the earlier explicit project convention, minute precision, unknown acquisition time and unknown observation coverage. Acquisition-specific terms were not supplied; the recorded license statement is inherited from the existing project provenance declaration.

The pasted text is preserved byte-for-byte as HI-Medium_Pattern.txt. Structural auditing found 2,756 starts, 2,756 ends, 22,743 annotated transfer rows and no malformed blocks. These are publisher-style benchmark annotations, not detector findings or instructions. Pattern matching and benchmark metrics are outside the maintained scope. Neither labels nor pattern text feed detection, graph analysis, priorities or ordinary investigation views.

### Local workflow

Dataset ID: `ibm-36acee4d7cbbcb860c86c84a7b6016c37548a43188dd0823eb9211e43ca6a12a`.

The source manifest and audit are `data/raw/ibm/manifest-hi-medium.json` and `data/raw/ibm/upload-audit-hi-medium.json`. See [the main data workflow](../README.md#local-data-workflow) for commands. Existing destinations must not be overwritten. Repeat verification/normalization uses:

```bash
.venv/bin/python scripts/prepare_data.py verify data/raw/ibm/manifest-hi-medium.json
.venv/bin/python scripts/prepare_data.py ingest data/raw/ibm/manifest-hi-medium.json
.venv/bin/python scripts/prepare_data.py accounts \
  data/processed/datasets/ibm-36acee4d7cbbcb860c86c84a7b6016c37548a43188dd0823eb9211e43ca6a12a/accounts.parquet \
  --source HI-Medium_accounts.csv
```

Normalization and checksum-verified repeat import completed. All 31,898,238 financial rows were accepted, with zero quarantine entries and no validation issues. The observed registry contains 2,077,023 exact bank/account keys. All 20 duplicate-content rows and 2,561,860 self-transfers were retained. Monetary amounts remain decimal(38,8), separated by currency. Benchmark labels remain in the separate evaluation artifact; all 31,898,238 labels have valid binary values and no label issues were recorded.

Publisher reconciliation preserved all 2,087,786 supplied account rows without quarantine. Every observed account has one zero-padding review candidate; there are no exact-string, ambiguous or unmatched links in this run. No candidate rewrites transaction identities. Supplemental snapshot: `1b860803c53d5395b72dbc6f15b75113e40a7da3af56da4766ddd9a9bcda6e2b`.

The interrupted import had closed complete transaction/label Parquet files before finalization. One-time local recovery checked all four schemas, row counts, sequential source record numbers and dataset/file/run identity, reverified the source manifest, ran the normal summaries and published the normal completion/checksum inventories. The ordinary ingest command subsequently verified every artifact and returned `reused`. This recovery is not a general checkpoint/resume API.

### Investigation snapshot

The existing rules, graph, scoring and alert policies were retained. At the previous cutoff (2 September at 12:00 UTC), the three-hour graph window would contain 370,646 transactions, exceeding the unchanged 250,000 input budget. The new exclusive cutoff is `2022-09-03T06:00:00Z`, chosen to fit the existing budgets without sampling. The rules load 64,351 rows over their two-hour input interval; the graph loads 96,687 rows over three hours and retains 83,047 nodes and 94,774 non-self edges.

| Output | Count |
| --- | ---: |
| Fan-in findings | 46 |
| Fan-out findings | 15 |
| Observed pass-through findings | 5 |
| Repeated-payment findings | 188 |
| Ordered layering findings | 22 |
| Circular-flow findings | 4 |
| Total findings | 280 |
| Scored accounts | 269 |
| Review alerts | 270 |

The latest priority snapshot is `priorities-1168dfe76b4760448d795269102d71fb34b9cebe1c5b762d1a14fcb176c70f3c`. The rules run is `rules-e4f794a7b38ae02cde692d8331c7d29d781812e514cd9dcc92e5291fb44ac34e`; the graph run is `graphs-c0d1ad9343f65ab902af575bb0d39a97583dade27a6386ad77874dd9390c1b89`. The existing HI-Small priority snapshot remains readable, and the combined local store has 557 alerts across both datasets.

Full-file ingestion does not imply full-history detection. Layering coverage is truncated by the seed-search budget and the UI discloses that limit. Burst/dormancy history remains unavailable because observation coverage is unknown; optional independent exposure remains disabled. Counts describe review evidence and priorities, not confirmed criminal activity or benchmark accuracy. The original four investigation pages remain implemented. Versioned cases, general local report exports and checkpointed historical replay were subsequently implemented and verified in the [workflow service report](#case-report-and-replay-service-verification). Benchmark metrics, full-history account querying and independent context/screening are outside the maintained scope.

### Regression checks

The implementation passed 158 tests and 46 subtests, including ingestion, exact amounts, lineage, currency and temporal boundaries, label isolation, graph budgets, priorities, audited alert storage and Streamlit views. The scaffold checker also passed. No machine-learning functionality or new runtime dependency was added. Rule thresholds, scoring weights and graph budgets remain unchanged.

The first normalization attempt validated all source financial rows, then failed during account aggregation at the existing 512 MB DuckDB limit. Atomic publication correctly removed the incomplete artifacts. The importer now uses 32 scratch partitions for larger account and duplicate summaries while retaining that memory budget. A regression check compares the partitioned and original summaries, including exact bank strings, currency sets, timestamps, endpoint roles and duplicate counts. A separate generated scale check completed in 26.97 seconds with 3,000,000 input rows, 2,100,000 exact account keys and 900,000 duplicate-content rows. This verifies aggregation capacity on that fixture, not full-dataset performance or detection accuracy.

## Checked Streamlit frontend

The current workspace also contains the verified HI-Medium snapshot at exclusive cutoff `2022-09-03T06:00:00Z`: 269 scored accounts, 270 review alerts and 280 findings. Its graph source has 83,047 account nodes and 94,774 non-self transfer edges. The previous HI-Small snapshot below remains available. See [HI-Medium verification](#hi-medium-local-dataset) for ingestion, policies, scope and limitations.

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

Limits remain explicit: snapshot-only investigation, graph-window totals, current rather than historical workflow status, bounded catalog/tables/graph, and no verified customer context. The local app has no authentication or public deployment configuration. Versioned cases, verified local reports and checkpointed replay are implemented on separate pages; benchmark metrics are outside scope. Selected finding JSON downloads are evidence copies, not regulatory reports.

Start with `.venv/bin/python -m streamlit run app/streamlit_app.py` after following [the main setup guide](../README.md#run-locally).


### Case, report and replay extension

The seven-page workspace now includes versioned case management, verified local report downloads and isolated historical replay with progress/resume. The full suite passed 171 tests and 46 subtests. New Streamlit fixture checks cover explicit case creation, report generation, replay start/continue and no repeated writes on rerender. Headless Chrome verified the three new pages and mobile layout without JavaScript errors; browser checks submitted no analyst actions. See [workflow service verification](#case-report-and-replay-service-verification) for source resolution, export safety, checkpoint recovery and measured HI-Medium checks. Earlier counts above describe the initial four-page verification.

## Case, report and replay service verification

Versioned cases, local evidence exports and bounded historical replay are implemented in their domain services, CLI commands and the seven-page Streamlit workspace. No machine-learning functionality or new runtime dependency was added. Existing detection, scoring and graph policy files are unchanged.

### Automated checks

The service integration fixtures exercise exact bank/account strings, currency-separated totals, source record lineage and strict cutoff handling. They cover case creation, request idempotency, notes/corrections, assignment, required closure disposition, explicit reopen, immutable previous versions, stale-version rollback and unknown-evidence rejection. Reports are checked for source resolution, HTML escaping, CSV formula neutralization, complete artifact manifests, verified reuse and cleanup after a renderer fails during staged publication.

Replay tests compare uninterrupted execution with both ordinary resume and interruption after alert commit but before checkpoint advancement. Resulting alerts and audit events match without duplication. Graph-enabled replay matches batch findings, equal-time events enter together and cannot form ordered chains, earlier artifacts remain frozen, and changed policy/source bytes or corrupt checkpoints reject resume. Corrupting evaluation labels does not change replay or report results.

Streamlit tests visit the new pages without writes, create a fixture case through an explicit form, generate one local report, and start/continue a replay. Rerenders do not repeat those actions. These write tests use temporary synthetic fixtures, not the uploaded-data investigation store.

### HI-Medium local verification

A report was generated for one existing HI-Medium alert at the exclusive analysis cutoff `2022-09-03T06:00:00Z`. It contains one finding and five resolved evidence transfers, with US Dollar paid and received totals each exactly 1,177.45. Its PNG has three nodes and five edges. JSON, CSV, escaped HTML, PNG and the completed hash manifest remain local under `outputs/`; no report was transmitted.

Report ID: `report-180160b904de9278db509e7f84c9c1e18df00d18dfc182479989f387e8fa6eba`.

A graph-enabled replay at the same cutoff completed in its isolated store, producing the same rule run, graph run and priority snapshot IDs as batch processing: 280 findings, 269 scored accounts and 270 replay-local alerts. Its progress watermark counts 7,737,738 available source records; detection still uses the original bounded two-/three-hour rule/graph windows, not an unbounded full-history scan. Unknown historical coverage and graph search limitations remain visible.

Replay ID: `replay-ff2b240f44127ba6aab1ef6ac6ab2758da3f4b033712e55f1753ad23d035b0d4`. The actual local step measured 62.07375 seconds, including verification and artifact publication; this is not a live-processing latency guarantee. Its checkpoint and separate alert database remain under `data/processed/replays/`.

The ordinary investigation queue is unchanged. No analyst case, note, assignment, closure or reopen was fabricated in the uploaded-data store. Headless Chrome verified the new Cases, Reports and Replay pages without JavaScript errors, checked mobile overflow, and submitted no analyst actions. Generated screenshots/tooling remain local and ignored by Git.

### Usage and remaining scope

Use **Cases**, **Reports** and **Replay** in the workspace sidebar. The [service contracts](services.md) provide callable interfaces, CLI examples, budgets and error behavior.

Benchmark metrics, independent context/screening and full-history account querying are outside scope. Historical replay recomputes the same bounded snapshot services; it does not connect to a live bank. Reports are internal investigation artifacts, not regulatory submissions. Production authentication remains a separate deployment concern.

## Repository cleanup verification

The cleanup removed unfinished evaluation/context/screening, optional detector and general pipeline/repository scaffolds. The seven-page workspace and implemented domain services remain. There is one root instruction file and one root README; contracts and verification records are consolidated in this directory. All source datasets, normalized artifacts, stores, reports and replay checkpoints were left untouched.

The full regression suite passed **171 tests and 46 subtests** after cleanup. Structure checks passed for 23 maintained directories, six documents and 85 Python files, including TOML policy/dependency checks and local links. Disabled legacy optional policy sections remain loadable; attempting to enable a removed service fails explicitly. Existing policy file bytes were not changed.

## Default top-ten alerted-account network

The network explorer now defaults to the ten highest-priority distinct accounts with active alerts, together with observed graph-window counterparties. Orange nodes mark ranked accounts; teal nodes mark counterparties. Selection uses fixed-policy priority with deterministic exact bank/account ties, never laundering labels. Single-account exploration and finding highlights remain available. Missing-window subjects remain isolated and explicitly identified; no transfers are invented.

Read-only HI-Medium verification returned ten ranked accounts, 23 displayed accounts and 36 observed transfers within the unchanged display budgets, with no ranked subject missing from the selected window. The full regression suite passed 175 tests and 46 subtests, including new ranking, duplicate-alert, missing-window, bank-identity, fair-expansion, budget, ordering and default-route checks. Structure/link checks passed. No datasets, policy weights or analyst records were changed.

Headless Chrome verified that the live default graph renders ten ranked subjects, 23 nodes and 36 edges, and that switching to Single account and back succeeds without JavaScript errors. No analyst action was submitted. Preview screenshots remain local and ignored by Git.

## Stable graph layout and full-screen controls

NetworkX now computes bounded node coordinates once with a fixed seed. Browser physics and dynamic edge simulation are disabled, preventing idle wobble while retaining manual dragging, panning, zoom and tooltips. The graph toolbar offers Full screen, Exit full screen and Fit graph; Escape exits the expanded view. Resizing and fitting preserve node coordinates.

Eighteen focused investigation/UI tests passed, including input-order-independent coordinates. Headless Chrome verified unchanged idle positions, disabled physics, native full-screen enlargement from 1,140 × 560 to 1,600 × 1,052 pixels, fit without node movement, button/keyboard exit and no JavaScript errors. Structure/link checks passed. Screenshots remain ignored local artifacts. No financial data, detection policy or analyst records were modified.

## Larger network defaults and transfer visibility

The explorer and investigation services now default to six structural neighbourhood hops and up to 100 displayed accounts. The top ten active-alert subjects remain origins. The UI retains its 150-transfer limit; service hard caps remain 200 nodes/500 edges, with a six-hop maximum. Display size is a limit, not a promise to fabricate additional accounts in smaller neighbourhoods. Detector temporal-path policies and financial records are unchanged.

Transfer strokes are three pixels wide, highlighted evidence is five pixels wide and arrowheads have scale factor 1.6. Nineteen focused tests passed, including six-hop boundary/budget checks and default UI values. Chrome verified the live HI-Medium default renders 100 accounts and 150 transfers, larger arrows, stable coordinates, full-screen/fit/exit/Escape controls and no JavaScript errors. Structure/link checks passed. The bounded-view notice continues to disclose omitted graph scope.
