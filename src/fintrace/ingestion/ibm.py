"""Chunked, immutable Parquet ingestion of one verified IBM transaction CSV."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

from fintrace.ingestion.manifest import ManifestError, _source_path, verify_manifest
from fintrace.validation.transactions import validate_transaction_fields

INGESTION_VERSION = "ibm-parquet-v1"


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schemas():
    import pyarrow as pa
    common = [
        ("schema_version", pa.string()), ("run_id", pa.string()), ("dataset_id", pa.string()),
        ("transaction_id", pa.string()), ("source_file_id", pa.string()),
        ("source_record_number", pa.int64()),
    ]
    transactions = common + [
        ("source_row_hash", pa.string()), ("normalization_version", pa.string()),
        ("source_timestamp", pa.string()), ("timestamp_precision", pa.string()),
        ("occurred_at", pa.timestamp("us", tz="UTC")),
        ("sender_bank_id", pa.string()), ("sender_account_id", pa.string()),
        ("receiver_bank_id", pa.string()), ("receiver_account_id", pa.string()),
        ("amount_received", pa.decimal128(38, 8)), ("receiving_currency", pa.string()),
        ("amount_paid", pa.decimal128(38, 8)), ("payment_currency", pa.string()),
        ("payment_format", pa.string()), ("is_self_transfer", pa.bool_()),
    ]
    return {
        "transactions": pa.schema(transactions),
        "quarantine": pa.schema(common + [
            ("financial_fields_json", pa.string()),
            ("issue_codes", pa.list_(pa.string())), ("messages", pa.list_(pa.string())),
        ]),
        "labels": pa.schema(common + [("is_laundering", pa.int8())]),
        "label_issues": pa.schema(common + [("raw_label", pa.string()), ("code", pa.string())]),
    }


def _derive_accounts_and_diagnostics(transaction_path: Path, accounts_path: Path, scratch: Path) -> dict:
    import duckdb
    connection = duckdb.connect()
    try:
        connection.execute("SET memory_limit='512MB'")
        connection.execute("SET threads=2")
        connection.execute("SET temp_directory=?", [str(scratch)])
        # Detection-only Parquet is the sole input: no benchmark labels are queried.
        query = """
            WITH endpoints AS (
                SELECT schema_version, run_id, dataset_id, sender_bank_id AS bank_id,
                    sender_account_id AS account_id, occurred_at, payment_currency AS currency,
                    'sender' AS role FROM read_parquet(?)
                UNION ALL
                SELECT schema_version, run_id, dataset_id, receiver_bank_id AS bank_id,
                    receiver_account_id AS account_id, occurred_at, receiving_currency AS currency,
                    'receiver' AS role FROM read_parquet(?)
            )
            SELECT schema_version, run_id, dataset_id, bank_id, account_id,
                min(occurred_at) AS first_observed_at, max(occurred_at) AS last_observed_at,
                list_sort(list_distinct(list(currency))) AS observed_currencies,
                list_sort(list_distinct(list(role))) AS source_endpoint_roles
            FROM endpoints GROUP BY schema_version, run_id, dataset_id, bank_id, account_id
            ORDER BY bank_id, account_id
        """
        relation = connection.sql(query, params=[str(transaction_path), str(transaction_path)])
        relation.write_parquet(str(accounts_path), compression="zstd")
        duplicate_rows = connection.execute("""
            SELECT coalesce(sum(n - 1), 0) FROM (
                SELECT count(*) AS n FROM read_parquet(?)
                GROUP BY source_row_hash HAVING count(*) > 1
            )
        """, [str(transaction_path)]).fetchone()[0]
        counts = connection.execute("""
            SELECT count(*),
                strftime(min(occurred_at) AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%SZ'),
                strftime(max(occurred_at) AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%SZ'),
                coalesce(sum(CASE WHEN is_self_transfer THEN 1 ELSE 0 END), 0)
            FROM read_parquet(?)
        """, [str(transaction_path)]).fetchone()
        account_count = connection.execute("SELECT count(*) FROM read_parquet(?)",
                                           [str(accounts_path)]).fetchone()[0]
        return {
            "accepted_records": counts[0], "duplicate_financial_records": int(duplicate_rows),
            "self_transfers": int(counts[3]), "observed_accounts": account_count,
            "occurred_at_min": counts[1],
            "occurred_at_max": counts[2],
        }
    finally:
        connection.close()


def _verify_completed(target: Path, evaluation_target: Path, manifest: dict) -> dict:
    path = target / "completion.json"
    if not path.is_file():
        raise ManifestError("Existing dataset has no completion marker; refusing to overwrite")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        raise ManifestError("Unreadable completion marker") from error
    if not isinstance(result, dict) or result.get("status") != "completed":
        raise ManifestError("Invalid completion marker")
    if result.get("dataset_id") != manifest["dataset_id"] or result.get("ingestion_version") != INGESTION_VERSION:
        raise ManifestError("Existing completion marker uses different inputs or ingestion policy")
    for group, root in (("detection_artifacts", target), ("evaluation_artifacts", evaluation_target)):
        expected_files = ({"transactions.parquet", "quarantine.parquet", "accounts.parquet", "quality.json"}
                          if group == "detection_artifacts" else {"labels.parquet", "label_issues.parquet", "quality.json"})
        entries = result.get(group)
        if (not isinstance(entries, list) or len(entries) != len(expected_files)
                or any(not isinstance(entry, dict) or set(entry) != {"file", "sha256"} for entry in entries)
                or {entry["file"] for entry in entries} != expected_files):
            raise ManifestError("Incomplete artifact inventory in completion marker")
        for entry in entries:
            relative = entry["file"]
            if Path(relative).name != relative:
                raise ManifestError("Invalid artifact name in completion marker")
            artifact = root / relative
            if artifact.is_symlink() or not artifact.is_file() or _hash(artifact) != entry["sha256"]:
                raise ManifestError(f"Completed artifact integrity mismatch: {relative}")
    return {**result, "status": "reused"}


def ingest_ibm(
    manifest_path: Path, raw_root: Path, processed_root: Path, *,
    batch_size: int = 25000, progress=None,
) -> dict:
    """Normalize a verified source with exact amounts and separate label artifacts.

    Completed datasets are reused only after source and artifact verification.
    A per-dataset lock and staged publication prevent concurrent or partial imports
    from appearing complete. Neither publisher accounts nor pattern annotations
    are inputs to this function.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    if not isinstance(batch_size, int) or not 1 <= batch_size <= 1000000:
        raise ValueError("batch_size must be between 1 and 1000000")
    manifest = verify_manifest(manifest_path, raw_root)
    if manifest["normalization_version"] != "1":
        raise ManifestError("This adapter implements normalization_version=1 only")
    root = Path(processed_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for directory in (root / "datasets", root / "evaluation"):
        if directory.is_symlink():
            raise ManifestError("Artifact parent directories must not be symbolic links")
    dataset_id = manifest["dataset_id"]
    target = root / "datasets" / dataset_id
    evaluation_target = root / "evaluation" / dataset_id
    if target.is_symlink() or evaluation_target.is_symlink():
        raise ManifestError("Dataset artifact directories must not be symbolic links")
    if target.exists():
        return _verify_completed(target, evaluation_target, manifest)
    lock = root / f".{dataset_id}.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    stage = None
    published_evaluation = False
    try:
        if target.exists():
            return _verify_completed(target, evaluation_target, manifest)
        if evaluation_target.exists():
            raise ManifestError("An evaluation directory already exists without its completed dataset")
        stage = Path(tempfile.mkdtemp(prefix=".ingest-", dir=root))
        detection_stage, evaluation_stage = stage / "detection", stage / "evaluation"
        detection_stage.mkdir()
        evaluation_stage.mkdir()
        schemas = _schemas()
        paths = {
            "transactions": detection_stage / "transactions.parquet",
            "quarantine": detection_stage / "quarantine.parquet",
            "labels": evaluation_stage / "labels.parquet",
            "label_issues": evaluation_stage / "label_issues.parquet",
        }
        buffers = {name: [] for name in paths}
        counts, issue_counts = Counter(), Counter()
        source = manifest["source_files"][0]
        run_id = "ingest-" + hashlib.sha256((dataset_id + INGESTION_VERSION).encode()).hexdigest()[:24]
        common = {"schema_version": "1", "run_id": run_id, "dataset_id": dataset_id,
                  "source_file_id": source["sha256"]}
        with ExitStack() as stack:
            writers = {
                name: stack.enter_context(pq.ParquetWriter(path, schemas[name], compression="zstd"))
                for name, path in paths.items()
            }

            def flush():
                for name, records in buffers.items():
                    if records:
                        writers[name].write_table(pa.Table.from_pylist(records, schema=schemas[name]))
                        records.clear()

            source_path = _source_path(raw_root, source["relative_path"])
            with source_path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, strict=True)
                header = next(reader)
                if header != source["header"]:
                    raise ManifestError("Source header changed after verification")
                for number, row in enumerate(reader, 1):
                    counts["source_records"] += 1
                    transaction_id = hashlib.sha256(
                        json.dumps([dataset_id, source["relative_path"], number], separators=(",", ":")).encode()
                    ).hexdigest()
                    identity = {**common, "transaction_id": transaction_id, "source_record_number": number}
                    financial = row[:10]
                    # Missing/invalid labels do not reject otherwise valid financial fields.
                    candidate = financial if len(row) in (10, 11) else []
                    validation = validate_transaction_fields(
                        candidate, timezone_policy=manifest["timezone_policy"],
                        timestamp_precision=manifest["timestamp_precision"],
                    )
                    for issue in validation.issues:
                        issue_counts[f"{issue['severity']}:{issue['code']}"] += 1
                    if validation.record is not None:
                        source_hash = hashlib.sha256(
                            json.dumps(financial, separators=(",", ":")).encode()
                        ).hexdigest()
                        buffers["transactions"].append({
                            **identity, **validation.record, "source_row_hash": source_hash,
                            "normalization_version": manifest["normalization_version"],
                        })
                        counts["accepted_records"] += 1
                    else:
                        buffers["quarantine"].append({
                            **identity, "financial_fields_json": json.dumps(financial),
                            "issue_codes": [issue["code"] for issue in validation.issues],
                            "messages": [issue["message"] for issue in validation.issues],
                        })
                        counts["quarantined_records"] += 1
                    if len(row) == 11 and row[10] in ("0", "1"):
                        buffers["labels"].append({**identity, "is_laundering": int(row[10])})
                        counts["benchmark_labels"] += 1
                    else:
                        buffers["label_issues"].append({
                            **identity, "raw_label": row[10] if len(row) > 10 else None,
                            "code": "missing_or_invalid_benchmark_label",
                        })
                        counts["benchmark_label_issues"] += 1
                    if number % batch_size == 0:
                        flush()
                        if progress is not None:
                            progress(dict(counts))
                flush()
        diagnostics = _derive_accounts_and_diagnostics(
            paths["transactions"], detection_stage / "accounts.parquet", stage / "scratch",
        )
        verify_manifest(manifest_path, raw_root)
        quality = {
            "schema_version": "1", "dataset_id": dataset_id, "run_id": run_id,
            "ingestion_version": INGESTION_VERSION,
            "source_records": counts["source_records"],
            "quarantined_records": counts["quarantined_records"], **diagnostics,
            "issue_counts": dict(sorted(issue_counts.items())),
            "timestamp_policy": manifest["timezone_policy"],
            "timestamp_policy_basis": manifest.get("timezone_policy_basis", "user_declared"),
            "acquired_at": manifest["acquired_at"],
            "source_observed_at": manifest.get("observed_at"),
            "source_file": source["relative_path"],
            "source_sha256": source["sha256"],
            "timestamp_precision": manifest["timestamp_precision"],
            "observation_intervals": manifest["observation_intervals"],
            "known_gaps": manifest["known_gaps"],
            "history_eligibility": "requires_explicit_coverage" if not manifest["observation_intervals"] else "check_each_requested_window",
            "limitations": ["Observed bounds do not establish complete history.",
                            "Duplicate-content transfers are preserved.",
                            "Amounts are exact decimal(38,8); no currency conversion is performed."],
        }
        (detection_stage / "quality.json").write_text(json.dumps(quality, indent=2) + "\n")
        evaluation_report = {
            "schema_version": "1", "dataset_id": dataset_id, "run_id": run_id,
            "benchmark_labels": counts["benchmark_labels"],
            "benchmark_label_issues": counts["benchmark_label_issues"],
            "interpretation": "Transaction laundering labels, not confirmed mule-account labels.",
        }
        (evaluation_stage / "quality.json").write_text(json.dumps(evaluation_report, indent=2) + "\n")
        result = {
            "schema_version": "1", "dataset_id": dataset_id, "run_id": run_id,
            "ingestion_version": INGESTION_VERSION, "status": "completed",
            "detection_artifacts": [
                {"file": path.name, "sha256": _hash(path)} for path in sorted(detection_stage.iterdir())
            ],
            "evaluation_artifacts": [
                {"file": path.name, "sha256": _hash(path)} for path in sorted(evaluation_stage.iterdir())
            ],
        }
        (detection_stage / "completion.json").write_text(json.dumps(result, indent=2) + "\n")
        target.parent.mkdir(parents=True, exist_ok=True)
        evaluation_target.parent.mkdir(parents=True, exist_ok=True)
        evaluation_stage.rename(evaluation_target)
        published_evaluation = True
        detection_stage.rename(target)
        return result
    except BaseException:
        if published_evaluation and not target.exists():
            shutil.rmtree(evaluation_target)  # Only this call's unpublished artifacts.
        raise
    finally:
        if stage is not None:
            shutil.rmtree(stage)
        lock.unlink(missing_ok=True)
