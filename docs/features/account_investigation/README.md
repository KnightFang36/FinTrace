# Account investigation

**Status: implementation pending.** Owner: `src/fintrace/investigations/`.

## Proposed interface
```text
get_account_dossier(account_key, time_range, cutoff, filters) -> AccountDossier
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Unknown account returns an explicit not-found result.
- Missing profile/context appears unavailable, not as zero income or unknown-country risk.
- No balances are reconstructed as actual bank balances from incomplete transaction history.

## Acceptance criteria
- Selecting a finding exposes the exact supporting transfers.
- Multi-currency totals remain separate.
- Ordinary account views never expose benchmark laundering labels.

## Data availability
Core feature; depends on stored analysis outputs.
