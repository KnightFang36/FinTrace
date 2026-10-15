# data/raw/ibm instructions

## Purpose
Hold locally acquired IBM synthetic AML source files.

## Inputs
HI-Small transaction CSV, acquisition manifest and optional publisher pattern annotations.

## Outputs
Verified source file references consumed by ingestion; pattern annotations consumed only by evaluation.

## Functionality
Use scripts/prepare_data.py to validate the ordered header with its two Account columns, hash original bytes and record the exact dataset variant, acquisition/source terms, explicit source timezone/precision and observation declarations. See README.md and data/README.md. The tool never overwrites an existing manifest or infers complete history from observed timestamps.

## Constraints
No data is bundled by this scaffold. Treat all records as synthetic. Do not pass Is Laundering or pattern annotations to detectors. Raw files stay immutable and ignored.
