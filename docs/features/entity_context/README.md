# Optional entity and account context

**Status: implementation pending.** Owner: `src/fintrace/context/`.

## Proposed interface
```text
enrich_accounts(account_keys, context_tables, reference_snapshot, cutoff) -> ContextResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

## Inputs
- Observed account registry and optional verified customers, expected-activity policies and account/entity links.
- Dated independent intelligence or explicit payment-format mappings, each with provenance and observed-at time.

## Outputs
- Context-enriched account records, deterministic discrepancy/link findings and field-level availability.
- Source references, effective periods and limitations for each context claim.

## Functionality
- Keep observed endpoint accounts distinct from verified customer identities and ownership.
- Identify shared device/IP/beneficiary links without assuming common control from a single weak link.
- Compare activity with explicit expected-activity limits only when recorded context supports the comparison.
- Assess directed exposure to independently identified entities; never seed exposure from benchmark labels.
- Treat cash-out and jurisdiction indicators as unavailable until verified channel/geography mappings exist.

## Errors and edge cases
- Absent optional tables produce unavailable status.
- Future-known intelligence is excluded at historical cutoffs.
- Stale, overlapping or conflicting references produce visible diagnostics.

## Acceptance criteria
- IBM-only input does not acquire invented names, income, countries, devices or opening dates.
- Two accounts sharing a public IP are described as a shared indicator, not confirmed common ownership.
- A reference learned after the replay cutoff does not affect that replay result.

## Data availability
Disabled by default for unsupported fields; an observed account registry alone is insufficient.
