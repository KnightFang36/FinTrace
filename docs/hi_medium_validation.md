# HI-Medium local dataset

The user supplied the HI-Medium transaction and account CSVs and pasted pattern annotations on 19 October 2026. Files remain local and excluded from Git. HI-Medium is imported independently of HI-Small; the earlier dataset, snapshots and analyst history are preserved. This report records measured local checks, not independent publisher authentication or benchmark accuracy.

## Source audit

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| HI-Medium_Trans.csv | 3,031,783,420 | 3126afb8155e7c8815d62bc5370549a7b5ae6bf7dfe872b3cd7813e66a3d7ff5 |
| HI-Medium_accounts.csv | 145,008,642 | 0fb441d31df9ca0868803eebce718b7e85a4e385334222427c400a5ba64475f9 |
| HI-Medium_Pattern.txt | 2,279,574 | d612cd7ed6f7761c0e36f3b788dfbae68aa0842c77145b192c777c22daba5c9f |

The transaction CSV has the expected eleven positional columns, including the two Account columns, and 31,898,238 records with no wrong-width rows. The five-column publisher account table has 2,087,786 records with no malformed rows in the source audit. There are seven payment formats and fifteen payment currencies.

Observed source timestamp strings range from `2022/09/01 00:00` through `2022/09/28 15:58`. These bounds do not establish complete historical coverage. The manifest retains UTC as the earlier explicit project convention, minute precision, unknown acquisition time and unknown observation coverage. Acquisition-specific terms were not supplied; the recorded license statement is inherited from the existing project provenance declaration.

The pasted text is preserved byte-for-byte as HI-Medium_Pattern.txt. Structural auditing found 2,756 starts, 2,756 ends, 22,743 annotated transfer rows and no malformed blocks. These are publisher-style benchmark annotations, not detector findings or instructions. Matching them to transactions and calculating benchmark performance remain pending. Neither labels nor pattern text feed detection, graph analysis, priorities or ordinary investigation views.

## Local workflow

Dataset ID: `ibm-36acee4d7cbbcb860c86c84a7b6016c37548a43188dd0823eb9211e43ca6a12a`.

The source manifest and audit are `data/raw/ibm/manifest-hi-medium.json` and `data/raw/ibm/upload-audit-hi-medium.json`. See [the HI-Medium workflow](../data/README.md#selecting-hi-medium) for creation commands. Existing destinations must not be overwritten. Repeat verification/normalization uses:

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

## Investigation snapshot

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

Full-file ingestion does not imply full-history detection. Layering coverage is truncated by the seed-search budget and the UI discloses that limit. Burst/dormancy history remains unavailable because observation coverage is unknown; optional independent exposure remains disabled. Counts describe review evidence and priorities, not confirmed criminal activity or benchmark accuracy. The original four investigation pages remain implemented. Versioned cases, general local report exports and checkpointed historical replay were subsequently implemented and verified in the [workflow service report](workflow_services_validation.md). Benchmark evaluation, full-history account querying and optional context/screening remain pending.

## Regression checks

The implementation passed 158 tests and 46 subtests, including ingestion, exact amounts, lineage, currency and temporal boundaries, label isolation, graph budgets, priorities, audited alert storage and Streamlit views. The scaffold checker also passed. No machine-learning functionality or new runtime dependency was added. Rule thresholds, scoring weights and graph budgets remain unchanged.

The first normalization attempt validated all source financial rows, then failed during account aggregation at the existing 512 MB DuckDB limit. Atomic publication correctly removed the incomplete artifacts. The importer now uses 32 scratch partitions for larger account and duplicate summaries while retaining that memory budget. A regression check compares the partitioned and original summaries, including exact bank strings, currency sets, timestamps, endpoint roles and duplicate counts. A separate generated scale check completed in 26.97 seconds with 3,000,000 input rows, 2,100,000 exact account keys and 900,000 duplicate-content rows. This verifies aggregation capacity on that fixture, not full-dataset performance or detection accuracy.
