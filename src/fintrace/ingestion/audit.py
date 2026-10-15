"""Read-only inventory of uploaded files; no timezone or acquisition inference."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from fintrace.ingestion.manifest import ManifestError, _source_path, inspect_source

ACCOUNTS_HEADER = ("Bank Name", "Bank ID", "Account Number", "Entity ID", "Entity Name")


def fingerprint(path: Path, raw_root: Path) -> dict:
    """Hash a supplemental source without changing it or interpreting its records."""
    root = Path(raw_root).resolve(strict=True)
    supplied = Path(path)
    if supplied.is_symlink():
        raise ManifestError("Source files must not be symbolic links")
    resolved = supplied.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ManifestError("Source must be inside raw_root")
    resolved = _source_path(root, resolved.relative_to(root).as_posix())
    before = resolved.stat()
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = resolved.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
    ):
        raise ManifestError("Source changed during fingerprinting")
    return {"relative_path": resolved.relative_to(root).as_posix(),
            "sha256": digest.hexdigest(), "byte_count": after.st_size}


def audit_sources(raw_root: Path, transactions: str, accounts: str | None = None,
                  patterns: str | None = None) -> dict:
    """Count records and inspect source shapes, keeping supplemental data separate.

    Time bounds are lexical source strings, not UTC instants or coverage proof.
    This inventory does not substitute for a manifest or financial validation.
    """
    root = Path(raw_root).resolve(strict=True)
    path = _source_path(root, transactions)
    transaction_source = inspect_source(path, root)
    formats, currencies = Counter(), Counter()
    rows = malformed = 0
    minimum = maximum = None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader)
        for row in reader:
            rows += 1
            if len(row) != 11:
                malformed += 1
                continue
            minimum = row[0] if minimum is None else min(minimum, row[0])
            maximum = row[0] if maximum is None else max(maximum, row[0])
            formats[row[9]] += 1
            currencies[row[8]] += 1
    if inspect_source(path, root) != transaction_source:
        raise ManifestError("Transaction source changed during audit")
    result = {
        "schema_version": "1", "observed_at": datetime.now(timezone.utc).isoformat(),
        "acquired_at": None, "timezone_policy": None, "observation_coverage": "unknown",
        "transactions": {**transaction_source, "record_count": rows,
                         "wrong_width_records": malformed,
                         "source_timestamp_min": minimum, "source_timestamp_max": maximum,
                         "payment_formats": dict(sorted(formats.items())),
                         "payment_currencies": dict(sorted(currencies.items()))},
        "limitations": ["Observed timestamp bounds are not complete observation intervals.",
                        "Hashes record local file identity, not publisher authenticity.",
                        "Acquisition time and source timezone have not been inferred."],
    }
    if accounts:
        account_path = _source_path(root, accounts)
        source = fingerprint(account_path, root)
        count = invalid = 0
        with account_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            if next(reader, None) != list(ACCOUNTS_HEADER):
                raise ManifestError("Publisher accounts header mismatch")
            for row in reader:
                count += 1
                invalid += len(row) != 5 or any(not field.strip() for field in row)
        if fingerprint(account_path, root) != source:
            raise ManifestError("Accounts source changed during audit")
        result["publisher_accounts"] = {
            **source, "header": list(ACCOUNTS_HEADER),
            "record_count": count, "malformed_records": invalid,
            "join_policy": "No implicit bank-ID normalization; preserve source strings.",
        }
    if patterns:
        pattern_path = _source_path(root, patterns)
        source = fingerprint(pattern_path, root)
        starts = ends = transfers = invalid = 0
        active = False
        with pattern_path.open(encoding="utf-8-sig", newline="") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                if text.startswith("BEGIN LAUNDERING ATTEMPT"):
                    invalid += active
                    active = True
                    starts += 1
                elif text.startswith("END LAUNDERING ATTEMPT"):
                    invalid += not active
                    active = False
                    ends += 1
                else:
                    transfers += 1
                    invalid += not active or len(next(csv.reader([text]))) != 11
        invalid += active
        if fingerprint(pattern_path, root) != source:
            raise ManifestError("Pattern source changed during audit")
        result["evaluation_only_patterns"] = {
            **source, "attempts_started": starts, "attempts_ended": ends,
            "annotated_rows": transfers, "malformed_records": invalid,
            "role": "Evaluation only; never an input to detection or entity intelligence.",
        }
    return result
