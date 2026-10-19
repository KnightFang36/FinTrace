# FinTrace

A local banking investigation workspace using IBM's fully synthetic AML transaction data. It combines explicit transaction rules, bounded temporal NetworkX graphs and fixed-policy review priorities. No machine learning is used.

The seven workspace pages cover overview, alert review, account evidence, network exploration, cases, reports and historical replay. Findings are suspicions for analyst review; priorities are not probabilities or determinations of guilt.

## Run locally

Requires Python 3.11 or newer. Use the existing `.venv` if already installed:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r config/frontend-requirements.txt
python -m pip install -e '.[dev]'
streamlit run app/streamlit_app.py
```

The dashboard reads `data/processed/alerts.duckdb` and completed analysis artifacts. An empty store displays setup instructions. Override local paths with `FINTRACE_ALERT_DATABASE`, `FINTRACE_PROCESSED_ROOT` and `FINTRACE_EXPORT_ROOT` (default `outputs/`). Browsing does not write analyst actions.

## Working features

- Streaming IBM CSV normalization, provenance checks, exact account identifiers, financial validation, quarantine and row lineage.
- Six transaction rules: observed pass-through, fan-in, fan-out, repeated payments, bursts and dormant activation. Historical rules require declared observation coverage.
- Bounded chronological chains, cycles and coordinated groups; descriptive graph statistics and a default combined network of the top ten active-alert accounts, with bounded neighbourhoods and visible limits.
- Auditable priority contributions, deduplicated persistent alerts and version-checked review transitions.
- Snapshot account dossiers and graph-window transfer timelines.
- Versioned cases with frozen evidence, notes, assignments, closure/reopen and append-only audit history.
- Verified local JSON, CSV, HTML and PNG reports, plus ZIP downloads.
- Historical cutoff replay with isolated alerts, durable checkpoints and validated resume.

Account timelines cover the selected graph window. Independent customer context/screening, benchmark metrics, full-history account queries and a combined pipeline are outside the maintained scope. IBM labels and pattern annotations remain isolated ingestion artifacts and never feed these working services.

## Local data workflow

Keep source files in `data/raw/ibm/`; all source datasets and generated artifacts remain ignored by Git. Both the existing HI-Small and HI-Medium datasets are preserved. HI-Medium has 31,898,238 accepted transfers and 2,077,023 observed account keys; this is ingestion coverage, not full-history detection.

For the existing HI-Medium manifest:

```bash
python scripts/prepare_data.py verify data/raw/ibm/manifest-hi-medium.json
python scripts/prepare_data.py ingest data/raw/ibm/manifest-hi-medium.json
```

For a new source, use `python scripts/prepare_data.py create --help` to declare its variant, timezone, timestamp precision and actual source terms before ingestion. Do not overwrite existing manifests or infer complete observation history from file dates. UTC in the current manifests is an explicit project convention, not a publisher timezone claim.

Run bounded snapshots with an exclusive cutoff, then import their returned directories:

```bash
python scripts/run_rules.py PATH_TO_TRANSACTIONS_PARQUET --cutoff 2022-09-03T06:00:00Z
python scripts/run_graphs.py PATH_TO_TRANSACTIONS_PARQUET --cutoff 2022-09-03T06:00:00Z
python scripts/manage_alerts.py import \
  --rules-run PATH_TO_COMPLETED_RULE_RUN \
  --graph-run PATH_TO_COMPLETED_GRAPH_RUN \
  --actor local-investigator --at AUDIT_TIME_WITH_TIMEZONE
```

Placeholders above must be replaced with actual local paths and audit time. The transaction input is the completed `data/processed/datasets/<dataset_id>/transactions.parquet`. Budgets fail oversized input rather than sampling. Rule settings, graph bounds, priority weights and alert policy live in `config/`. Existing disabled optional-rule sections are retained only for old policy/checkpoint compatibility; they cannot enable removed services.

Cases, reports and replay are available in the dashboard and through `scripts/manage_cases.py`, `scripts/export_reports.py` and `scripts/run_replay.py`. Each command provides `--help`; detailed interfaces and limits are in [service contracts](docs/services.md).

## Verify and navigate

```bash
python scripts/check_scaffold.py
python -m pytest tests -q
```

- [AGENTS.md](AGENTS.md): project-wide development instructions.
- [Service contracts](docs/services.md): callable interfaces, inputs, outputs, limits and errors.
- [Architecture](docs/architecture.md) and [data contracts](docs/data_contracts.md): service boundaries and record schemas.
- [Local validation](docs/validation.md): measured dataset, dashboard and workflow verification.

`app/` contains Streamlit presentation, `src/fintrace/` contains domain services, `scripts/` contains operational commands, and `tests/` contains synthetic verification fixtures. Data and exports stay local; the application does not submit reports or restrict accounts.

The retained [presentation PDF](docs/PRESENTATION.pdf) and [editable slides](docs/PRESENTATION.pptx) describe the earlier four-page demo. They are historical presentation assets; use the service list above for current functionality.
