# Checked IBM HI-Small data snapshot

## Scope and status

The uploaded files were audited locally on 16 October 2026 in Asia/Kolkata (15 October in UTC). The complete transaction file was normalized successfully. A repeat import verified the source and every completed artifact checksum and returned reused. Publisher-account preservation and reconciliation also completed and passed verified reuse.

This report contains aggregate validation facts and source hashes, not transaction records. Actual source files, manifests, Parquet, quarantine and generated reports remain local and ignored by Git. No suspicious-account detector has been run.

## Uploaded source identity

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| HI-Small_Trans.csv | 475,664,283 | b19d39f515523373f991b689c07e11e7b0b95c17a2c27a87d91584ae16c5b040 |
| HI-Small_accounts.csv | 34,053,187 | 786808526e33cfc441212dd6fccda7edfc24172149bed59c6ef59b186836b014 |
| Pattern.txt | 323,844 | 2c546b5ce6009e73851f0139af053cf845f08bf92f3bc82fe1eb937dec2ef39b |

All original source hashes were checked again after processing and remained unchanged. These checks establish local file continuity, not independent publisher authenticity.

## Transaction validation

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

## Provenance declarations

- Dataset ID: ibm-d09512cc782ac4059163288737a35b3a948ab93d31888fb8da9c6c342b86cde4.
- Ingestion run: ingest-a3c8a7de57bc5df2bff20961.
- Manifest schema: version 2; acquisition time is unknown/null.
- Timezone: UTC as an explicit project convention, not an assertion about IBM's source timezone.
- Observation coverage: unknown; history-dependent rules must not assume an uninterrupted historical interval.
- Terms: the publisher repository identifies CDLA-Sharing-1.0; acquisition-specific terms were not separately supplied.

## Evaluation-only data

All 5,078,345 source labels were valid binary values. The separate evaluation artifact contains 5,073,168 transactions labelled 0 and 5,177 labelled 1. There were no benchmark-label errors.

These are synthetic transaction laundering labels, not detected alerts and not confirmed mule-account labels. They are stored outside detection-facing transaction/account artifacts and are never passed to financial validation or publisher-account reconciliation.

Pattern.txt contains 370 balanced laundering-attempt blocks and 3,209 annotated transfer rows. Structural auditing found no malformed blocks. Pattern-to-transaction benchmark matching remains future evaluation work.

## Publisher account metadata

The supplied entity table has 518,581 records, with no malformed source rows and no publisher-row quarantine in this run.

Each of the 515,088 observed account keys has one numeric zero-padding link candidate to the publisher table. This run produced no exact-string key matches, ambiguous links or unmatched observed keys. For example, bank strings can be 010 versus 10; both values remain in the candidate ledger. No candidate is automatically applied to rewrite a transaction account identity.

Synthetic entity IDs/names are preserved as publisher metadata. They do not establish real customer identity, verified ownership, expected income, or source of wealth.

Supplemental snapshot ID: b013e9f42e2fac65065de99cfb8b347aa1f2a6a2f02158e644c61feee90694f5.

## Local artifacts and repeatable commands

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

## Remaining scope

The data preparation boundary is implemented. Rule/graph detection, account priorities, alert/case services, investigation dashboards, report exports and benchmark detector evaluation remain pending. Optional reference intelligence and complete-history declarations are not fabricated.
