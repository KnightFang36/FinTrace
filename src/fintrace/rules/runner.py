"""Bounded rule snapshots from verified detection-only Parquet artifacts."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from datetime import timedelta
from pathlib import Path

from fintrace.contracts import AccountKey, TRANSACTION_FIELDS, TRANSACTION_METADATA, utc_instant
from fintrace.rules.engine import evaluate_rules
from fintrace.rules.policy import CORE_RULES, execution_limits, load_policy


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_detection_snapshot(transactions_path, cutoff, *, start=None, max_records, subject_accounts=()):
    """Run one explicit cutoff, never opening labels or pattern annotations."""
    import pyarrow as pa
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq

    path = Path(transactions_path)
    if path.name != "transactions.parquet" or path.is_symlink():
        raise ValueError("Use the completed detection dataset's transactions.parquet")
    if "evaluation" in path.parts:
        raise ValueError("Evaluation artifacts cannot be used for rule detection")
    parent = path.parent
    completion_path, quality_path = parent / "completion.json", parent / "quality.json"
    if completion_path.is_symlink() or quality_path.is_symlink():
        raise ValueError("Input metadata must not be symbolic links")
    completion = json.loads(completion_path.read_text())
    if not isinstance(completion, dict) or completion.get("status") != "completed":
        raise ValueError("Input dataset is not complete")
    inventory = {item["file"]: item["sha256"] for item in completion["detection_artifacts"]}
    hashes = {}
    for name in ("transactions.parquet", "quality.json"):
        actual = _hash(parent / name)
        if actual != inventory.get(name):
            raise ValueError(f"Detection input integrity mismatch: {name}")
        hashes[name] = actual
    fields = set(pq.read_schema(path).names)
    if not set(TRANSACTION_FIELDS) <= fields or fields - set(TRANSACTION_FIELDS) - TRANSACTION_METADATA:
        raise ValueError("Only the normalized label-free transaction schema is accepted")
    quality = json.loads(quality_path.read_text())
    if not isinstance(quality, dict):
        raise ValueError("Invalid dataset quality metadata")
    if quality["dataset_id"] != completion["dataset_id"]:
        raise ValueError("Conflicting input dataset identities")
    cutoff = utc_instant(cutoff)
    subjects = tuple(sorted(set(
        item if isinstance(item, AccountKey) else AccountKey(**item) for item in subject_accounts
    )))
    expression = ds.field("occurred_at") < pa.scalar(cutoff, type=pa.timestamp("us", tz="UTC"))
    if start is not None:
        expression = expression & (
            ds.field("occurred_at") >= pa.scalar(utc_instant(start),
                                                type=pa.timestamp("us", tz="UTC"))
        )
    if subjects:
        account_filter = None
        for account in subjects:
            item = (
                ((ds.field("sender_bank_id") == account.bank_id) & (ds.field("sender_account_id") == account.account_id))
                | ((ds.field("receiver_bank_id") == account.bank_id) & (ds.field("receiver_account_id") == account.account_id))
            )
            account_filter = item if account_filter is None else account_filter | item
        expression = expression & account_filter
    rows = []
    limit = max_records
    scanner = ds.dataset(path, format="parquet").scanner(
        columns=list(TRANSACTION_FIELDS), filter=expression, batch_size=16384,
    )
    for batch in scanner.to_batches():
        if len(rows) + batch.num_rows > limit:
            raise ValueError("Input transaction budget exceeded; select an account scope or a smaller policy window")
        rows.extend(batch.to_pylist())
    context = {
        "dataset_id": quality["dataset_id"], "observation_intervals": quality["observation_intervals"],
        "known_gaps": quality["known_gaps"], "subject_accounts": subjects,
        "timezone_policy": quality["timestamp_policy"],
        "timezone_policy_basis": quality.get("timestamp_policy_basis", "user_declared"),
        "timestamp_precision": quality["timestamp_precision"],
    }
    return rows, context, hashes


def run_rule_snapshot(transactions_path, policy_path, cutoff, output_root, *, subject_accounts=()):
    """Run one explicit cutoff, never opening labels or pattern annotations."""
    policy = load_policy(policy_path)
    cutoff = utc_instant(cutoff)
    active_width = max(
        (policy[rule].get("active_window_minutes", policy[rule].get("window_minutes", 0))
         for rule in CORE_RULES if policy.get(rule, {}).get("enabled")), default=0,
    )
    # Read verified metadata in the loader, then choose the bounded active prefix
    # unless complete observation intervals require historical records.
    rows, context, hashes = load_detection_snapshot(
        transactions_path, cutoff, start=cutoff - timedelta(minutes=active_width),
        max_records=execution_limits(policy)["max_input_transactions"], subject_accounts=subject_accounts,
    )
    if context["observation_intervals"] and any(
        policy.get(rule, {}).get("enabled") for rule in ("burst", "dormant_activation")
    ):
        rows, context, hashes = load_detection_snapshot(
            transactions_path, cutoff, max_records=execution_limits(policy)["max_input_transactions"],
            subject_accounts=subject_accounts,
        )
    parent = Path(transactions_path).parent
    quality = json.loads((parent / "quality.json").read_text())
    result = evaluate_rules(rows, policy=policy, cutoff=cutoff, context=context)
    # Detect a source change during scanning before publishing any finding artifacts.
    for name, expected in hashes.items():
        if _hash(parent / name) != expected:
            raise ValueError("Detection input changed during analysis")
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / result.run_id
    if target.is_symlink():
        raise ValueError("Rule-run output must not be a symbolic link")
    if target.exists():
        if (target / "run.json").is_symlink():
            raise ValueError("Rule-run metadata must not be a symbolic link")
        previous = json.loads((target / "run.json").read_text())
        evidence = target / "findings.json"
        if (not isinstance(previous, dict) or previous.get("status") != "completed"
                or evidence.is_symlink() or previous.get("run_id") != result.run_id
                or previous.get("input_hashes") != hashes
                or _hash(evidence) != previous.get("findings_sha256")):
            raise ValueError("Existing rule-run integrity mismatch; refusing to overwrite")
        return {**previous, "status": "reused", "output_directory": str(target)}
    with tempfile.TemporaryDirectory(prefix=".rules-", dir=root) as temporary:
        stage = Path(temporary)
        evidence = stage / "findings.json"
        evidence.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")
        summary = {
            "schema_version": "1", "status": "completed", "engine_version": result.engine_version,
            "run_id": result.run_id, "dataset_id": result.dataset_id, "cutoff": result.cutoff.isoformat(),
            "policy_version": result.policy_version, "policy_hash": result.policy_hash,
            "mode": "cutoff_snapshot", "input_records": len(rows),
            "finding_count": len(result.findings),
            "findings_by_rule": dict(sorted(Counter(item.rule_id for item in result.findings).items())),
            "feature_status": {item.feature_id: item.status for item in result.coverage},
            "input_hashes": hashes, "findings_sha256": _hash(evidence),
            "subject_scope": result.to_dict()["scope"]["subjects"],
            "source_observed_bounds": {
                "minimum": quality["occurred_at_min"], "maximum": quality["occurred_at_max"],
            },
            "limitations": [
                "This is one cutoff snapshot, not a full-history scan or a risk score.",
                "Finding counts are not confirmed illicit-account counts or benchmark accuracy.",
                "Unknown source coverage keeps history-dependent rules unavailable.",
            ],
        }
        (stage / "run.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        stage.rename(target)
        return {**summary, "output_directory": str(target)}
