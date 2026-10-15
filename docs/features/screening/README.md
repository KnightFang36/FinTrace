# Optional reference-list screening

**Status: implementation pending.** Owner: `src/fintrace/screening/`.

## Proposed interface
```text
screen_entities(entities, reference_snapshot, screening_policy, cutoff) -> ScreeningResult
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- IBM bank/account IDs alone are insufficient and produce unavailable status.
- Do not assert a person is sanctioned based on a name-only candidate.
- Missing/stale lists and mismatched identity fields are explicit limitations.

## Acceptance criteria
- IBM-only input leaves screening disabled/unavailable.
- A name-only candidate remains unconfirmed.
- A future list entry is excluded from an earlier historical cutoff.

## Data availability
Disabled by default; independent identity and reference data required.
