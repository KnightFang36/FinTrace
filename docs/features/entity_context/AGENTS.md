# Optional entity and account context contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/context/`. Implementation is pending.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
