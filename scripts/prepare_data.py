"""Audit, manifest, verify and normalize local IBM sources; no downloads."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintrace.ingestion.manifest import (  # noqa: E402
    ManifestError,
    VARIANTS,
    SOURCE_URL,
    create_manifest,
    verify_manifest,
    write_manifest,
)
from fintrace.ingestion.audit import audit_sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-root", type=Path, default=ROOT / "data/raw/ibm",
        help="Source directory; defaults to this repository's data/raw/ibm",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="Inventory local uploads without inferring timezone or acquisition time")
    audit.add_argument("--transactions", default="HI-Small_Trans.csv")
    audit.add_argument("--accounts")
    audit.add_argument("--patterns")
    audit.add_argument("--output", type=Path)
    create = commands.add_parser("create", help="Verify a local CSV and publish a new manifest")
    create.add_argument("source", type=Path)
    create.add_argument("--variant", choices=VARIANTS, required=True)
    create.add_argument("--acquired-at", help="Actual acquisition time with offset; omitted means unknown in manifest v2")
    create.add_argument("--timezone-basis", choices=("project_convention", "publisher_declared"))
    create.add_argument("--timezone", required=True, help="Declared source timezone, e.g. UTC")
    create.add_argument("--timestamp-precision", choices=("minute", "second"), required=True)
    create.add_argument("--source-terms", required=True, help="Terms of the exact acquired copy")
    create.add_argument("--source-url", default=SOURCE_URL)
    create.add_argument("--normalization-version", default="1")
    create.add_argument("--coverage", nargs=2, action="append", default=[], metavar=("START", "END"))
    create.add_argument("--gap", nargs=2, action="append", default=[], metavar=("START", "END"))
    create.add_argument("--output", type=Path)
    verify = commands.add_parser("verify", help="Recompute hashes and check recorded source identity")
    verify.add_argument("manifest", type=Path)
    ingest = commands.add_parser("ingest", help="Validate and normalize a manifested source into separate Parquet artifacts")
    ingest.add_argument("manifest", type=Path)
    ingest.add_argument("--processed-root", type=Path, default=ROOT / "data/processed")
    ingest.add_argument("--batch-size", type=int, default=25000)
    accounts = commands.add_parser("accounts", help="Preserve publisher metadata and report review-only account links")
    accounts.add_argument("observed_accounts", type=Path)
    accounts.add_argument("--source", default="HI-Small_accounts.csv")
    accounts.add_argument("--processed-root", type=Path, default=ROOT / "data/processed")
    args = parser.parse_args(argv)
    try:
        raw_root = args.raw_root.resolve(strict=True)
        if args.command == "accounts":
            from fintrace.ingestion.publisher import reconcile_publisher_accounts
            from fintrace.ingestion.manifest import _source_path
            result = reconcile_publisher_accounts(_source_path(raw_root, args.source), raw_root,
                                                 args.observed_accounts, args.processed_root)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "audit":
            report = audit_sources(raw_root, args.transactions, args.accounts, args.patterns)
            payload = json.dumps(report, indent=2) + "\n"
            if args.output:
                with args.output.open("x", encoding="utf-8") as handle:
                    handle.write(payload)
            print(payload, end="")
            return 0
        if args.command == "ingest":
            from fintrace.ingestion.ibm import ingest_ibm
            def progress(counts):
                if counts["source_records"] % 250000 == 0:
                    print(json.dumps({"progress": counts}), file=sys.stderr, flush=True)
            result = ingest_ibm(args.manifest, raw_root, args.processed_root,
                                batch_size=args.batch_size, progress=progress)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "create":
            manifest = create_manifest(
                args.source, raw_root, variant=args.variant, acquired_at=args.acquired_at,
                timezone_policy=args.timezone, timestamp_precision=args.timestamp_precision,
                source_terms=args.source_terms, source_url=args.source_url,
                normalization_version=args.normalization_version,
                timezone_policy_basis=args.timezone_basis,
                observation_intervals=[{"start": start, "end": end} for start, end in args.coverage],
                known_gaps=[{"start": start, "end": end} for start, end in args.gap],
            )
            destination = write_manifest(
                manifest, args.output or raw_root / "manifest.json", raw_root,
            )
            status = "created"
        else:
            manifest = verify_manifest(args.manifest, raw_root)
            destination = args.manifest.resolve(strict=True)
            status = "verified"
    except (ManifestError, OSError, ValueError, csv.Error) as error:
        print(f"Data preparation failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": status,
        "dataset_id": manifest["dataset_id"],
        "manifest_path": str(destination),
        "source_files": len(manifest["source_files"]),
        "coverage": "declared" if manifest["observation_intervals"] else "unknown",
        "scope": "source header, bytes and declared metadata; no financial row validation",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
