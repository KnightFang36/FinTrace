# Evidence reporting and exports

**Status: implemented verified local exports, CLI and Streamlit Reports page.** Owner: `src/fintrace/reporting/export.py`.

## Implemented interface

```python
export_evidence(database, processed_root, export_root, *, snapshot_id=None,
                alert_ids=(), case_id=None, case_version=None,
                formats=('json', 'csv', 'html', 'png'), at) -> dict
verify_report(directory) -> dict
report_archive(directory) -> bytes
```

Select either a priority snapshot (optionally specific alert IDs; empty selects all its alerts) or an explicit immutable case version. Example: `export_evidence(db, processed, exports, snapshot_id=priority_id, formats=('json', 'csv'), at=audit_time)`.

CLI: `python scripts/export_reports.py --snapshot PRIORITY_ID --at TIME_WITH_OFFSET`, or `--case CASE_ID --case-version VERSION`. Optional `--database`, `--processed-root`, `--output-root`, repeated `--alert`, and `--formats json csv html png` choose the local scope. The Reports page generates artifacts only after an explicit button click and offers a verified ZIP download.

## Inputs

Frozen snapshot/alert scope or case version, completed label-free source datasets, supported formats and configured local export root. Audit time must include an offset and must not precede the analysis or selected case version. No benchmark label/pattern file is opened.

## Outputs

Every completed report contains authoritative `evidence.json` and `manifest.json`. Requested CSV adds `transactions.csv` and `findings.csv`; HTML adds `summary.html`; PNG adds `network.png`. JSON retains bank/account strings, exact decimal strings, currencies, original timestamp text, source-file hashes and source-record numbers. The manifest records artifact hashes, source hashes, policy snapshots, selected filters, coverage, currency-separated totals, counts, export time, case version and limitations.

## Functionality

Resolve every finding's transaction IDs by scanning only verified detection-facing Parquet. Validate source inventory/schema/dataset identity and source hashes before and after export; reject missing, duplicate or future evidence. Include earlier baseline evidence where findings reference it. Totals count each distinct evidence transaction once, with separate paid/received amounts and counts per currency, using exact decimal arithmetic.

Fixed headings and measured findings provide the narrative; no generated prose or machine learning is used. Case exports retain the exact selected version and captured attachments. HTML escapes all source/analyst text. CSV quotes cells and prefixes potentially executable formula/control-character text with an apostrophe; JSON is authoritative for literal source values and does not rely on spreadsheet type inference.

Limits: 10,000 findings, 1,000 alert references and 50,000 distinct evidence transfers per report. PNG uses a deterministic layout with at most 100 nodes/200 edges and discloses omitted scope. Browser ZIP downloads have a 100 MiB artifact budget; larger completed artifacts remain local. Export writes stage in a temporary directory and publish a complete manifest by atomic directory rename. Repeating the same scope, formats and export instant verifies/reuses the completed report.

## Errors and edge cases

Reject unsupported/empty formats, conflicting scope selectors, absent source transactions, corrupted evidence/artifacts, future evidence and exceeded budgets. Generated report IDs fix artifact paths beneath the export root; symlink roots/ancestors and raw/evaluation destinations are rejected. Failed exports do not publish a completed directory. Export time and current alert workflow metadata may postdate evidence cutoff and are labelled separately. Reports are local internal artifacts; they are never transmitted or automatically filed.

## Acceptance criteria

Every exported finding resolves to financial source records with lineage and timestamps before its cutoff. Totals reconcile exactly by currency. HTML/CSV injection fixtures remain inert. Changed source/report bytes fail verification, and interrupted exports do not appear complete. Historical case exports cannot acquire later notes or evidence.

## Data availability

Uses implemented snapshots, case versions and completed IBM detection artifacts. Does not require independent customer profiles or benchmark evaluation.
