# tests/integration instructions

## Purpose
Verify complete implemented service boundaries and persistence.

## Inputs
Small fixture imports, isolated temporary storage and explicit cutoffs.

## Outputs
End-to-end lineage, idempotency, export, replay and evaluation-isolation checks.

## Functionality
Exercise ingest-to-evidence flow, repeat imports, case audit, replay resume and prevention of label/future-data leakage.

## Constraints
Use temporary paths. No automatic dataset download or external account access. Do not treat a status-page render as complete detector verification.
