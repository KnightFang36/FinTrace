# Optional entity and account context implementation instructions

## Purpose
Own the source service described in `docs/features/entity_context/README.md`. Modules are placeholders until implemented.

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

## Module responsibilities
- `entities.py`: Optional verified customer, shared-entity and reference-context enrichment.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
