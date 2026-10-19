# Deterministic transaction rules

**Status: six deterministic core rules and their evidence/coverage engine are implemented.** Owner: `src/fintrace/rules/`.

## Implemented interface
```text
evaluate_rules(transactions, history=None, *, policy, cutoff, context=None) -> RuleResult
```
Inputs are normalized label-free mappings, a validated TOML-derived policy and an explicit timezone-aware exclusive cutoff. RuleResult contains findings, per-rule coverage, deterministic run identity, scope and policy hash; to_dict() returns JSON-compatible decimal strings and timestamps. Unknown record/context fields are rejected rather than silently passing benchmark columns through.

Evaluation is one cutoff snapshot: each core rule examines its configured half-open interval ending at cutoff. It is not a full-history rolling scan. Self-transfers are excluded from movement/frequency indicators, source account strings are preserved, values stay separated by currency, and all money arithmetic uses an explicit 60-digit decimal context. Graph-derived rules remain unavailable in this phase; optional context rules are disabled or unavailable until their services exist.

## Inputs
- Validated, label-free transactions available before the analysis cutoff.
- Versioned rules, known observation intervals and optional verified context.

## Outputs
- Findings with affected account roles, rule measurements, thresholds, transaction IDs and limitations.
- A per-rule coverage result, including disabled, unavailable and evaluated-with-no-finding.

## Functionality
- Evaluate pass-through with an explicitly declared FIFO allocation of observed same-currency inflows; never allocate an inflow more than once within one account/window evaluation.
- Count distinct counterparties for fan-in/out; record each payment separately for frequency.
- Compare bursts with eligible complete historical windows, excluding the active window; reject a zero or unavailable baseline instead of dividing by it.
- Require sufficient prior observation for inactivity indicators; first appearance alone is not reactivation.
- Identify repeated splitting patterns without assuming a legal reporting threshold or proving intentional evasion.

## Errors and edge cases
- Missing history makes historical rules unavailable, not negative.
- Cross-currency attribution is unavailable without explicit dated conversion data.
- Unsupported cash-out mappings or customer context disable the corresponding rule.

## Acceptance criteria
- Incoming transfers followed by eligible forwarding generate an auditable allocated-value ledger.
- Outflows preceding inflows cannot create pass-through evidence.
- A legitimate repeated payroll example can trigger a pattern finding but must remain described as requiring contextual review.

## Data availability
Core rules supported; cash-out and profile mismatch are gated by additional verified inputs.

## Rule-specific contracts

All windows exclude records at or after their end/cutoff. Currency-dependent calculations use compatible same-currency amounts only. Values below are illustrative policy from `config/rules.toml`, not legal thresholds.

`config/rules.toml` carries parameters only for the six core rules. The `layering`, `circular_flow` and `coordinated_group` sections accept `enabled` alone and report coverage from this policy. Their thresholds are read from `config/graph.toml`. Any other key in those sections, or in the unimplemented `cash_out`, `profile_mismatch` and `known_exposure` sections, fails validation instead of being ignored.

| Rule / proposed function | Required inputs | Condition and functionality | Finding measurements and evidence |
| --- | --- | --- | --- |
| pass_through / detect_pass_through | Account inflows/outflows, 60-minute horizon, FIFO policy | At least 3 incoming payments and at least 80% eligible observed inflow forwarded within the horizon; only strictly later outflows count | Allocation ledger, inflow/outflow IDs, denominator, forwarded ratio, time-to-forward; opening balance and exact provenance unknown |
| fan_in / detect_fan_in | Receiver, 60-minute window, sender identities | At least 8 distinct sending accounts; identify collection concentration | Sender count, incoming count, totals by currency, supporting payments |
| fan_out / detect_fan_out | Sender, 60-minute window, recipient identities | At least 8 distinct recipients; identify dispersal | Recipient count, outgoing count, totals by currency, supporting payments |
| burst / detect_burst | Active-hour count, previous 7 complete days, comparable historical hourly windows | At least 20 payments and at least 4 times the median comparable prior count; zero/absent baseline yields unavailable under current policy | Current count, historical counts/median, ratio, coverage and payment IDs |
| dormant_activation / detect_dormant_activation | Complete preceding observation, account history, current 120-minute window | At least 7 days observed inactivity after a prior observed transaction, then at least 10 payments | Last observed activity, covered inactive interval, activation count and payment IDs; do not call this verified bank dormancy |
| repeated_splitting / detect_repeated_splitting | Direction, account, counterparty links, same-currency payments in 60 minutes | At least 5 payments on the same directed account-counterparty relationship, each below the policy-declared episode total; collection/dispersal findings may link related episodes | Episode total, per-payment values, counterparties and times; descriptive repeated splitting, not intentional structuring |
| cash_out / detect_cash_out | Inflows, following exit payments, verified channel mapping | Disabled until the source channel can be reliably mapped and a time/value policy is configured | Inflows, exit IDs, mapped channel provenance and delay |
| profile_mismatch / detect_profile_mismatch | Verified customer expected-activity policy, transactions | Disabled without real context and explicit comparison limits | Observed value/count, declared expectation, discrepancy and context source |
| known_exposure / detect_known_exposure | Dated independent references and temporal graph | Disabled by default; delegates directional path/exposure work to graph service | Reference identity/date, directed path, depth and cutoff; never derived from IBM labels |

The repeated-splitting rule intentionally records a broad pattern. Repeated legitimate payments can satisfy it. Without a configured contextual threshold or independent evidence it must not be described as deliberate reporting evasion.

## Callable responsibility boundaries
`engine.py` resolves eligibility, invokes enabled rules and combines findings without scoring them. Rule modules accept validated records, not raw CSV paths, UI state, benchmark labels or database connections. Graph-derived layering/cycle/coordinated-group findings come from the graph service and use the same Finding schema.

## Minimal worked acceptance example
Given same-currency incoming payments of 100, 100 and 100, followed strictly later by an eligible outgoing payment of 250 within 60 minutes, the allocated forwarded ratio is 250/300. The finding must include all four transaction IDs, the 300 denominator, the 250 allocated value and the FIFO assumption. Reversing the payment order must remove that pass-through finding. This is a handcrafted specification example, not IBM data.

## Command-line workflow

Use the prepared detection artifact and an explicit exclusive cutoff:

```bash
.venv/bin/python scripts/run_rules.py \
  data/processed/datasets/ibm-d09512cc782ac4059163288737a35b3a948ab93d31888fb8da9c6c342b86cde4/transactions.parquet \
  --cutoff 2022-09-02T12:00:00Z
```

Use --policy for another validated TOML file and --output-root for another local artifact root. Add --account BANK_ID ACCOUNT_ID, repeated if needed, to analyze only exact subject keys. Bank/account strings retain leading zeros. Counterparties remain evidence participants, not automatically included subjects.

The runner verifies the transaction and quality-file hashes in the completed dataset inventory. It validates the normalized schema, projects only financial columns and excludes all records at cutoff or later. It does not open evaluation-label or pattern files. It reads the largest configured active window; when historical rules have declared source coverage, it reads the relevant complete prefix for the selected subject scope so prior-activity anchors are retained. Large prefixes must be narrowed with account scope or an explicitly reviewed input budget; they are never silently sampled.

Current context fields are dataset_id, subject_accounts, observation_intervals, known_gaps, timezone_policy, timezone_policy_basis and timestamp_precision. Unknown context keys, including benchmark/enrichment payloads, are rejected. Verified-context detection is reserved for the later context phase.

## Output contracts

Artifacts under data/processed/rule_runs/<run_id>/:

- findings.json: RuleResult, including findings, policy/run/dataset identity, cutoff, source timing context and per-rule coverage.
- run.json: run summary, exact input hashes, finding counts, feature statuses and findings-file checksum.

A completed repeat run verifies the inputs and findings checksum and returns reused. Corrupted/incomplete output is rejected without overwriting it. Runtime artifacts stay ignored by Git.

Each finding includes one primary account and its role, source transaction IDs, a half-open active interval, currency-specific measurements, actual thresholds and a fixed explanatory template. Pass-through includes the FIFO allocation ledger and exact numerator/denominator; its displayed ratio is rounded to six decimal places, while eligibility uses exact cross multiplication. Baseline and dormancy anchors may reference older transactions; those historical IDs are included explicitly and count toward evidence limits.

## Coverage and deterministic semantics

- Unknown observation coverage makes burst and dormancy unavailable even if file timestamps span enough calendar days.
- Burst comparisons use complete 24-hour UTC-offset days. Counts stay aligned with their comparison windows, the median excludes the active interval, and a zero median is unavailable. The comparison window is bounded to 24 hours and lookback to 365 days.
- Dormancy requires actual prior activity, a completely covered quiet gap and enough current activity. First appearance is not reactivation.
- The default movement/frequency analysis excludes exact-key self-transfers.
- A same-time outgoing transfer cannot consume a same-time inflow. Stable identifier order only resolves bookkeeping among equal-time outgoing transfers.
- Same-currency asset values are compared at each account; no exchange rate is inferred.
- The default limits are 250,000 input records, 10,000 findings per rule, 10,000 evidence transactions per finding and 20,000 FIFO allocation entries. Input overflow fails. Findings with incomplete evidence are withheld and coverage is truncated; no silent ID clipping occurs.
- Coverage reports evaluated_groups, unavailable_groups_by_reason, truncated_groups and findings. An evaluated rule may still have unavailable groups; read the reasons and counters.
- Graph rules are unavailable until the graph phase. Optional cash-out/profile/exposure rules are disabled or unavailable until verified-context services exist.
- Snapshot windows can overlap across runs; incident grouping/deduplication belongs to the later alerts phase.

## Verification

Run `.venv/bin/python -m pytest tests -q` and `python3 scripts/check_scaffold.py`. Handcrafted tests cover true patterns and legitimate counterexamples, exact-money totals, chronology/ties, distinct counterparties, currency separation, observation gaps, zero baselines, historical anchors, future-record isolation, subject scope, record order, budgets and artifact integrity.

See [the checked IBM snapshot](../../rule_validation.md) for source-backed results. Pattern findings are review candidates, not proven illicit activity, risk scores or confirmed mule identities.
