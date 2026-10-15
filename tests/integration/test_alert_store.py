"""Transactional evidence retention, idempotent import and audited workflow."""
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import tomllib

import pytest

from fintrace.alerts.runner import import_analysis
from fintrace.contracts import AccountKey, Finding, canonical_json
from fintrace.graph import analyze_graph
from fintrace.graph.policy import load_graph_policy
from fintrace.rules.engine import evaluate_rules
from fintrace.rules.policy import load_policy
from fintrace.rules.runner import _hash
from fintrace.scoring.priority import load_scoring_policy, score_accounts
from fintrace.storage.alert_store import AlertStore

ROOT = Path(__file__).resolve().parents[2]
START = datetime(2022, 9, 1, tzinfo=timezone.utc)
END = datetime(2022, 9, 1, 3, tzinfo=timezone.utc)


def finding(identifier="f1"):
    return Finding(identifier, "pass_through", "fixture-v1", "fixture", (AccountKey("01", "A"),), ("forwarder",),
                   START, END, END, ("tx-" + identifier,), {"observed_count": 5}, {"minimum_count": 3},
                   "USD", "Synthetic fixture evidence for review.", ("Not a guilt determination.",))


def scores(findings):
    return score_accounts(findings, {}, load_scoring_policy(ROOT / "config/scoring.toml"), {"start": START, "end": END})


def policy():
    return tomllib.loads((ROOT / "config/alerts.toml").read_text())


def test_persistence_repeated_import_and_complete_immutable_evidence(tmp_path):
    path = tmp_path / "alerts.duckdb"
    with AlertStore(path) as store:
        changes = store.import_analysis([finding()], scores([finding()]), policy(), actor="test-runner", at=END)
        alert = changes["alerts"][0]
        assert len(store.events(alert["alert_id"])) == 1
        repeated = store.import_analysis([finding()], scores([finding()]), policy(), actor="test-runner", at=END)
        assert repeated["unchanged"] == 1 and not repeated["events"]
        updated = store.import_analysis([finding(), finding("f2")], scores([finding(), finding("f2")]), policy(), actor="test-runner", at=END)
        assert updated["alerts"][0]["version"] == 2
        assert len(updated["alerts"][0]["priority_snapshot_ids"]) == 2
        assert store.evidence("f1")["transaction_ids"] == ["tx-f1"]
        for identifier in updated["alerts"][0]["priority_snapshot_ids"]:
            assert store.priority(identifier)["score"] == 25
    with AlertStore(path) as store:
        assert len(store.list_alerts()) == 1
        assert len(store.events(alert["alert_id"])) == 2


def test_conflicting_evidence_and_interrupted_import_roll_back(tmp_path, monkeypatch):
    with AlertStore(tmp_path / "alerts.duckdb") as store:
        store.import_analysis([finding()], scores([finding()]), policy(), actor="test", at=END)
        changed = replace(finding(), explanation="Conflicting evidence with reused ID")
        with pytest.raises(ValueError, match="Immutable"):
            store.import_analysis([changed], scores([changed]), policy(), actor="test", at=END)
        assert len(store.events(store.list_alerts()[0]["alert_id"])) == 1
        original_save = store._save
        def interrupted(alert, event):
            original_save(alert, event)
            raise RuntimeError("simulated interrupted transaction")
        monkeypatch.setattr(store, "_save", interrupted)
        with pytest.raises(RuntimeError):
            store.import_analysis([finding("f2")], scores([finding("f2")]), policy(), actor="test", at=END)
        assert store.list_alerts()[0]["version"] == 1
        assert len(store.events(store.list_alerts()[0]["alert_id"])) == 1
        with pytest.raises(ValueError, match="Unknown"):
            store.evidence("f2")


def test_versioned_lifecycle_persists_audit_and_rejects_stale_writers(tmp_path):
    with AlertStore(tmp_path / "alerts.duckdb") as store:
        changes = store.import_analysis([finding()], scores([finding()]), policy(), actor="test", at=END)
        alert = changes["alerts"][0]
        reviewed = store.transition(alert["alert_id"], "in_review", actor="reviewer", at=END, reason="Review started", expected_version=1)
        with pytest.raises(ValueError, match="Stale"):
            store.transition(alert["alert_id"], "closed", actor="reviewer", at=END, reason="Stale request", expected_version=1)
        closed = store.transition(alert["alert_id"], "closed", actor="reviewer", at=END, reason="Legitimate pattern", expected_version=2)
        assert closed["state"] == "closed"
        store.transition(alert["alert_id"], "open", actor="reviewer", at=END, reason="Further information", expected_version=3, reopen=True)
        events = store.events(alert["alert_id"])
        assert [event["version"] for event in events] == [1, 2, 3, 4]
        assert events[-1]["action"] == "reopened"
        assert events[2]["reason"] == "Legitimate pattern"


@pytest.fixture
def analysis_runs(tmp_path):
    rows = [{"transaction_id": str(i), "dataset_id": "fixture", "occurred_at": f"2022-09-01T00:0{i+1}:00Z",
             "sender_bank_id": "1", "sender_account_id": sender, "receiver_bank_id": "1", "receiver_account_id": receiver,
             "amount_paid": "10.00", "payment_currency": "USD", "amount_received": "10.00", "receiving_currency": "USD"}
            for i, (sender, receiver) in enumerate((("A", "B"), ("B", "C"), ("C", "A")))]
    rules = evaluate_rules(rows, policy=load_policy(ROOT / "config/rules.toml"), cutoff=END, context={"dataset_id": "fixture"}).to_dict()
    graphs = analyze_graph(rows, [], load_graph_policy(ROOT / "config/graph.toml"), END).to_dict()
    paths = []
    for kind, payload, filename in (("rules", rules, "findings.json"), ("graphs", graphs, "graph.json")):
        directory = tmp_path / kind
        directory.mkdir()
        (directory / filename).write_text(canonical_json(payload))
        marker = {key: payload[key] for key in ("run_id", "dataset_id", "cutoff", "policy_hash")}
        marker.update(status="completed", finding_count=len(payload["findings"]),
                      input_hashes={"transactions.parquet": "fixture-transfer-hash", "quality.json": "fixture-quality-hash"})
        if kind == "rules":
            marker["findings_sha256"] = _hash(directory / filename)
        else:
            (directory / "network.png").write_bytes(b"fixture-graph-not-read-by-alert-analysis")
            marker["artifacts"] = {name: _hash(directory / name) for name in (filename, "network.png")}
        (directory / "run.json").write_text(canonical_json(marker))
        paths.append(directory)
    return paths


def test_combined_verified_runs_create_priorities_and_reuse(analysis_runs, tmp_path):
    rules, graphs = analysis_runs
    database = tmp_path / "alerts.duckdb"
    first = import_analysis(rules, graphs, ROOT / "config/scoring.toml", ROOT / "config/alerts.toml", database, actor="test", at=END)
    assert first["scored_accounts"] == 3 and first["changed_alerts"] == 3
    second = import_analysis(rules, graphs, ROOT / "config/scoring.toml", ROOT / "config/alerts.toml", database, actor="test", at=END)
    assert second["changed_alerts"] == 0 and second["unchanged_incidents"] == 3
    with AlertStore(database) as store:
        for alert in store.list_alerts():
            assert alert["family_id"] == "temporal_network"
            assert len(store.events(alert["alert_id"])) == 1


def test_corrupt_run_or_mismatched_cutoffs_fail_before_store_creation(analysis_runs, tmp_path):
    rules, graphs = analysis_runs
    graph_marker = graphs / "run.json"
    data = json.loads(graph_marker.read_text())
    data["input_hashes"]["quality.json"] = "changed"
    graph_marker.write_text(canonical_json(data))
    with pytest.raises(ValueError, match="share a dataset"):
        import_analysis(rules, graphs, ROOT / "config/scoring.toml", ROOT / "config/alerts.toml", tmp_path / "alerts.duckdb", actor="test", at=END)
    assert not (tmp_path / "alerts.duckdb").exists()
    (rules / "findings.json").write_text("corrupt")
    with pytest.raises(ValueError, match="integrity"):
        import_analysis(rules, None, ROOT / "config/scoring.toml", ROOT / "config/alerts.toml", tmp_path / "alerts.duckdb", actor="test", at=END)


def test_cli_import_list_and_audited_transition(analysis_runs, tmp_path):
    rules, graphs = analysis_runs
    base = [sys.executable, str(ROOT / "scripts/manage_alerts.py"), "--database", str(tmp_path / "alerts.duckdb")]
    imported = subprocess.run(base + ["import", "--rules-run", str(rules), "--graph-run", str(graphs),
                                      "--actor", "fixture-runner", "--at", END.isoformat()], capture_output=True, text=True)
    assert imported.returncode == 0, imported.stderr
    listed = subprocess.run(base + ["list"], capture_output=True, text=True)
    assert listed.returncode == 0, listed.stderr
    alert = json.loads(listed.stdout)["alerts"][0]
    transitioned = subprocess.run(base + ["transition", alert["alert_id"], "in_review", "--expected-version", "1",
                                          "--actor", "fixture-reviewer", "--at", END.isoformat(), "--reason", "Review started"], capture_output=True, text=True)
    assert transitioned.returncode == 0, transitioned.stderr
    assert json.loads(transitioned.stdout)["state"] == "in_review"


def test_finding_identity_must_match_frozen_run_even_if_checksum_updated(analysis_runs, tmp_path):
    rules, graphs = analysis_runs
    graph_path = graphs / "graph.json"
    payload = json.loads(graph_path.read_text())
    payload["findings"][0]["dataset_id"] = "other"
    graph_path.write_text(canonical_json(payload))
    marker_path = graphs / "run.json"
    marker = json.loads(marker_path.read_text())
    marker["artifacts"]["graph.json"] = _hash(graph_path)
    marker_path.write_text(canonical_json(marker))
    with pytest.raises(ValueError, match="conflicts"):
        import_analysis(rules, graphs, ROOT / "config/scoring.toml", ROOT / "config/alerts.toml", tmp_path / "alerts.duckdb", actor="test", at=END)
    assert not (tmp_path / "alerts.duckdb").exists()


def test_cli_reports_corrupt_database_without_traceback(tmp_path):
    database = tmp_path / "broken.duckdb"
    database.write_bytes(b"corrupt database")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/manage_alerts.py"), "--database", str(database), "list"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "Alert operation failed" in result.stderr
    assert "Traceback" not in result.stderr
