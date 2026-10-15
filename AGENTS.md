# Project instructions

## Purpose and scope
Implement the documented FinTrace banking investigation system against IBM's fully synthetic AML benchmark. Data preparation, transaction rules, bounded temporal graphs, fixed-policy priorities and persistent audited alerts and the core Streamlit investigation workspace are implemented; the remaining feature contracts explicitly mark pending services.

The user's instruction is authoritative: **exclude all machine-learning functionality**. Use explicit transaction rules, deterministic historical comparisons, NetworkX algorithms and auditable policy weights. Do not add Scikit-learn, fitted predictors, embeddings, automated prose generation, or similar features.

## Inputs
IBM source files and a provenance manifest; versioned TOML policies; optional independently sourced context; analyst actions. Read the relevant feature specification and folder instructions before modifying a module.

## Outputs
Normalized transaction/account records, validation diagnostics, evidence-backed findings, priority scores, alerts, cases, reports and benchmark measurements. Shared schemas are specified in `docs/data_contracts.md`.

## Functionality and ownership
Keep ingestion, quality checks, rules, graph analysis, priority scoring, alert lifecycle, investigation views, case workflow, storage, reports, replay and evaluation separate. Business logic belongs in `src/fintrace`; Streamlit presents service outputs.

## Required invariants
- Account keys include bank and account identifiers, both stored as strings.
- Preserve source row lineage and duplicate transactions unless an explicit ingestion policy establishes that an import is repeated.
- Quarantine invalid rows; do not silently fix financial values or timestamps.
- Amounts use declared fixed precision and remain separated by currency.
- Preserve original timestamp representation and precision. Require a timezone policy rather than assuming UTC.
- IBM laundering labels and supplied pattern annotations belong exclusively to benchmark evaluation. No detector or user-facing score may read them.
- Evidence uses only records available at the analysis cutoff. Earlier replay results must not change because of future records.
- Ordinary graph reachability is not a temporal transfer path; all evidence paths need ordered timestamps.
- Bound cycle searches, path depth, neighbour expansion and rendered graph size; disclose incomplete results.
- Context unavailable in IBM is optional and explicitly absent, never fabricated.
- An alert is a suspicion for review. Do not claim guilt, exact source-of-funds attribution, or confirmed mule status.
- Scores are fixed-policy review priorities, never probabilities.
- Do not transmit reports, file regulatory submissions, or freeze accounts.
- Do not download or commit source datasets as part of routine source changes.

## Working agreements
Every maintained project directory must have its own `AGENTS.md` with purpose, input/output contracts, functionality, and local constraints. Feature contract directories also specify proposed callable interfaces, examples, errors and acceptance criteria. Update those contracts with implementation changes.

Keep scaffolds visibly marked pending. Add meaningful temporal, currency, lineage and evidence tests when implementing behaviour. Run `python scripts/check_scaffold.py` for documentation/structure changes; run relevant Pytest checks after implementation exists. Do not report absent tests or placeholder modules as completed functionality.

## Useful references
- `README.md`: approved scope and setup.
- `docs/data_contracts.md`: shared records and isolation boundaries.
- `docs/features/*/README.md`: feature inputs, outputs and behaviour.
- `config/`: illustrative policy, not jurisdictional requirements.
