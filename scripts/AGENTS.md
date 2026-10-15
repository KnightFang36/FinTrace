# scripts instructions

## Purpose
Maintain explicit repository checks and future operational command wrappers.

## Inputs
Repository files and declared local dataset/configuration paths.

## Outputs
Diagnostics, exit codes and eventually auditable service invocations.

## Functionality
check_scaffold.py validates directory instructions, local Markdown links including data READMEs, syntax, configuration consistency and the declared dependency boundary without downloading data. prepare_data.py delegates local source-header verification, hashing and manifest create/verify operations to fintrace.ingestion.manifest. Future operational scripts must also delegate to source services.

## Constraints
The prepare_data.py audit command inventories uploaded transactions/accounts/patterns without creating a provenance declaration. Optional pattern content must remain separate from detection inputs.

No silent network access, credential prompts, source modification or invented runnable commands. A scaffold check is not a detection-system test.
