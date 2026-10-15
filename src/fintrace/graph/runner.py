"""Verified graph snapshots, JSON evidence and a bounded PNG projection."""
import json
import tempfile
from collections import Counter
from datetime import timedelta
from pathlib import Path

from fintrace.contracts import utc_instant
from fintrace.graph.engine import analyze_graph
from fintrace.graph.policy import load_graph_policy
from fintrace.graph.visualization import render_graph_png
from fintrace.rules.runner import _hash, load_detection_snapshot


def run_graph_snapshot(transactions_path, policy_path, cutoff, output_root, *, seed_accounts=()):
    policy = load_graph_policy(policy_path)
    cutoff = utc_instant(cutoff)
    rows, context, hashes = load_detection_snapshot(
        transactions_path, cutoff, start=cutoff - timedelta(minutes=policy["window_minutes"]),
        max_records=policy["max_input_transactions"],
    )
    result = analyze_graph(rows, seed_accounts, policy, cutoff, dataset_id=context["dataset_id"])
    parent = Path(transactions_path).parent
    if any(_hash(parent / name) != digest for name, digest in hashes.items()):
        raise ValueError("Graph detection input changed during analysis")
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / result.artifact["run_id"]
    if target.is_symlink():
        raise ValueError("Graph-run output cannot be a symbolic link")
    if target.exists():
        marker = target / "run.json"
        if marker.is_symlink():
            raise ValueError("Graph-run metadata cannot be a symbolic link")
        previous = json.loads(marker.read_text())
        if (previous.get("status") != "completed" or previous.get("run_id") != result.artifact["run_id"]
                or previous.get("input_hashes") != hashes
                or set(previous.get("artifacts", {})) != {"graph.json", "network.png"}):
            raise ValueError("Existing graph-run integrity mismatch")
        for name, digest in previous["artifacts"].items():
            artifact = target / name
            if artifact.is_symlink() or _hash(artifact) != digest:
                raise ValueError("Existing graph-run artifact integrity mismatch")
        return previous | {"status": "reused", "output_directory": str(target)}
    with tempfile.TemporaryDirectory(prefix=".graphs-", dir=root) as temporary:
        stage = Path(temporary)
        visualization = render_graph_png(result.graph, stage / "network.png", policy)
        payload = result.to_dict() | {"source_context": context, "visualization": visualization}
        (stage / "graph.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        summary = {
            "schema_version": "1", "status": "completed", "run_id": result.artifact["run_id"],
            "dataset_id": context["dataset_id"], "cutoff": cutoff.isoformat(),
            "policy_version": policy["policy_version"], "policy_hash": result.artifact["policy_hash"],
            "input_records": len(rows), "nodes": len(result.graph), "edges": result.graph.number_of_edges(),
            "finding_count": len(result.findings),
            "findings_by_rule": dict(sorted(Counter(item.rule_id for item in result.findings).items())),
            "coverage": payload["coverage"], "visualization": visualization, "input_hashes": hashes,
            "artifacts": {name: _hash(stage / name) for name in ("graph.json", "network.png")},
        }
        (stage / "run.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        stage.rename(target)
    return summary | {"output_directory": str(target)}
