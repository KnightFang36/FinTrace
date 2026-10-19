# FinTrace project instructions

This is the single instruction file for the repository. Maintain the implemented local investigation system; do not restore removed feature scaffolds unless requested. Setup and commands belong in [README.md](README.md), callable contracts in [docs/services.md](docs/services.md), shared schemas in [docs/data_contracts.md](docs/data_contracts.md), and measured verification in [docs/validation.md](docs/validation.md).

## Scope and ownership

Use explicit transaction rules, deterministic historical comparisons, NetworkX algorithms and fixed, auditable priority weights. **Exclude all machine learning**, fitted predictors, embeddings and generated prose. The working services are ingestion/validation, transaction rules, temporal graphs, priorities, audited alerts, snapshot account/network investigation, cases, local reports and historical replay. Benchmark evaluation, independent context/screening, general orchestration and full-history account querying are outside the maintained scope.

Business logic belongs in `src/fintrace`; Streamlit in `app` presents service results and explicit analyst actions. Keep ingestion, rules, graphs, scoring, alert lifecycle, storage, cases, reports and replay separate. CLI wrappers in `scripts` delegate to domain services. Policy files in `config` declare demonstration thresholds, not legal requirements.

## Data and evidence invariants

- Preserve exact string bank/account pairs, source row lineage and duplicate payments. Never rewrite identifiers to match publisher metadata; reconciliation candidates remain review-only.
- Quarantine invalid financial values/timestamps without rounding or silent repair. Use fixed-precision Decimal amounts; keep paid/received values and currencies separate.
- Preserve original timestamp representation/precision and require an explicit timezone policy. Unknown source coverage stays unknown; first observed activity does not establish account opening or dormancy.
- IBM labels and supplied pattern annotations remain in isolated ingestion artifacts. No detection, scoring, investigation, report or replay service may read them. Do not delete retained label artifacts: completed ingestion inventories verify them on reuse.
- Evidence must precede the exclusive analysis cutoff. Earlier replay outputs must not change because of future records. Temporal evidence paths require strictly increasing timestamps; tied events do not prove transfer order.
- Bound input size, path depth, cycle search, neighbour expansion and rendered graphs. Fail oversized inputs or disclose incomplete searches; never silently sample.
- Missing customer identities, ownership, devices, expected income and independent intelligence remain unavailable. Do not infer these from synthetic account metadata.
- Findings are suspicions for review; scores are fixed-policy priorities, never probabilities or guilt determinations. Do not claim exact source-of-funds attribution or confirmed mule status.
- Keep all local datasets, generated artifacts and analyst history unless explicitly authorized to remove them. Do not download or commit source datasets, DuckDB files, exports, caches, credentials or screenshots.

## Service constraints

Verify completed input manifests, label-free schemas, dataset/cutoff/policy identities and artifact hashes before reuse. Incomplete writes must not appear complete. Source data is immutable; read-only dashboard browsing must not create stores or outputs.

Alert and case writes require explicit actor/time/reason and expected-version checks. Case request IDs are idempotent; retain immutable versions and append-only audit events. Never fabricate analyst actions in the uploaded-data store. Reports resolve source evidence, escape HTML, neutralize spreadsheet formulas and publish atomically. Replay reuses bounded batch services, commits isolated alerts before checkpoint advancement, and rejects changed source/policy/audit identities.

Preserve immutable run compatibility when cleaning code: existing disabled optional-rule keys remain accepted in version-1 policy files so retained checkpoints can resume with their original policy bytes. Enabling a removed optional service must fail explicitly. No reports are transmitted, regulatory submissions filed or accounts frozen. No automatic deployment or external notifications.

## Verification and documentation

Keep one root `AGENTS.md` and one root `README.md`; avoid recreating per-folder instruction or README files. Update the consolidated contracts when behavior changes. Preserve temporal, currency, lineage, evidence, persistence and UI tests. Use small synthetic fixtures for writes.

Run `python scripts/check_scaffold.py` for structure, Python syntax, TOML, dependency and local-link checks. Run relevant Pytest checks for implementation changes; run the full suite for cross-cutting cleanup. Structure checks alone do not prove runtime functionality. Never report removed or unavailable services as implemented.
