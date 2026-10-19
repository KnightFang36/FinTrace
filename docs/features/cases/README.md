# Case management and audit

**Status: implemented local service, CLI and Streamlit case workspace.** Owners: `src/fintrace/cases/service.py` and `src/fintrace/storage/case_store.py`. Authentication remains a separate deployment concern.

## Implemented interface

```python
apply_case_action(database, case_id, action, *, actor, at, reason,
                  expected_version, request_id, payload=None) -> dict
read_cases(database, case_id=None, *, version=None) -> dict
```

Creation uses `case_id=None`, `expected_version=0`, and payload `{"title": "Review transfers", "snapshot_id": "priorities-...", "alert_ids": ["alert-..."]}`. Supported actions are `create`, `attach` (snapshot ID and alert IDs), `note` (`text`), `assign` (`assignee`), `transition` (`state`, plus `disposition` when closing), and `reopen`. Every action requires a nonblank actor/rationale, an explicit timezone-aware audit time and a request ID. Identical retries return the original response; reusing a request ID for different arguments fails.

CLI: `python scripts/manage_cases.py --database data/processed/alerts.duckdb list` or `show CASE_ID --version 1`. Apply actions with `apply ACTION --case-id CASE_ID --expected-version VERSION --payload-file action.json --request-id UNIQUE_REQUEST_ID --actor REVIEWER --at TIME_WITH_OFFSET --reason RATIONALE`. Omit `--case-id` on creation. Payload files contain the JSON objects above. The Cases page provides the same explicit actions.

## Inputs

Selected alerts from an existing immutable priority snapshot, analyst notes, assignment and explicit actions. Expected record version is required for concurrency checks. Workflow time cannot move backwards or precede attached evidence.

## Outputs

Versioned cases, append-only notes and disposition/assignment history, frozen evidence attachments and immutable audit events. Every event records actor, time, reason, previous/new state, request ID and case/evidence hashes. All prior case versions remain readable. Catalog reads return up to 200 case summaries and disclose omitted results; reading never creates storage.

## Functionality

Open cases may become investigating or closed. Investigating cases may be escalated or closed. Escalated cases may return to investigating or close. Reopening is a distinct action that returns a closed case to investigating. Closed cases accept appended correction notes; other edits require reopening. The last closure disposition and all earlier versions remain retained.

Attach 1–100 alerts per snapshot action, up to 100 attachments and 1,000 versions per case. Attachments freeze the selected snapshot's alert/evidence projection and hash it; later alert evidence cannot enter an earlier attachment. Different accounts and datasets can be linked without declaring participants guilty. The service never changes alert lifecycle state merely by attaching it to a case. Review-only publisher identity candidates are not promoted to verified identities.

The storage transaction commits the current case, immutable version, audit event and request response together. The UI keeps the displayed expected version until an explicit reload or successful action; a rerender alone does not submit an action.

## Errors and edge cases

Reject unknown/out-of-snapshot alerts, stale versions, duplicate attachments, conflicting request IDs, invalid transitions, missing closure dispositions, backwards timestamps and exceeded budgets. No partial case/event/request is committed on failure. A missing/empty store produces an empty read-only catalog. No external notifications, account restrictions or regulatory submissions occur.

## Acceptance criteria

Closing preserves evidence, notes, assignment and prior versions. Reopening creates a new event while retaining the closure. A stale update cannot replace the latest state. A retried request adds no version/event; a rerender adds no write. Historical case versions and evidence hashes remain verifiable.

## Data availability

Uses the implemented local alert store and frozen snapshots. Analyst identifiers are entered audit names, not authenticated identities. Benchmark labels and optional context are not inputs.
