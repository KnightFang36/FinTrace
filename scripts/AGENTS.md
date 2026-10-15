# scripts instructions

## Purpose
Maintain explicit repository checks and future operational command wrappers.

## Inputs
Repository files and declared local dataset/configuration paths.

## Outputs
Diagnostics, exit codes and eventually auditable service invocations.

## Functionality
check_scaffold.py validates directory instructions, local Markdown links, syntax, configuration consistency and the declared dependency boundary without downloading data. Future operational scripts must delegate to source services.

## Constraints
No silent network access, credential prompts, source modification or invented runnable commands. A scaffold check is not a detection-system test.
