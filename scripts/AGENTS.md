# scripts instructions

## Purpose
Maintain explicit repository checks and future operational command wrappers.

## Inputs
Repository files and declared local dataset/configuration paths.

## Outputs
Diagnostics, exit codes and eventually auditable service invocations.

## Functionality
run_rules.py delegates cutoff snapshot analysis to fintrace.rules.runner. It requires an explicit timezone-aware cutoff, accepts optional exact account keys, and uses the verified normalized detection artifact only. Input overflow fails; incomplete evidence is reported through rule coverage rather than sampled findings.

check_scaffold.py validates directory instructions, local Markdown links including data READMEs, syntax, configuration consistency and the declared dependency boundary without downloading data. prepare_data.py delegates local source-header verification, hashing and manifest create/verify operations to fintrace.ingestion.manifest. Future operational scripts must also delegate to source services.

## Constraints
The prepare_data.py audit command inventories uploaded transactions/accounts/patterns without creating a provenance declaration. Optional pattern content must remain separate from detection inputs.

ingest creates label-isolated Parquet datasets from a verified manifest; accounts preserves synthetic publisher records and explicit review-only links. Both require the pinned data environment. Keep source values, metadata assumptions, quarantine and completion integrity visible; no routine source artifacts belong in commits.

No silent network access, credential prompts, source modification or invented runnable commands. A scaffold check is not a detection-system test.

run_graphs.py delegates to graph.runner, publishing verified graph JSON and a bounded headless PNG. --seed restricts chain/cycle origins while groups and descriptive context retain full loaded-window scope.

manage_alerts.py imports verified compatible snapshots, lists local alerts and delegates explicit version-checked transitions to AlertStore. It defaults to ignored data/processed/alerts.duckdb, never contacts external services, and reports dependency/database errors without exposing tracebacks for expected failures.
