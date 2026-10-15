# outputs instructions

## Purpose
Contain locally generated evidence bundles and graph exports.

## Inputs
Frozen report snapshots and an export manifest.

## Outputs
CSV, JSON, HTML, PNG and their hashes/provenance.

## Functionality
Organize output by report/run identity so exported evidence can be reconciled against immutable source snapshots.

## Constraints
No reports exist in the scaffold. Keep generated artifacts ignored. Do not email, publish or file reports automatically. Escape HTML and neutralize spreadsheet formulas.
