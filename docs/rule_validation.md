# Verified deterministic rule snapshot

## Scope

This check ran the transaction-rules-v1 engine against the completed local HI-Small detection artifact. It is one cutoff snapshot, not a scan of every historical window and not a labelled-performance evaluation.

- Dataset: ibm-d09512cc782ac4059163288737a35b3a948ab93d31888fb8da9c6c342b86cde4.
- Exclusive cutoff: 2022-09-02T12:00:00Z.
- Loaded normalized source interval: 10:00 through 12:00 UTC, excluding the cutoff.
- Evaluated movement rules use their configured 60-minute active interval ending at cutoff.
- Input: 61,418 valid normalized records; 1,163 exact-key self-transfers excluded from rule indicators.
- Source precision: minute. UTC is the recorded project convention.
- Policy: demo-v1; SHA-256 79423c60f60055e3cad4c2c98af2ac7af615c2231f66e3c523252d96c4a17596.

## Findings

| Rule | Findings |
| --- | ---: |
| Fan-in / collection | 12 |
| Fan-out / dispersal | 15 |
| FIFO observed pass-through | 26 |
| Descriptive repeated-payment episodes | 191 |
| Total | 244 |

The findings reference 234 distinct primary account keys and 4,305 distinct transactions. These counts describe patterns for review, not confirmed criminal accounts. One account can participate in multiple findings. Repeated-payment episodes can be legitimate recurring business.

Burst and observed-dormancy rules were unavailable because observation coverage is unknown. The engine did not infer coverage from timestamp minima/maxima. Graph features remained unavailable; cash-out, profile mismatch and known-exposure extensions remained disabled.

## Evidence and integrity checks

Every referenced transaction was resolved against the prepared detection Parquet. The check verified half-open active windows, self-transfer exclusion, fan-in/out counterpart counts and exact totals, repeated-payment totals, strict FIFO timing, same-currency allocation and that neither incoming nor outgoing amounts were over-allocated.

The analysis read no benchmark labels or publisher pattern annotations. Fixture integration tests additionally corrupt the evaluation-label artifact and confirm that rule results remain unchanged.

A repeat invocation verified the input and output hashes and returned reused. Actual run artifacts remain local under data/processed/rule_runs/.

- Run ID: rules-80b9cff57faaa73d5f0d409e94fa8157c52ee0725a6e0f883e3b30e5554d61c8.
- Findings SHA-256: 0d9a480b74f21580e8e07a2d54d2a8001bb5e441885cfe8b0bb10e6442519109.
- Transaction input SHA-256: 1fcd872cc27b5b21d03b6e9e6c72e9b81f8b5754e41f24726f010d65ffac80d6.
- Quality input SHA-256: 94f3198f07b6045987b073b8225f5e039a3f9ace7c1942a9db7e309ec26e13b9.

## Reproduce

```bash
.venv/bin/python scripts/run_rules.py \
  data/processed/datasets/ibm-d09512cc782ac4059163288737a35b3a948ab93d31888fb8da9c6c342b86cde4/transactions.parquet \
  --cutoff 2022-09-02T12:00:00Z

.venv/bin/python -m pytest tests -q
python3 scripts/check_scaffold.py
```

The completed suite passed 90 tests and 31 subtests, including positive and legitimate counterexamples, complete-history fixtures, unavailable coverage, currency/timestamp boundaries, exact financial arithmetic, FIFO allocation, evidence limits, source corruption and repeat-run integrity.

See [the feature contract](features/transaction_rules/README.md) for the API, limits and supported inputs. Temporal NetworkX analysis is the next roadmap phase; priorities, alerts, cases and the investigation UI follow separately.
