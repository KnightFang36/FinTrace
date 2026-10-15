# data/processed instructions

## Purpose
Store versioned local outputs of validated analysis.

## Inputs
Transactions, observed accounts, quarantine, graph evidence, findings, priorities, alerts, case events and checkpoints.

## Outputs
Parquet artifacts, isolated benchmark-label files and local DuckDB databases.

## Functionality
Partition by dataset/run identity and expose only complete snapshots. Store label artifacts under an explicit evaluation-only boundary.

## Constraints
Use fixed precision, maintain lineage and prevent raw label columns from entering investigation queries. Generated data stays ignored by Git.
