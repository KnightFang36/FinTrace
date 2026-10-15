# Explainable priority scoring

**Status: implemented.** Owner: `src/fintrace/scoring/`.

## Implemented interface

```python
score_accounts(findings, coverage, scoring_policy, window) -> dict
validate_priority_snapshot(snapshot) -> dict
load_scoring_policy(path) -> dict
```

## Inputs

Shared Finding objects or exact label-free Finding mappings, per-service coverage metadata, versioned fixed weights from `config/scoring.toml`, and an explicit timezone-aware `{start, end}` scoring window. All findings must share one dataset and the same exclusive cutoff, equal to the scoring-window end. The scoring window must fully contain their analysis windows. No labels, account-neighbour expansion, statistical predictors or fitted values are used.

## Outputs

A deterministic snapshot ID, policy hash and JSON-compatible account records. Each record contains its dataset, exact bank/account key, scoring window, 0–100 score, band, uncapped total, immutable priority ID, policy version/hash, coverage and contribution ledger. Every family records eligible finding IDs, one selected finding ID, suppressed correlated IDs and its configured weight. Only accounts with findings receive a record; an empty result makes no statement about unscored accounts.

## Functionality

Group findings only by their explicit subject roles: forwarder, collector, distributor, payer, high-frequency account, reactivated account, temporal intermediary, cycle participant or synchronized participant. A path endpoint or shared hub is not automatically a subject. Each configured evidence family contributes its fixed weight once per account/window. The smallest finding ID is the deterministic representative; all others remain retained and reviewable. Sum family weights, cap at 100, then apply strictly increasing low/medium/high/critical band boundaries.

All feature coverage is retained, including missing history, limited graph origins and unavailable context. The separate rule service's graph-unavailable status remains visible alongside the actual graph-service coverage; the combined import preserves service/run identity rather than overwriting it.

## Errors and edge cases

Reject unknown or unconfigured rule IDs, unsupported roles, conflicting finding IDs, mixed datasets/cutoffs, findings outside the scoring window, invalid weights, repeated family assignments, invalid bands, implicit timezones and non-evidence records. Optional context needs an explicitly supported scoring contract before it can contribute; it is not silently assigned points. Duplicate identical findings are idempotent. Integrity validation checks snapshot/ledger IDs, policy identity, suppression, contribution arithmetic and bands before alert import.

Scores express fixed-policy investigation priority, never probability or guilt. Versioned weights are demonstration choices; they have not been tuned against benchmark labels.

## Acceptance criteria

Pass-through 25 + collection 15 + temporal network 30 yields 70/high. Fan-in and fan-out share one 15-point family. Reordered identical inputs give identical ledgers. Distinct banks never merge accounts sharing an account string. Missing coverage remains visible, and altered score arithmetic fails validation even when an artifact hash is recomputed.

## Data availability

Works from rule and graph findings without additional customer context. Source labels and pattern annotations remain exclusive to later evaluation.

The [alert workflow](../alerts/README.md) provides the combined snapshot import CLI and persistent evidence access. [Checked results](../../priority_alert_validation.md) document one IBM snapshot.
