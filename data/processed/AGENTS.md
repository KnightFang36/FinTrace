# data/processed instructions

## Purpose
Store versioned local outputs of validated analysis.

## Inputs
Transactions, observed accounts, quarantine, graph evidence, findings, priorities, alerts, case events and checkpoints.

## Outputs
Parquet artifacts, isolated benchmark-label files and local DuckDB databases.

## Functionality
Ingestion partitions by dataset/run identity and exposes only completed snapshots. Label artifacts stay under the evaluation-only boundary described in README.md. Supplemental publisher accounts and review-only link candidates are separate from detection accounts. Preserve completion-marker checksums and verify them before idempotent reuse.

## Constraints
Use fixed precision, maintain lineage and prevent raw label columns from entering investigation queries. Generated data stays ignored by Git.
