# data instructions

## Purpose
Separate immutable source input, generated records and optional independently sourced references.

## Inputs
Locally acquired IBM files, normalization outputs and dated reference data.

## Outputs
Local data directory boundaries and documented provenance.

## Functionality
raw/ibm contains publisher files and generated provenance manifests; processed reserves derived artifacts and a local database; reference reserves explicitly sourced enrichment. README files, manifest.schema.json, manifest.template.json and folder instructions are tracked. Actual source/reference data and generated manifests remain ignored.

## Constraints
The ingest command now generates validated label-free transaction/account Parquet and isolated evaluation artifacts. The accounts command preserves publisher-supplied synthetic metadata and review-only link candidates. Do not treat numeric bank-ID padding differences as permission to rewrite detection identities.

Do not fabricate customer profiles. Keep benchmark labels separate from detection-facing records. Record acquisition terms before redistribution. Follow README.md for the implemented prepare_data.py create/verify workflow. Source checks cover headers and file bytes, not transaction-row validity or publisher authenticity. Templates contain placeholders and must not be treated as real manifests.
