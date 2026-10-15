# src/fintrace instructions

## Purpose
Own domain contracts, orchestration and service subpackages.

## Inputs
Validated financial records, explicit policy and run/cutoff identity.

## Outputs
Deterministic evidence, priority, alerts, investigation data and audit artifacts.

## Functionality
contracts.py defines exact account/transaction records, findings, feature coverage and rule results. pipeline.py remains pending general orchestration. rules/engine.py owns deterministic evaluation; rules/runner.py owns verified snapshot loading/publication. Preserve dependencies in docs/architecture.md and keep subpackage business logic separate.

## Constraints
Do not expose placeholder APIs as working. Ingestion may extract benchmark labels into a separate evaluation artifact; evaluation alone may consume that artifact. All detection and investigation services remain label-free. No floating-point money, implicit timezones, hidden currency conversion or unsupported exact-provenance claims.

Graph engine owns chronological evidence; graph runner reuses the verified detection snapshot loader without account-edge filtering. Explicit seeds restrict path origins only. Optional reference exposure remains pending.
