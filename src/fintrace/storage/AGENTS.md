# Storage instructions

## Purpose
Implement local Parquet/DuckDB persistence with an explicit evaluation-data boundary.

## Inputs
Validated normalized records, immutable dataset/run manifests, findings, graphs, priority ledgers, alerts, cases, audit actions and replay checkpoints. Reference tables are optional and versioned.

## Outputs
Idempotently persisted records, snapshot IDs, repository query read models, conflict diagnostics and schema/version metadata.

## Functionality
Provide future repository operations for importing dataset versions, opening analysis runs, persisting findings, reading investigation snapshots, updating version-checked cases, appending audit events and resuming replay checkpoints. Store benchmark labels in a separate artifact and repository path accessible only to evaluation. Ordinary queries must never accidentally join labels.

## Constraints
Use parameterized queries and explicit transactions. Do not convert money to floating point. Preserve structured account identity and source record uniqueness. Make incomplete writes invisible to completed-run queries. Keep paths under configured local roots. Do not mutate raw files. Concurrent case updates require expected-version checks. Audit history must remain append-only. Database files are ignored by Git.
