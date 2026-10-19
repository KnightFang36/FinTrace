# Alert generation and lifecycle

**Status: local deduplication, audited lifecycle, transactional persistence, CLI and Streamlit alert review implemented.** The [investigation dashboard](../dashboard/README.md) provides explicit version-checked review transitions. Case linking and general report exports remain pending; regulatory submission is excluded. Owners: `src/fintrace/alerts/` and `src/fintrace/storage/alert_store.py`.

## Implemented interfaces

```python
build_alerts(findings, priorities, existing_alerts, alert_policy, *, actor, at) -> dict
transition_alert(alert, new_state, *, actor, at, reason, expected_version, reopen=False) -> (alert, event)
import_analysis(rule_run, graph_run, scoring_policy_path, alert_policy_path, database_path, *, actor, at) -> dict
```

`AlertStore(path)` is a context manager exposing `import_analysis`, `list_alerts`, `events(alert_id)`, `evidence(finding_id)`, `priority(priority_id)` and version-checked `transition`. Store inputs are validated Finding records and a verified priority snapshot; the CLI additionally verifies frozen detector artifacts before computing priorities.

## Inputs

Completed `run_rules.py` artifacts, optionally completed `run_graphs.py` artifacts from the same dataset, exclusive cutoff and input hashes; fixed scoring policy; versioned `config/alerts.toml`; local DuckDB path; explicit audit actor and timezone-aware action timestamp. Transitions also require expected version and reason. The import validates source artifact hashes, engine/schema versions, finding dataset/cutoff/policy identity and finding counts. No raw data, evaluation labels or pattern annotations are read.

## Outputs

Persistent alerts with exact subject identity, family, stable incident key, linked finding and transaction IDs, retained priority snapshot IDs, state/version, analysis-window bounds and measured-count explanations. Each explanation links back to immutable findings containing the rule thresholds, measurements, source references and limitations. `first_observed_at` and `last_observed_at` represent the earliest/latest **finding analysis-window bounds**, not exact first/last transaction timestamps. Actual transaction times remain in source/graph evidence. No exact activity duration is inferred from these alert fields.

Imports return changed-alert/event counts, unchanged incidents, review-band counts, source run IDs and coverage. Evidence, account-priority snapshots and complete priority runs are immutable; audit events append in version order. Persistence uses DuckDB with explicit transactions and parameterized values.

## Functionality

Incident keys hash dataset, exact account, scoring family, versioned alert policy and an epoch-aligned time bucket. Defaults use 24-hour buckets containing the last instant of the finding's exclusive analysis window. A midnight window end belongs to the preceding incident. A finding crossing a bucket boundary stays whole in that final bucket; overlapping windows ending in different daily buckets may create separate incidents. This is an explicit grouping policy, not a claim about criminal-episode boundaries.

Identical imports create no new alert or event. New findings or a new priority snapshot update the incident, union transaction IDs and append one audit event while retaining previous evidence/scores. A changed alert policy starts a distinct incident identity. The default minimum priority of zero includes every supported evidence-backed finding; centrality/community metrics cannot generate alerts.

States: open -> in_review -> escalated or closed. Escalated alerts may return to in_review or close. Closed alerts require an explicit audited reopen to return to open. Every transition needs actor, timestamp, reason and expected version. New evidence for a closed alert is appended while it remains closed. Imports and transitions cannot move their effective audit time backwards. No automatic account blocking, external notification, filing or confirmed-crime determination occurs.

DuckDB tables are namespaced `ft_*` and schema versioned. Alerts/events/evidence/priorities are written in one transaction. Failure rolls back the complete import. Expected-version checks reject stale updates; DuckDB locking/transaction errors are surfaced for retry instead of silently overwriting. Local database files stay outside Git. Backups, tamper-proof external audit storage and multi-user hosting are later operational work.

## Errors and edge cases

Reject incomplete/corrupt detector outputs, symlink artifacts, cross-dataset/cutoff/source combinations, unsupported evidence, missing priorities, altered contribution ledgers, immutable-ID conflicts, illegal/stale transitions, absent actors/reasons, implicit timezones and unsupported store schema versions. The store must have a `.duckdb` path outside raw/evaluation data. Dependency, filesystem and database errors produce actionable CLI errors. Independently dated enrichment remains absent.

## CLI

```bash
.venv/bin/python scripts/manage_alerts.py import \
  --rules-run data/processed/rule_runs/RULE_RUN_ID \
  --graph-run data/processed/graph_runs/GRAPH_RUN_ID \
  --actor local-investigator --at 2026-10-16T12:00:00+05:30

.venv/bin/python scripts/manage_alerts.py list

.venv/bin/python scripts/manage_alerts.py transition ALERT_ID in_review \
  --expected-version 1 --actor local-investigator \
  --at 2026-10-16T12:05:00+05:30 --reason "Review started"
```

Use actual completed run IDs and the actual action time. Omit `--graph-run` for rule-only import; missing graph coverage remains explicit. The default store is `data/processed/alerts.duckdb`; global `--database PATH` goes before the subcommand. Close only after entering review, with a reason; reopening requires both target `open` and `--reopen`. No analyst actions are performed by imports beyond creating/updating local review records.

## Acceptance criteria

Importing the same analysis twice creates one alert per incident and exactly one creation event. New evidence retains prior priority IDs and appends an event. All alert transaction IDs reconcile to retained finding evidence. Partial graph/history coverage survives in priorities. Stale/illegal transitions fail. Interrupted imports and immutable evidence conflicts roll back all writes. Closing/reopening remains explicitly audited.

## Data availability

Core IBM rule/graph findings support this feature. Customer identities, analyst decisions, confirmed mule labels and regulatory outcomes are not invented. See [the checked snapshot](../../priority_alert_validation.md) and the unit/integration tests for verification.
