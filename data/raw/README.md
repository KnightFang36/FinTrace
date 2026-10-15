# Raw inputs

Inputs are original publisher files and acquisition declarations. Outputs are immutable source identities used by later ingestion.

Place IBM files in [ibm](ibm/README.md). Preserve original bytes and names, record where and when they were acquired, and never clean the source in place. The provenance command hashes bytes and verifies the CSV header; it does not assess transaction validity.

Source CSVs and generated manifests are ignored by Git. Only this README and folder instructions are tracked here. No source download is performed automatically. See [data workflow](../README.md).
