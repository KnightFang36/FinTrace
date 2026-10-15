# Processed artifacts

The data ingestion command now creates immutable normalized records and provenance/quality artifacts here. Downstream detection and case persistence remain pending.

| Planned location | Inputs | Outputs |
| --- | --- | --- |
| datasets/<dataset_id>/ | Validated ingestion with lineage | Label-free transactions, observed accounts, quarantine and quality reports |
| evaluation/<dataset_id>/ | Isolated publisher labels and pattern annotations | Benchmark-only artifacts unavailable to detection and ordinary investigation queries |
| runs/<run_id>/ | Versioned transactions, policies and cutoff | Findings, graph evidence, priority ledgers and alert snapshots |
| supplemental/<snapshot_id>/ | Publisher entity CSV and observed account registry | Preserved synthetic publisher records, explicit link candidates and row quarantine |
| Local database | Future persisted workflow actions | Cases, append-only audit events and replay checkpoints |

datasets/, evaluation/ and supplemental/ are created by implemented commands. runs/ and the local case database remain planned. Data stays ignored by Git. Monetary values retain fixed precision, currencies stay distinct, and incomplete processing does not appear as a completed dataset. A completion.json marker lists artifact hashes for verified reuse.

Before future ingestion, verify the raw manifest. See [data workflow](../README.md) and [shared record contracts](../../docs/data_contracts.md).
