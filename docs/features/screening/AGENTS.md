# Optional reference-list screening contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/screening/`. Implementation is pending.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
