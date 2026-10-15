"""Verify frozen detector outputs, assign priorities and transactionally import alerts."""
import json
import tomllib
from pathlib import Path
from datetime import timedelta

from fintrace.contracts import parse_finding, utc_instant
from fintrace.rules.runner import _hash
from fintrace.scoring.priority import load_scoring_policy, score_accounts
from fintrace.storage.alert_store import AlertStore


def load_analysis_run(directory, kind):
    directory = Path(directory)
    if kind not in ("rules", "graphs") or directory.is_symlink() or "evaluation" in directory.parts:
        raise ValueError("Use a completed detection run outside evaluation data")
    marker_path = directory / "run.json"
    if marker_path.is_symlink():
        raise ValueError("Run metadata cannot be a symbolic link")
    marker = json.loads(marker_path.read_text())
    if not isinstance(marker, dict) or marker.get("status") != "completed":
        raise ValueError("Detection run is incomplete")
    name = "findings.json" if kind == "rules" else "graph.json"
    artifacts = {"findings.json": marker.get("findings_sha256")} if kind == "rules" else marker.get("artifacts", {})
    expected = {"findings.json"} if kind == "rules" else {"graph.json", "network.png"}
    if not isinstance(artifacts, dict) or set(artifacts) != expected:
        raise ValueError("Invalid detection artifact inventory")
    for filename, digest in artifacts.items():
        path = directory / filename
        if path.is_symlink() or _hash(path) != digest:
            raise ValueError("Detection artifact integrity mismatch")
    payload = json.loads((directory / name).read_text())
    if not isinstance(payload, dict) or payload.get("schema_version") != "1":
        raise ValueError("Invalid detection artifact schema")
    for key in ("run_id", "dataset_id", "cutoff", "policy_hash"):
        if payload.get(key) != marker.get(key):
            raise ValueError("Conflicting detection run identities")
    if not payload["run_id"].startswith(kind + "-"):
        raise ValueError("Incorrect detection run type")
    expected_engine = "transaction-rules-v1" if kind == "rules" else "temporal-graphs-v1"
    if payload.get("engine_version") != expected_engine:
        raise ValueError("Unsupported detection engine version")
    if marker.get("finding_count") != len(payload["findings"]):
        raise ValueError("Detection finding count mismatch")
    hashes = marker.get("input_hashes")
    if not isinstance(hashes, dict) or set(hashes) != {"transactions.parquet", "quality.json"}:
        raise ValueError("Detection input identities are required")
    for value in payload["findings"]:
        finding = parse_finding(value)
        if finding.dataset_id != payload["dataset_id"] or finding.cutoff != utc_instant(payload["cutoff"]):
            raise ValueError("Finding dataset/cutoff conflicts with detection run")
        version = expected_engine + ":" + payload["policy_version"] + "@" + payload["policy_hash"][:16]
        if finding.rule_version != version:
            raise ValueError("Finding policy identity conflicts with detection run")
    return payload, marker


def import_analysis(rule_run, graph_run, scoring_policy_path, alert_policy_path, database_path, *, actor, at):
    rules, rule_marker = load_analysis_run(rule_run, "rules")
    cutoff = utc_instant(rules["cutoff"])
    findings = list(rules["findings"])
    coverage = {"transaction_rules": {"run_id": rules["run_id"], "features": rules["coverage"], "scope": rules["scope"]}}
    source_ids = [rules["run_id"]]
    if graph_run is not None:
        graphs, graph_marker = load_analysis_run(graph_run, "graphs")
        if (graphs["dataset_id"] != rules["dataset_id"] or utc_instant(graphs["cutoff"]) != cutoff
                or graph_marker["input_hashes"] != rule_marker["input_hashes"]):
            raise ValueError("Rule and graph runs must share a dataset, exclusive cutoff and input hashes")
        findings.extend(graphs["findings"])
        coverage["temporal_graphs"] = {"run_id": graphs["run_id"], "features": graphs["coverage"],
                                      "context_status": {currency: {name: data["status"] for name, data in value.items()}
                                                         for currency, value in graphs["context"].items()}}
        source_ids.append(graphs["run_id"])
    else:
        coverage["temporal_graphs"] = {"status": "unavailable", "reason": "graph_snapshot_not_supplied"}
    with Path(alert_policy_path).open("rb") as handle:
        alert_policy = tomllib.load(handle)
    start = min((utc_instant(finding["window_start"]) for finding in findings), default=cutoff - timedelta(minutes=1))
    priorities = score_accounts(findings, coverage, load_scoring_policy(scoring_policy_path), {"start": start, "end": cutoff})
    with AlertStore(database_path) as store:
        changes = store.import_analysis(findings, priorities, alert_policy, actor=actor, at=at)
        alert_count = len(store.list_alerts())
    return {"schema_version": "1", "dataset_id": rules["dataset_id"], "cutoff": cutoff.isoformat(),
            "source_run_ids": source_ids, "priority_snapshot_id": priorities["snapshot_id"],
            "scored_accounts": len(priorities["accounts"]), "changed_alerts": len(changes["alerts"]),
            "unchanged_incidents": changes["unchanged"], "audit_events_appended": len(changes["events"]),
            "total_persisted_alerts": alert_count, "diagnostics": changes["diagnostics"],
            "database_path": str(Path(database_path).resolve()), "coverage": coverage,
            "priority_bands": {band: sum(item["band"] == band for item in priorities["accounts"])
                               for band in ("low", "medium", "high", "critical")}}
