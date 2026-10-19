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

scoring/priority.py owns fixed-family contributions. alerts/engine.py owns stable incidents and explicit lifecycle actions; alerts/runner.py verifies compatible frozen detector outputs. storage/alert_store.py transactionally retains immutable evidence/priority snapshots and append-only audit. storage/case_store.py retains immutable case versions, current state, idempotent requests and append-only audit events. cases/service.py owns explicit lifecycle actions.

investigations/dashboard.py owns read-only snapshot catalogs, source-evidence projection and graph integrity gates. Frontend app/ only presents these read models and explicit action results. reporting/export.py resolves verified source transactions and publishes local reports atomically. replay/engine.py reuses the existing batch services at ordered cutoffs with isolated alerts and durable checkpoints.
