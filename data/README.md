# Data foundation

This folder separates immutable IBM source files, generated analysis artifacts, and optional verified references. **Provenance and upload auditing are implemented; transaction normalization and detection remain pending. Source datasets are local and excluded from Git.**

| Location | Input | Output / responsibility |
| --- | --- | --- |
| [raw/ibm](raw/ibm/README.md) | Separately acquired IBM transaction CSV | Immutable source plus a locally generated manifest |
| [processed](processed/README.md) | Future validated ingestion and analysis results | Versioned normalized records and evidence; separate evaluation-only labels |
| [reference](reference/README.md) | Optional independently sourced context | Versioned customer/entity/reference data with explicit availability |
| [manifest.schema.json](manifest.schema.json) | A generated manifest | Version-1 shape; runtime also checks semantic constraints |
| [manifest.template.json](manifest.template.json) | Human-readable field template | Documentation only; placeholders deliberately fail runtime validation |

## Implemented functionality

Run `python3 scripts/prepare_data.py --help` from the repository root. This standard-library tool needs no application dependencies.

It verifies the exact ordered IBM CSV header, preserving both columns named Account; computes a streaming SHA-256 hash and byte count; records acquisition/source terms and explicit IANA timezone interpretation; and writes a new manifest without replacing existing files. Verification recomputes the header and checksum. Sources remain inside the selected raw root; direct symbolic-link inputs and path traversal are rejected.

It performs no downloads, transaction-row validation, value normalization, customer inference, label extraction, or detection. A matching local checksum establishes continuity with the recorded file, not publisher authenticity or completeness.

## Workflow

Before creating a manifest, inventory the transaction CSV and optional supplemental files without inferring their timezone or acquisition date:

```bash
python3 scripts/prepare_data.py audit --accounts HI-Small_accounts.csv --patterns Pattern.txt \
  --output data/raw/ibm/upload-audit.json
```

The audit streams all CSV records, verifies source headers and checksums, counts malformed row widths and pattern-block boundaries, and reports source timestamp strings and payment categories. This is not financial validation or proof of complete observation coverage. The output destination must be new. Pattern metadata remains explicitly evaluation-only.

1. Acquire HI-Small separately from the publisher-linked distribution in [the dataset guide](../docs/dataset.md).
2. Place the original transaction CSV inside data/raw/ibm without editing it.
3. Record the actual acquisition timestamp and terms of that copy. Establish explicit timezone interpretation and source precision.
4. Create the manifest using the command below.
5. Verify the manifest before later ingestion.
6. Keep all publisher files and generated manifests local and ignored by Git.

The following values are examples. Replace acquisition date, timezone interpretation, precision, and terms with actual declarations for your copy. UTC here is an example, not a claim about the publisher's timezone.

```bash
python3 scripts/prepare_data.py create data/raw/ibm/HI-Small_Trans.csv \
  --variant HI-Small \
  --acquired-at '2026-10-15T12:00:00+00:00' \
  --timezone UTC \
  --timestamp-precision minute \
  --source-terms 'CDLA-Sharing-1.0; record the terms of the exact acquired copy'

python3 scripts/prepare_data.py verify data/raw/ibm/manifest.json
```

Create defaults to data/raw/ibm/manifest.json. Use --output for a new version; existing output is never overwritten. --raw-root before the subcommand supports another explicitly chosen local source directory. The CLI returns JSON on success and exit code 2 on invalid inputs, changed sources, missing files, or an existing destination.

## Observation coverage and identity

No coverage is inferred from file dates or transaction minima/maxima. Omitted coverage produces an empty observation_intervals list meaning unknown coverage; historical rules must then remain unavailable.

Use repeated --coverage START END declarations only for independently established observation horizons. Use --gap START END for known gaps. Endpoints require ISO timestamps with offsets; intervals are half-open, sorted and non-overlapping. When coverage is supplied, gaps must fall inside it. These declarations are metadata, not a statement that the source has been audited for every expected transaction.

dataset_id hashes source-relative path, content hash/size/header, variant, timezone, precision, declared coverage/gaps, and normalization version. Acquisition timestamp and source terms remain provenance fields but do not change content identity. Version 1 supports one transaction CSV per manifest.

The template is not a real manifest and must not be passed to ingestion. Use the CLI to generate actual hashes and identity.

## Verification

From the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/unit -p 'test_data_manifest.py' -v
python3 -m unittest discover -s tests/integration -p 'test_prepare_data_cli.py' -v
python3 scripts/check_scaffold.py
```

Tests use temporary handcrafted examples, never actual IBM records. Detection-facing normalized files and evaluation-label separation remain implementation work for the ingestion branch.
