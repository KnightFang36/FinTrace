# Account investigation

**Status: snapshot evidence dossier and graph-window transfers implemented.** Full-history Parquet queries and verified customer/profile context remain pending. Owner: `src/fintrace/investigations/`.

## Implemented interface

```python
get_account_dossier(account_key, model, graph=None) -> dict | None
```

## Inputs

An exact bank/account mapping or AccountKey, a validated dashboard model from the selected priority snapshot, and optional verified graph JSON linked to that snapshot. The Streamlit account page calls this service; it does not join raw/evaluation data.

## Outputs

Account priority, explicit subject findings, linked alerts, graph-window incoming/outgoing transaction timeline, separate currency totals, source-scope limitations and missing-profile status. Amounts remain decimal text; totals use 60-digit Decimal arithmetic. No inferred bank balance, ownership, income, account opening date or customer identity is displayed.

## Functionality

Keep all source finding/transaction IDs available for review. Totals describe only observed graph-window transactions touching the exact account. Rule evidence may include historical references outside that interval; the view states this limitation. The frontend shows at most 500 timeline rows and discloses omitted rows. First observed transfers are not verified account age. Score-family contributions retain correlated suppressed evidence.

## Errors and edge cases

Unknown account returns None; identical account strings at different banks remain distinct. Missing graph input yields findings/priority with no invented transaction totals. Verified context is explicitly unavailable. This API assumes graph input already passed the dashboard's graph identity/integrity boundary; callers must not pass unrelated raw graphs.

## Acceptance criteria

Finding expansions reveal exact evidence references, measured values and policy thresholds. Graph transfers preserve timestamps, parallel IDs and currency-specific amounts. Large Decimal totals remain exact. Ordinary screens never expose benchmark labels. Missing profile and full-history coverage remain visible.

## Data availability

Works with imported rule/graph outputs and stored priorities. Rule-only imports support evidence references without a graph transfer timeline. Customer KYC, true balances and account opening dates are not supplied by this source.
