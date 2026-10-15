# Implementation roadmap

The scaffold and local source-manifest create/verify tool are available. Phase 1 is partially implemented: source header/checksum/provenance checks exist, while normalization, financial row validation and storage remain pending. No later phase is completed by the existence of placeholder modules.

| Phase | Deliverables | Completion evidence |
| --- | --- | --- |
| 1. Data foundation | Manifest, positional CSV adapter, fixed-precision schema, observed accounts, quarantine and storage | Source lineage preserved; identifier/currency/time boundary tests; labels physically separated |
| 2. Transaction rules | Pass-through, fan-in/out, bursts, observed dormancy and repeated splitting | Positive and legitimate counterexamples; insufficient-history and mixed-currency checks |
| 3. Temporal graphs | MultiDiGraph, bounded chains/cycles, coordinated groups and descriptive metrics | Time-order checks; tie handling; bounded searches; evidence transaction mapping |
| 4. Priority and alerts | Versioned fixed weights, correlated-evidence caps, deduplicated alert lifecycle | Contribution arithmetic and repeat-run idempotency verified |
| 5. Investigation and cases | Account dossier, network service, audit-preserving case persistence | Traceable evidence and legal lifecycle transitions verified |
| 6. Dashboard and exports | Streamlit overview, queue, account/network pages, cases and safe export | UI displays real service outputs; truncation/coverage visible; exports reproducible |
| 7. Replay and evaluation | Cutoff-isolated replay, checkpoints and frozen benchmark evaluation | No future-record leakage; labels unavailable to detectors; repeatable metrics |
| 8. Optional context | Verified customer/link data, dated intelligence and reference screening | Explicit data contracts met; absent context stays unavailable |

## Design decisions already fixed
IBM synthetic benchmark; explicit rules and NetworkX; transparent additive priority; no machine-learning features; no fabricated customer identities; no automatic blocking or regulatory submission.

## Decisions to resolve using actual data
Timestamp interpretation, precision and coverage; feasible historical windows; verified channel mapping; runtime budgets; eligible currency handling; exact optional reference sources.

All policy defaults in `config/` are illustrative starting values, not validated detection performance or legal thresholds.
