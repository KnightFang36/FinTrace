# Optional reference-list screening implementation instructions

## Purpose
Own the source service described in `docs/features/screening/README.md`. Modules are placeholders until implemented.

## Inputs
- Verified entity identities and dated external reference-list snapshots.
- Explicit normalized-name/identifier comparison rules and reference provenance.

## Outputs
- Candidate matches with matched fields, reference record IDs, list date and review status.
- Unavailable/no-match/partial-match distinctions and coverage diagnostics.

## Functionality
- Keep screening separate from transaction-pattern findings and priority unless an explicit policy connects them.
- Use exact identifiers or transparent configured text-normalization comparisons; no opaque matching service.
- Require human review of ambiguous names and distinguish PEP status from sanctions designation.
- Retain list version and information-availability dates for historical analysis.

## Module responsibilities
- `service.py`: Optional transparent reference-list candidate matching.

## Implementation constraints
Follow root invariants and shared records. Implement the feature contract's failure cases and acceptance examples. Keep labels out of this service entirely. Persist source evidence and explicit coverage; do not conceal insufficient input as no suspicious activity. Do not add business logic to the dashboard. Update docs and relevant tests with implementation.
