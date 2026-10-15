# data instructions

## Purpose
Separate immutable source input, generated records and optional independently sourced references.

## Inputs
Locally acquired IBM files, normalization outputs and dated reference data.

## Outputs
Local data directory boundaries and documented provenance.

## Functionality
raw/ibm contains publisher files; processed contains derived artifacts and local database; reference contains explicitly sourced enrichment. All data files remain ignored by Git except directory instructions.

## Constraints
Do not fabricate customer profiles. Keep benchmark labels separate from detection-facing records. Record acquisition terms before redistribution.
