# src/fintrace instructions

## Purpose
Own domain contracts, orchestration and service subpackages.

## Inputs
Validated financial records, explicit policy and run/cutoff identity.

## Outputs
Deterministic evidence, priority, alerts, investigation data and audit artifacts.

## Functionality
contracts.py will define shared records; pipeline.py will orchestrate services while preserving dependencies in docs/architecture.md. Subpackages own their feature logic.

## Constraints
Do not expose placeholder APIs as working. Ingestion may extract benchmark labels into a separate evaluation artifact; evaluation alone may consume that artifact. All detection and investigation services remain label-free. No floating-point money, implicit timezones, hidden currency conversion or unsupported exact-provenance claims.
