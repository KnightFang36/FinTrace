# data/raw/ibm instructions

## Purpose
Hold locally acquired IBM synthetic AML source files.

## Inputs
HI-Small transaction CSV, acquisition manifest and optional publisher pattern annotations.

## Outputs
Verified source file references consumed by ingestion; pattern annotations consumed only by evaluation.

## Functionality
Validate the ordered header with its two Account columns, preserve original record order and record the exact dataset variant and source terms.

## Constraints
No data is bundled by this scaffold. Treat all records as synthetic. Do not pass Is Laundering or pattern annotations to detectors. Raw files stay immutable and ignored.
