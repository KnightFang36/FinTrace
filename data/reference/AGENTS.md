# data/reference instructions

## Purpose
Hold optional verified identity/context inputs and dated reference lists.

## Inputs
Customer profiles, entity links, source channel mappings and external reference intelligence with provenance.

## Outputs
Versioned reference snapshots and field availability metadata.

## Functionality
Record source, effective date, observed-at date, scope and source terms for each future table. Supply only context actually available for the chosen analysis cutoff. README.md documents these optional contracts; no reference tables or enrichment service are supplied yet.

## Constraints
IBM account IDs are not identities or countries. Do not invent enrichment. Sensitive reference content remains local and ignored. Screening is disabled by default.
