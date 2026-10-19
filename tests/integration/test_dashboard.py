"""Live service totals, cutoff isolation, empty states and explicit UI writes."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tomllib

import pytest
from streamlit.testing.v1 import AppTest

from fintrace.contracts import AccountKey, Finding
from fintrace.investigations.dashboard import list_snapshots, load_dashboard, filter_alerts
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


def test_snapshot_catalog_keeps_newest_cutoffs_and_discloses_hidden_count(tmp_path):
    """IDs are content hashes, so ordering by them would drop arbitrary cutoffs."""
    path = tmp_path / "catalog.duckdb"
    policy = tomllib.loads((ROOT / "config/alerts.toml").read_text())
    scoring = load_scoring_policy(ROOT / "config/scoring.toml")
    count = 205
    # The fixture finding spans [START, end), so the first usable cutoff is START + 1h.
    with AlertStore(path) as store:
        for index in range(1, count + 1):
            end = START + timedelta(hours=index)
            value = finding(f"f{index}", end)
            store.import_analysis([value], score_accounts([value], {"temporal_graphs": {"status": "unavailable"}},
                                                          scoring, {"start": START, "end": end}),
                                  policy, actor="fixture", at=end)
    catalog = list_snapshots(path)
    cutoffs = [item["cutoff"] for item in catalog["items"]]
    # The hidden snapshots must be the oldest ones, never arbitrary middle cutoffs.
    assert cutoffs == [(START + timedelta(hours=hour)).isoformat()
                       for hour in range(count, count - 200, -1)]
    assert catalog["truncated"] is True
    assert len(catalog["items"]) == 200
    assert catalog["total"] == count
    assert catalog["excluded"] == count - 200


def test_snapshot_catalog_rejects_malformed_payload_with_actionable_error(tmp_path):
    path = tmp_path / "malformed.duckdb"
    with AlertStore(path) as store:
        store.connection.execute("INSERT INTO ft_priority_runs VALUES (?,?)", ["priorities-broken", "not json"])
    with pytest.raises(ValueError, match="malformed priority snapshot"):
        list_snapshots(path)


def test_ui_warns_how_many_snapshots_are_hidden(tmp_path, monkeypatch):
    path = tmp_path / "large-catalog.duckdb"
    policy = tomllib.loads((ROOT / "config/alerts.toml").read_text())
    scoring = load_scoring_policy(ROOT / "config/scoring.toml")
    with AlertStore(path) as store:
        for index in range(1, 203):
            end = START + timedelta(hours=index)
            value = finding(f"f{index}", end)
            store.import_analysis([value], score_accounts([value], {"temporal_graphs": {"status": "unavailable"}},
                                                          scoring, {"start": START, "end": end}),
                                  policy, actor="fixture", at=end)
    monkeypatch.setenv("FINTRACE_ALERT_DATABASE", str(path))
    monkeypatch.setenv("FINTRACE_PROCESSED_ROOT", str(tmp_path))
    at = AppTest.from_file(ROOT / "app/streamlit_app.py", default_timeout=30).run()
    assert not at.exception
    assert any("2 older snapshots are hidden" in item.value for item in at.warning)
