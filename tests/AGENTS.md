# tests instructions

## Purpose
Verify the implemented source/data boundary and add meaningful checks as downstream services are implemented.

## Inputs
Small clearly labelled handcrafted fixtures and expected financial/temporal behaviour.

## Outputs
Focused unit and integration results for implemented source auditing, provenance, validation, ingestion, publisher diagnostics and deterministic transaction rules.

## Functionality
Test financial precision, distinct bank/account identity, source lineage, label isolation, chronological paths, tied timestamps, bounded searches, score caps and workflow transitions.

## Constraints
Rule tests cover distinct counterparties, legitimate recurring payments, exact totals, FIFO allocation, equal-time exclusions, source coverage, baseline evidence, cutoffs, input order and budgets. Runner tests prove evaluation files remain unread and corrupted artifacts cannot be reused. Add graph/alert tests with those implementations. Never use real personal data or redistribute IBM files in fixtures.

Graph tests now cover timestamp ties/reversal, cutoff isolation, precise currencies and identifiers, repeated groups, parallel edges, bounded search/context/rendering, evidence roles and verified publication.

Priority/alert tests cover family suppression, caps, eligibility, source snapshot identity, persistent repeat-run idempotency, evidence/score retention, transactional rollback, stale versions and explicit close/reopen audit.

Frontend AppTest checks use isolated fixture databases for writes. Cover missing-store no-write behavior, filters, current workflow vs cutoff-isolated evidence, explicit reviewed actions and rerender idempotency. Network unit checks cover caps, parallel edges, direction and HTML escaping. Browser verification must not submit analyst actions against the uploaded-data workspace. Case/report/replay integration tests use synthetic fixtures to cover stale versions, immutable history, safe exports, lineage/currency totals, cutoff isolation and crash recovery without duplicate events.
