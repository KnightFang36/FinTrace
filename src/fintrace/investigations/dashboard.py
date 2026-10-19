"""Read-only dashboard models scoped to an immutable priority snapshot."""
import json
from collections import Counter
from pathlib import Path

from fintrace.contracts import AccountKey, content_id, parse_finding
from fintrace.scoring.priority import validate_priority_snapshot


def _connect(path):
    import duckdb
    path = Path(path)
    if not path.is_file():
        raise ValueError("No alert store found. Import completed rule/graph runs with scripts/manage_alerts.py first.")
    if path.is_symlink() or {"raw", "evaluation"} & set(path.resolve().parts):
        raise ValueError("Use the local alert store outside raw/evaluation data")
    return duckdb.connect(str(path), read_only=True)


SNAPSHOT_CATALOG_LIMIT = 200


def list_snapshots(database):
    """Return the newest snapshots, newest first, with the hidden count disclosed.

    Snapshots are ordered by analysis cutoff, not by content-addressed ID. IDs are
    hashes, so ordering by them would hide arbitrary cutoffs while the list still
    looked cutoff-sorted. Instants are UTC-normalized by canonical_json, so their
    text order equals chronological order. Only the selected payloads are loaded,
    so the read stays bounded on a large catalog.
    """
    import duckdb

    limit = SNAPSHOT_CATALOG_LIMIT
    with _connect(database) as connection:
        try:
            total = connection.execute("SELECT count(*) FROM ft_priority_runs").fetchone()[0]
            rows = connection.execute(
                "WITH ordered AS ("
                "  SELECT id, json_extract_string(payload, '$.window.end') AS cutoff"
                "  FROM ft_priority_runs ORDER BY cutoff DESC NULLS LAST, id DESC LIMIT ?"
                ") SELECT o.id, t.payload, o.cutoff FROM ordered o JOIN ft_priority_runs t USING (id)"
                " ORDER BY o.cutoff DESC NULLS LAST, o.id DESC",
                [limit],
            ).fetchall()
        except duckdb.Error as error:
            raise ValueError(
                "Snapshot catalog is unreadable; the alert store holds a malformed priority snapshot: "
                f"{error}"
            ) from error
    items = []
    for identifier, text, cutoff in rows:
        snapshot = json.loads(text)
        validate_priority_snapshot(snapshot)
        if snapshot["window"]["end"] != cutoff:
            raise ValueError(f"Snapshot catalog ordering disagrees with stored payload for {identifier}")
        items.append({"id": identifier, "cutoff": snapshot["window"]["end"],
                      "accounts": len(snapshot["accounts"]), "policy": snapshot["policy"]["policy_version"]})
    items.sort(key=lambda item: (item["cutoff"], item["id"]), reverse=True)
    return {"items": items, "truncated": total > limit, "excluded": max(0, total - limit), "total": total}



def load_dashboard(database, snapshot_id):
    with _connect(database) as connection:
        row = connection.execute("SELECT payload FROM ft_priority_runs WHERE id=?", [snapshot_id]).fetchone()
        if row is None:
            raise ValueError("Priority snapshot not found")
        snapshot = validate_priority_snapshot(json.loads(row[0]))
        priorities = {content_id(item["account"]): item for item in snapshot["accounts"]}
        selected = {identifier for item in snapshot["accounts"] for contribution in item["contributions"]
                    for identifier in contribution["eligible_finding_ids"]}
        if len(selected) > 20000 or len(priorities) > 10000:
            raise ValueError("Dashboard snapshot exceeds the 20,000-finding / 10,000-account view budget")
        findings = {}
        for identifier in sorted(selected):
            evidence = connection.execute("SELECT payload FROM ft_findings WHERE id=?", [identifier]).fetchone()
            if evidence is None:
                raise ValueError("Snapshot references missing finding evidence")
            value = json.loads(evidence[0])
            finding = parse_finding(value)
            if finding.finding_id != identifier or finding.cutoff.isoformat() != snapshot["window"]["end"]:
                raise ValueError("Evidence conflicts with selected snapshot")
            findings[identifier] = value
        rows = connection.execute("SELECT payload FROM ft_alerts ORDER BY id LIMIT 20001").fetchall()
        if len(rows) > 20000:
            raise ValueError("Alert store exceeds dashboard view budget; a paginated repository is required")
        alerts = []
        for row in rows:
            alert = json.loads(row[0])
            priority = priorities.get(content_id(alert["subject"]))
            if priority is None or priority["priority_id"] not in alert["priority_snapshot_ids"]:
                continue
            ids = sorted(selected & set(alert["finding_ids"]))
            if not ids:
                continue
            evidence = [findings[identifier] for identifier in ids]
            # Current workflow metadata is deliberate; evidence and priority stay cutoff-isolated.
            alerts.append({key: alert[key] for key in ("alert_id", "subject", "family_id", "state", "version", "updated_at")} | {
                "finding_ids": ids, "transaction_ids": sorted({tid for item in evidence for tid in item["transaction_ids"]}),
                "score": priority["score"], "band": priority["band"], "priority_id": priority["priority_id"],
                "rules": sorted({item["rule_id"] for item in evidence}),
                "currencies": sorted({item["currency"] for item in evidence if item["currency"]}),
                "window_start": min(item["window_start"] for item in evidence),
                "window_end": max(item["window_end"] for item in evidence),
            })
    alerts.sort(key=lambda item: (-item["score"], item["alert_id"]))
    return {"snapshot": snapshot, "priorities": priorities, "findings": findings, "alerts": alerts,
            "summary": {"accounts": len(priorities), "findings": len(findings), "alerts": len(alerts),
                        "open_alerts": sum(item["state"] in ("open", "in_review") for item in alerts),
                        "by_family": dict(sorted(Counter(item["family_id"] for item in alerts).items())),
                        "by_band": {band: sum(item["band"] == band for item in priorities.values())
                                    for band in ("low", "medium", "high", "critical")}}}


def filter_alerts(model, *, query="", states=(), families=(), bands=(), currencies=()):
    query = query.strip().casefold()
    return [item for item in model["alerts"] if
            (not query or query in (item["subject"]["bank_id"] + ":" + item["subject"]["account_id"] + " " + item["alert_id"]).casefold())
            and (not states or item["state"] in states) and (not families or item["family_id"] in families)
            and (not bands or item["band"] in bands) and (not currencies or set(currencies) & set(item["currencies"]))]


def get_audit(database, alert_id):
    with _connect(database) as connection:
        rows = connection.execute("SELECT payload FROM ft_alert_events WHERE alert_id=? ORDER BY version LIMIT 1001", [alert_id]).fetchall()
    return {"events": [json.loads(row[0]) for row in rows[:1000]], "truncated": len(rows) > 1000,
            "scope": "current workflow history; may postdate the analysis cutoff"}


def load_graph_evidence(processed_root, model):
    from fintrace.alerts.runner import load_analysis_run
    coverage = model["snapshot"]["coverage"].get("temporal_graphs", {})
    identifier = coverage.get("run_id")
    if not identifier:
        return None
    if not isinstance(identifier, str) or not identifier.startswith("graphs-") or len(identifier) != 71 or any(
        char not in "0123456789abcdef" for char in identifier[7:]
    ):
        raise ValueError("Invalid graph run identity")
    path = Path(processed_root) / "graph_runs" / identifier
    artifact = path / "graph.json"
    if artifact.is_symlink() or not artifact.is_file():
        raise ValueError(
            "Graph run artifacts are missing under the processed root. Re-run scripts/run_graphs.py "
            "for this snapshot, or clear FINTRACE_PROCESSED_ROOT if it points at another machine."
        )
    if artifact.stat().st_size > 250 * 1024 * 1024:
        raise ValueError("Graph artifact exceeds dashboard loading budget")
    graph, marker = load_analysis_run(path, "graphs")
    datasets = {item["dataset_id"] for item in model["priorities"].values()}
    if (datasets and datasets != {graph["dataset_id"]}) or graph["cutoff"] != model["snapshot"]["window"]["end"]:
        raise ValueError("Graph does not match selected priority snapshot")
    if graph["run_id"] != identifier:
        raise ValueError("Graph directory identity mismatch")
    return graph
