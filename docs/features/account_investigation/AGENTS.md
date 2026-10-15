# Account investigation contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/investigations/`. Snapshot dossiers and graph-window timelines are implemented; full-history queries remain pending.

## Inputs
- Structured account identity, time range, analysis run and supported filters.
- Label-free transactions, findings, priority snapshots and optional verified context.

## Outputs
- Account summary, incoming/outgoing timeline, counterparties, currency-specific totals and observed activity changes.
- Linked alerts, evidence, coverage limitations and explanations.

## Functionality
- Preserve original evidence references while providing filterable views.
- Display first observed activity distinctly from verified account opening date.
- Explain each priority contribution using measurements and the underlying transactions.
- Use only analysis-run data available at the selected cutoff; disclose filtered and omitted records.

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
