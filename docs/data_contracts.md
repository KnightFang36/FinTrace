# Shared data contracts

Source manifests, normalized transaction/account records and ingestion validation artifacts are implemented. Detection findings, scores, alerts, cases and other downstream records remain planned and must be implemented before being advertised as available APIs.

## Common conventions
- Identifiers are strings. Account keys contain separate `bank_id` and `account_id` components.
- Monetary external values are decimal strings; internal arithmetic uses declared fixed precision, never binary floats.
- Timestamps retain source text and precision; normalized instants require a declared timezone policy.
- Every artifact includes `schema_version`; persisted outputs also include `run_id` and `dataset_id`.
- Missing, unsupported, incomplete, disabled and evaluated-with-no-finding are distinct states.
- A table with no rows retains its documented schema.

## DatasetManifest
Input: manually supplied provenance plus file metadata computed at ingestion.

Implemented source-manifest fields: `schema_version`, `dataset_id`, `variant`, `synthetic`, `source_url`, `acquired_at`, `source_files[]` with `relative_path`, `sha256`, `byte_count` and exact ordered `header`, `source_terms`, `timezone_policy`, `timestamp_precision`, `observation_intervals[]`, `known_gaps[]`, `normalization_version`. See [the version-1 schema](../data/manifest.schema.json) and [data workflow](../data/README.md). Version 1 supports one CSV; optional benchmark annotations require their own future provenance contract.

Output: immutable manifest and reproducible source identity. An unset timezone policy blocks timestamp-dependent analysis. Coverage may be declared unknown; history-dependent features then remain unavailable.

Version 2 additionally records observed_at and timezone_policy_basis. acquired_at may be null when unknown; observed_at is the tool's actual local observation instant, not a replacement acquisition date. The timezone basis is project_convention or publisher_declared. The basis participates in dataset identity; observation/acquisition times do not. See [the version-2 schema](../data/manifest.v2.schema.json).

## Transaction
Inputs: verified positional IBM source columns.

| Source | Normalized field | Constraint |
| --- | --- | --- |
| Timestamp | occurred_at, source_timestamp | Parse explicitly; preserve original and precision |
| From Bank | sender_bank_id | String, non-empty |
| First Account | sender_account_id | String, non-empty |
| To Bank | receiver_bank_id | String, non-empty |
| Second Account | receiver_account_id | String, non-empty |
| Amount Paid | amount_paid | Positive fixed-precision value; unsupported rows quarantined with reason |
| Payment Currency | payment_currency | Non-empty source currency code, preserved |
| Amount Received | amount_received | Positive fixed-precision value |
| Receiving Currency | receiving_currency | Non-empty source currency code, preserved |
| Payment Format | payment_format | Preserve raw format; normalized channel only via explicit mapping |
| Is Laundering | Separate BenchmarkLabel | Never part of the detection-facing transaction schema |

Additional fields: `transaction_id`, `dataset_id`, `source_file_id`, `source_record_number`, `source_row_hash`, `normalization_version`. Record numbers count data records, excluding the header. `source_line_number` is optional because quoted CSV fields can span physical lines.

Self-transfers are retained and annotated. They are not automatically suspicious. Duplicate content is reported, not silently dropped.

Implemented Parquet amounts are decimal(38,8); values outside that exact representation are quarantined without rounding. occurred_at is UTC under the explicit manifest interpretation, and timestamp_precision preserves the source granularity. source_row_hash hashes only the ten financial source fields, excluding the label. Financially valid records with an absent/invalid benchmark label remain accepted; label issues are isolated in evaluation outputs.

## ObservedAccount
Fields: structured account key, `first_observed_at`, `last_observed_at`, `observed_currencies[]`, `source_endpoint_roles[]`.

These are observation facts, not verified opening date, customer identity, account balance or ownership. Optional `customer_id` is null until a separate verified table supplies it.

## PublisherAccount and AccountLinkCandidate
The optional publisher registry preserves Bank Name, Bank ID, Account Number, Entity ID and Entity Name as exact strings, with source checksum/record number, schema/run/source-dataset identity and synthetic=true. It is stored separately from observed detection accounts.

Candidate links preserve both observed and publisher bank IDs. Status is exact_source_key, zero_padding_candidate, ambiguous or unmatched; candidate_count exposes conflicts. Numeric zero-padding equivalence is an explicit diagnostic and does not rewrite account keys or establish verified identity. Pattern annotations and transaction laundering labels are never inputs to this join.

## OptionalCustomer and EntityLink
Customer fields: `customer_id`, `entity_type`, `name`, `jurisdiction`, `expected_activity_policy`, `source_id`, `effective_from`, `effective_to`, `observed_at`. All unprovided attributes remain null.

Link fields: `account_key`, `link_type`, `link_value_token`, `source_id`, `effective_from`, `effective_to`, `observed_at`. Supported link types may include device, IP, beneficiary, identity or ownership. A shared IP alone does not establish shared control.

## ValidationIssue and QualityReport
Issue fields: `issue_id`, source identity, record number, `field`, `code`, `severity`, `message`, `disposition`.

Report fields: accepted/rejected/warning counts, affected records, missing columns, duplicate-content counts, coverage gaps and policy version. File-level schema errors stop ingestion; row-level failures produce quarantine entries. A reimport of the same dataset/file/record is idempotent.

## Finding
Fields: `finding_id`, `rule_id`, `rule_version`, `subject_accounts[]`, `subject_roles[]`, `window_start`, `window_end`, `cutoff`, `transaction_ids[]`, `measurements`, `thresholds`, `currency`, `evidence_graph_ref`, `explanation`, `limitations[]`, `coverage_status`.

Measurements include units, denominators and allocation policy where relevant. Role assignment distinguishes forwarding/collecting intermediaries from counterparties. Do not give every participant in a suspicious network the same role or priority.

## FeatureCoverage
Fields: `feature_id`, `status` (evaluated/disabled/unavailable/truncated/failed), `reason_codes[]`, `analysis_window`, `source_coverage`, `search_budget`, `observed_work`.

No findings with an unavailable status is not a clean-account determination.

## GraphEvidence
Fields: `graph_id`, graph type, account nodes, transaction edges, currency policy, temporal ordering policy, seed accounts, searched horizon, bounds and truncation diagnostics.

Paths list ordered transaction IDs and times. Cycles additionally show the returning account and value comparison basis. Communities retain algorithm name, configuration and membership; membership alone does not create an alert.

## AccountPriority
Fields: account key, scoring window, `score` (integer 0–100), `band`, `contributions[]`, `scoring_policy_version`, `coverage_summary`.

Each contribution records family ID, eligible finding IDs, selected finding IDs, applied weight and suppressed correlated findings. Missing features contribute no invented evidence; coverage remains visible.

## Alert
Fields: `alert_id`, `deduplication_key`, subject account/group, finding IDs, priority snapshot, detection window, first/last observed times, `state`, `assigned_to`, `case_id`, explanation and evidence references.

States: open -> in_review -> escalated or closed. Closed alerts require a reason; escalation is an internal workflow event. Repeated evidence appends an update event, not a silent replacement.

## Case and AuditEvent
Case: `case_id`, title, alert IDs, linked accounts, status, assignee, notes, created/updated timestamps, evidence snapshot IDs, disposition and rationale.

Case states: open -> investigating -> escalated or closed; an explicit audited reopen returns closed cases to investigating. Alert reopening is a separate explicit audited action returning it to open.

Event: ID, entity type/ID, actor, timestamp, action, previous/new state, reason, referenced artifact hashes. Never delete historical events through routine edits.

## ReportManifest
Fields: report ID, case/alert ID, export timestamp, file paths/hashes, dataset/run/policy identity, evidence count, applied filters and limitations. Escape HTML and neutralize formula-prefixed text cells in spreadsheet-oriented exports.

## BenchmarkLabel: evaluation only
Fields: `transaction_id`, `is_laundering`, source record identity. Optional pattern annotations have their own documented schema and provenance.

A positive transaction label is not a confirmed mule label for either endpoint. Account-level results, if computed, must be named explicitly as participation in labelled laundering transactions, with the endpoint aggregation policy disclosed.

## AnalysisRun and ReplayCheckpoint
Run fields: run ID, dataset/configuration/software identity, cutoff, start/end, completion status, per-feature coverage, artifact hashes.

Checkpoint fields: replay ID, dataset/configuration identity, last processed event ordering key, watermark, processed counts and persisted artifact references. Reject resume against changed inputs or policies.
