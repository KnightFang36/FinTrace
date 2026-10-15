# Processed artifacts

This directory is reserved for generated records; no normalization or persistence service is implemented yet.

| Planned location | Inputs | Outputs |
| --- | --- | --- |
| datasets/<dataset_id>/ | Validated ingestion with lineage | Label-free transactions, observed accounts, quarantine and quality reports |
| evaluation/<dataset_id>/ | Isolated publisher labels and pattern annotations | Benchmark-only artifacts unavailable to detection and ordinary investigation queries |
| runs/<run_id>/ | Versioned transactions, policies and cutoff | Findings, graph evidence, priority ledgers and alert snapshots |
| Local database | Future persisted workflow actions | Cases, append-only audit events and replay checkpoints |

These locations are a storage contract, not directories created by the current tool. Data stays ignored by Git. Monetary values retain fixed precision, currencies stay distinct, and incomplete processing must not appear as a completed dataset.

Before future ingestion, verify the raw manifest. See [data workflow](../README.md) and [shared record contracts](../../docs/data_contracts.md).
