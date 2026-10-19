"""Live service totals, cutoff isolation, empty states and explicit UI writes."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tomllib

import pytest
from streamlit.testing.v1 import AppTest

from fintrace.contracts import AccountKey, Finding
from fintrace.investigations.dashboard import filter_alerts, list_snapshots, load_dashboard, load_graph_evidence
from fintrace.scoring.priority import load_scoring_policy, score_accounts
from fintrace.storage.alert_store import AlertStore

ROOT = Path(__file__).resolve().parents[2]
START = datetime(2022, 9, 1, tzinfo=timezone.utc)
END = START + timedelta(hours=3)


def finding(identifier="f1", end=END):
    return Finding(identifier, "pass_through", "fixture-v1", "fixture", (AccountKey("01", "A"),), ("forwarder",),
                   START, end, end, ("tx-"+identifier,), {"count": 3}, {"minimum_count": 2}, "USD",
                   "Synthetic evidence fixture for review.", ("Not confirmed crime.",))


def scores(findings, end=END):
    return score_accounts(findings, {"temporal_graphs": {"status": "unavailable", "reason": "graph_snapshot_not_supplied"}},
                          load_scoring_policy(ROOT / "config/scoring.toml"), {"start": START, "end": end})


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    path = tmp_path / "alerts.duckdb"
    values = [finding()]
    snapshot = scores(values)
    policy = tomllib.loads((ROOT / "config/alerts.toml").read_text())
    with AlertStore(path) as store:
        store.import_analysis(values, snapshot, policy, actor="fixture", at=END)
    monkeypatch.setenv("FINTRACE_ALERT_DATABASE", str(path))
    monkeypatch.setenv("FINTRACE_PROCESSED_ROOT", str(tmp_path))
    return path, snapshot, policy


def test_snapshot_read_only_filters_and_future_evidence_isolation(workspace):
    path, snapshot, policy = workspace
    before = path.stat().st_mtime_ns
    model = load_dashboard(path, snapshot["snapshot_id"])
    assert model["summary"] == {"accounts": 1, "findings": 1, "alerts": 1, "open_alerts": 1,
                                "by_family": {"pass_through": 1}, "by_band": {"low": 1, "medium": 0, "high": 0, "critical": 0}}
    assert path.stat().st_mtime_ns == before
    assert filter_alerts(model, query="01:A") == model["alerts"]
    assert filter_alerts(model, currencies=["EUR"]) == []
    later = finding("later", END + timedelta(hours=1))
    with AlertStore(path) as store:
        store.import_analysis([later], scores([later], END+timedelta(hours=1)), policy, actor="fixture", at=END+timedelta(hours=1))
    old = load_dashboard(path, snapshot["snapshot_id"])
    assert old["alerts"][0]["finding_ids"] == ["f1"]
    assert old["alerts"][0]["transaction_ids"] == ["tx-f1"]
    assert old["alerts"][0]["score"] == 25
    assert old["alerts"][0]["version"] == 2
    assert len(list_snapshots(path)["items"]) == 2


def test_ui_overview_navigation_and_filtered_empty_queue(workspace):
    path, snapshot, _ = workspace
    at = AppTest.from_file(ROOT / "app/streamlit_app.py", default_timeout=30).run()
    assert not at.exception
    assert [metric.value for metric in at.metric] == ["1", "1", "1", "1"]
    at.radio(key="navigation").set_value("Alert review").run()
    assert not at.exception
    next(widget for widget in at.multiselect if widget.label == "Workflow status").set_value(["closed"]).run()
    assert any("No alerts match" in item.value for item in at.info)
    at.radio(key="navigation").set_value("Account evidence").run()
    assert not at.exception and any("Unavailable" in item.value for item in at.caption)
    next(button for button in at.button if button.label == "Load graph-window transfers").click().run()
    assert any("No graph snapshot" in item.value for item in at.info)
    at.radio(key="navigation").set_value("Network explorer").run()
    assert not at.exception and any("No temporal graph snapshot" in item.value for item in at.info)


def test_ui_review_requires_explicit_fields_and_rerender_does_not_repeat_write(workspace):
    path, snapshot, _ = workspace
    at = AppTest.from_file(ROOT / "app/streamlit_app.py", default_timeout=30).run()
    at.radio(key="navigation").set_value("Alert review").run()
    next(button for button in at.button if button.label == "Save audited review").click().run()
    assert any("Enter a reviewer" in item.value for item in at.error)
    next(widget for widget in at.text_input if widget.label == "Reviewer").set_value("fixture-analyst")
    next(widget for widget in at.text_area if widget.label == "Review reason").set_value("Begin evidence review")
    next(button for button in at.button if button.label == "Save audited review").click().run()
    assert not at.exception
    assert any("Review saved" in item.value for item in at.success)
    at.run()
    with AlertStore(path) as store:
        alert = store.list_alerts()[0]
        assert alert["state"] == "in_review" and alert["version"] == 2
        assert len(store.events(alert["alert_id"])) == 2


def test_empty_workspace_never_creates_database(tmp_path, monkeypatch):
    missing = tmp_path / "missing.duckdb"
    monkeypatch.setenv("FINTRACE_ALERT_DATABASE", str(missing))
    at = AppTest.from_file(ROOT / "app/streamlit_app.py", default_timeout=30).run()
    assert not at.exception
    assert not at.metric
    assert any("No alert store found" in item.value for item in at.info)
    assert not missing.exists()


def test_missing_graph_artifacts_raise_actionable_value_error(tmp_path, workspace):
    """A pruned or foreign processed root must not surface a raw OSError."""
    path, snapshot, _ = workspace
    model = load_dashboard(path, snapshot["snapshot_id"])
    model["snapshot"]["coverage"]["temporal_graphs"] = {
        "status": "evaluated", "run_id": "graphs-" + "a" * 64,
    }
    with pytest.raises(ValueError, match="Graph run artifacts are missing"):
        load_graph_evidence(tmp_path / "empty-root", model)
