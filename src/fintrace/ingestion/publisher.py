"""Preserve publisher entity records and report explicit account-link candidates."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
from pathlib import Path

from fintrace.ingestion.audit import ACCOUNTS_HEADER, fingerprint
from fintrace.ingestion.ibm import _hash
from fintrace.ingestion.manifest import ManifestError


def reconcile_publisher_accounts(
    source_path: Path, raw_root: Path, observed_accounts: Path, processed_root: Path,
) -> dict:
    """Write a separate synthetic publisher registry and a review-only link ledger.

    Numeric zero-padding equivalence nominates candidates; it never rewrites
    detection account keys or establishes verified customer identity.
    """
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq

    source = fingerprint(source_path, raw_root)
    observed_hash = _hash(observed_accounts)
    identity = hashlib.sha256((source["sha256"] + observed_hash + "publisher-links-v1").encode()).hexdigest()
    root = Path(processed_root).resolve() / "supplemental"
    if root.is_symlink():
        raise ManifestError("Supplemental output root must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    target = root / identity
    if target.is_symlink():
        raise ManifestError("Supplemental dataset must not be a symlink")
    if target.exists():
        report = json.loads((target / "completion.json").read_text())
        artifacts = report.get("artifacts", [])
        expected = {"publisher_accounts.parquet", "account_link_candidates.parquet", "quarantine.jsonl"}
        if {item.get("file") for item in artifacts} != expected or len(artifacts) != len(expected):
            raise ManifestError("Invalid supplemental completion inventory")
        for item in artifacts:
            path = target / item["file"]
            if path.is_symlink() or _hash(path) != item["sha256"]:
                raise ManifestError("Supplemental artifact integrity mismatch")
        return {**report, "status": "reused"}

    schema = pa.schema([
        ("schema_version", pa.string()), ("run_id", pa.string()), ("dataset_id", pa.string()),
        ("source_sha256", pa.string()), ("source_record_number", pa.int64()),
        ("bank_name", pa.string()), ("bank_id", pa.string()), ("account_id", pa.string()),
        ("entity_id", pa.string()), ("entity_name", pa.string()), ("synthetic", pa.bool_()),
    ])
    with tempfile.TemporaryDirectory(prefix=".publisher-", dir=root) as temporary:
        stage = Path(temporary)
        count = rejected = 0
        with pq.ParquetWriter(stage / "publisher_accounts.parquet", schema, compression="zstd") as writer:
            with Path(source_path).open(encoding="utf-8-sig", newline="") as handle, (
                stage / "quarantine.jsonl"
            ).open("w") as quarantine:
                reader = csv.reader(handle, strict=True)
                if next(reader, None) != list(ACCOUNTS_HEADER):
                    raise ManifestError("Publisher accounts header mismatch")
                buffer = []
                for number, row in enumerate(reader, 1):
                    if len(row) != 5 or any(not item or item != item.strip() for item in row):
                        rejected += 1
                        quarantine.write(json.dumps({"source_record_number": number, "source_fields": row,
                                                     "code": "invalid_publisher_account"}) + "\n")
                        continue
                    buffer.append({
                        "schema_version": "1", "run_id": "publisher-" + identity[:24],
                        "dataset_id": "publisher-" + source["sha256"],
                        "source_sha256": source["sha256"], "source_record_number": number,
                        "bank_name": row[0], "bank_id": row[1], "account_id": row[2],
                        "entity_id": row[3], "entity_name": row[4], "synthetic": True,
                    })
                    count += 1
                    if len(buffer) == 25000:
                        writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
                        buffer.clear()
                if buffer:
                    writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
        connection = duckdb.connect()
        try:
            connection.execute("SET memory_limit='512MB'")
            connection.execute("SET threads=2")
            connection.execute("SET temp_directory=?", [str(stage / "scratch")])
            query = """
                WITH candidates AS (
                    SELECT o.schema_version, o.run_id, o.dataset_id, o.bank_id, o.account_id,
                        p.bank_id AS publisher_bank_id, p.entity_id AS publisher_entity_id,
                        p.source_record_number AS publisher_source_record_number,
                        p.source_sha256 AS publisher_source_sha256,
                        CASE WHEN p.bank_id=o.bank_id THEN 'exact_source_key'
                             WHEN p.bank_id IS NULL THEN 'unmatched'
                             ELSE 'zero_padding_candidate' END AS proposed_status,
                        count(p.account_id) OVER (PARTITION BY o.bank_id,o.account_id) AS candidate_count
                    FROM read_parquet(?) o LEFT JOIN read_parquet(?) p
                      ON o.account_id=p.account_id AND (
                        o.bank_id=p.bank_id OR (
                          regexp_full_match(o.bank_id,'[0-9]+') AND regexp_full_match(p.bank_id,'[0-9]+')
                          AND coalesce(nullif(ltrim(o.bank_id,'0'),''),'0')
                            = coalesce(nullif(ltrim(p.bank_id,'0'),''),'0')
                        )
                      )
                )
                SELECT * EXCLUDE(proposed_status),
                    CASE WHEN candidate_count>1 THEN 'ambiguous' ELSE proposed_status END AS link_status
                FROM candidates ORDER BY bank_id,account_id,publisher_source_record_number
            """
            connection.sql(query, params=[str(observed_accounts), str(stage / "publisher_accounts.parquet")]).write_parquet(
                str(stage / "account_link_candidates.parquet"), compression="zstd",
            )
            statuses = dict(connection.execute("""
                SELECT link_status,count(DISTINCT (bank_id,account_id))
                FROM read_parquet(?) GROUP BY link_status ORDER BY link_status
            """, [str(stage / "account_link_candidates.parquet")]).fetchall())
        finally:
            connection.close()
        if fingerprint(source_path, raw_root) != source or _hash(observed_accounts) != observed_hash:
            raise ManifestError("Source or observed account snapshot changed during reconciliation")
        report = {
            "schema_version": "1", "status": "completed", "snapshot_id": identity,
            "publisher_source": source, "observed_accounts_sha256": observed_hash,
            "publisher_records": count, "quarantined_publisher_records": rejected,
            "observed_account_status_counts": statuses,
            "interpretation": "Synthetic source links only; zero-padding matches are review candidates, not automatic identity joins.",
            "artifacts": [
                {"file": name, "sha256": _hash(stage / name)}
                for name in ("publisher_accounts.parquet", "account_link_candidates.parquet", "quarantine.jsonl")
            ],
        }
        (stage / "completion.json").write_text(json.dumps(report, indent=2) + "\n")
        # Rename into a fresh path; no existing completed snapshot is overwritten.
        stage.rename(target)
        # TemporaryDirectory tolerates the original temporary path no longer existing.
        return report
