"""Fixed family arithmetic, explicit roles and incident lifecycle invariants."""
import copy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import tomllib

import pytest

from fintrace.alerts.engine import build_alerts, transition_alert
from fintrace.contracts import AccountKey, Finding, content_id
from fintrace.scoring.priority import SUBJECT_ROLES, load_scoring_policy, score_accounts, validate_priority_snapshot

ROOT = Path(__file__).resolve().parents[2]
START = datetime(2022, 9, 1, tzinfo=timezone.utc)
END = datetime(2022, 9, 1, 3, tzinfo=timezone.utc)
ACCOUNT = AccountKey("01", "A")


def finding(rule="pass_through", identifier="f1", account=ACCOUNT):
    return Finding(identifier, rule, "fixture-v1", "fixture", (account,), (SUBJECT_ROLES.get(rule, "unsupported"),),
                   START, END, END, ("tx-" + identifier,), {"observed_count": 5}, {"minimum_count": 3},
                   "USD", "Measured fixture pattern for review.", ("Synthetic test evidence.",))


def score(findings, **overrides):
    policy = load_scoring_policy(ROOT / "config/scoring.toml") | overrides
    return score_accounts(findings, {"burst": {"status": "unavailable"}}, policy, {"start": START, "end": END})


def alert_policy(**overrides):
    with (ROOT / "config/alerts.toml").open("rb") as handle:
        return tomllib.load(handle) | overrides


def changes(findings, existing=(), priorities=None, **kwargs):
    return build_alerts(findings, priorities or score(findings), list(existing), alert_policy(),
                        actor="fixture-runner", at=END, **kwargs)


def test_expected_70_high_and_correlated_family_suppression():
    findings = [finding(), finding("fan_in", "f2"), finding("layering", "f3"), finding("fan_out", "f4")]
    result = score(findings)
    account = result["accounts"][0]
    assert (account["score"], account["band"]) == (70, "high")
    collection = next(item for item in account["contributions"] if item["family_id"] == "collection_dispersal")
    assert collection["selected_finding_ids"] == ["f2"]
    assert collection["suppressed_finding_ids"] == ["f4"]
    assert score(list(reversed(findings))) == result
    validate_priority_snapshot(result)


def test_cap_and_distinct_bank_identity():
    policy = load_scoring_policy(ROOT / "config/scoring.toml")
    policy["families"]["pass_through"]["weight"] = 100
    result = score([finding(), finding("fan_in", "f2"), finding("fan_out", "f3", AccountKey("1", "A"))], families=policy["families"])
    assert len(result["accounts"]) == 2
    first = result["accounts"][0]
    assert first["score"] == 100 and first["uncapped_total"] == 115


def test_coverage_is_preserved_and_no_neighbours_get_scores():
    result = score([finding()])
    assert len(result["accounts"]) == 1
    assert result["accounts"][0]["account"] == {"bank_id": "01", "account_id": "A"}
    assert result["accounts"][0]["coverage_summary"]["burst"]["status"] == "unavailable"
    assert score([])["accounts"] == []


@pytest.mark.parametrize("override", [{"maximum_score": 101}, {"medium_minimum": -1}, {"high_minimum": 30}, {"low_minimum": False}])
def test_invalid_policy_rejected(override):
    with pytest.raises(ValueError):
        score([finding()], **override)


def test_invalid_findings_policy_roles_ids_and_windows_rejected():
    values = [finding("unknown"), replace(finding(), subject_roles=("context_only",)),
              replace(finding(), window_start=END), replace(finding(), transaction_ids=()),
              replace(finding(), cutoff=END.replace(hour=4))]
    for value in values:
        with pytest.raises(ValueError):
            score([value])
    with pytest.raises(ValueError, match="Conflicting"):
        score([finding(), replace(finding(), explanation="different")])
    with pytest.raises(ValueError, match="mix datasets"):
        score([finding(), replace(finding("fan_in", "f2"), dataset_id="other")])
    policy = load_scoring_policy(ROOT / "config/scoring.toml")
    policy["families"]["pass_through"]["rules"].append("fan_in")
    with pytest.raises(ValueError):
        score([finding()], families=policy["families"])


def test_changed_priority_snapshot_cannot_create_alert():
    priorities = score([finding()])
    priorities["accounts"][0]["score"] = 100
    with pytest.raises(ValueError, match="integrity"):
        changes([finding()], priorities=priorities)


def test_same_incident_dedup_new_evidence_and_policy_identity():
    initial = changes([finding()])
    old = initial["alerts"]
    repeated = changes([finding()], old)
    assert repeated["alerts"] == [] and repeated["events"] == [] and repeated["unchanged"] == 1
    update = changes([finding(), finding(identifier="f2")], old)
    assert update["alerts"][0]["alert_id"] == old[0]["alert_id"]
    assert update["alerts"][0]["transaction_ids"] == ["tx-f1", "tx-f2"]
    assert len(update["alerts"][0]["priority_snapshot_ids"]) == 2
    assert update["events"][0]["action"] == "evidence_updated"
    changed_policy = build_alerts([finding()], score([finding()]), old, alert_policy(policy_version="new"), actor="test", at=END)
    assert changed_policy["alerts"][0]["alert_id"] != old[0]["alert_id"]


def test_exclusive_midnight_belongs_to_preceding_incident():
    midnight = END.replace(day=2, hour=0)
    value = replace(finding(), window_end=midnight, cutoff=midnight)
    priorities = score_accounts([value], {}, load_scoring_policy(ROOT / "config/scoring.toml"), {"start": START, "end": midnight})
    alert = build_alerts([value], priorities, [], alert_policy(), actor="test", at=midnight)["alerts"][0]
    assert alert["incident_bucket"] == int(START.timestamp()) // 86400


def test_lifecycle_stale_illegal_close_and_explicit_reopen():
    alert = changes([finding()])["alerts"][0]
    with pytest.raises(ValueError, match="Illegal"):
        transition_alert(alert, "closed", actor="analyst", at=END, reason="review", expected_version=1)
    with pytest.raises(ValueError, match="Stale"):
        transition_alert(alert, "in_review", actor="analyst", at=END, reason="review", expected_version=0)
    review, event = transition_alert(alert, "in_review", actor="analyst", at=END, reason="Review started", expected_version=1)
    with pytest.raises(ValueError, match="reason"):
        transition_alert(review, "closed", actor="analyst", at=END, reason="", expected_version=2)
    closed, _ = transition_alert(review, "closed", actor="analyst", at=END, reason="Legitimate activity", expected_version=2)
    with pytest.raises(ValueError, match="reopen"):
        transition_alert(closed, "open", actor="analyst", at=END, reason="New information", expected_version=3)
    reopened, event = transition_alert(closed, "open", actor="analyst", at=END, reason="New information", expected_version=3, reopen=True)
    assert reopened["state"] == "open" and event["action"] == "reopened"
    assert alert["state"] == "open" and alert["version"] == 1


def test_new_evidence_does_not_implicitly_reopen_closed_alert():
    alert = changes([finding()])["alerts"][0]
    review, _ = transition_alert(alert, "in_review", actor="analyst", at=END, reason="Review", expected_version=1)
    closed, _ = transition_alert(review, "closed", actor="analyst", at=END, reason="Reviewed", expected_version=2)
    updated = changes([finding(), finding(identifier="f2")], [closed])["alerts"][0]
    assert updated["state"] == "closed" and updated["version"] == 4


def test_import_before_cutoff_and_missing_priority_rejected():
    with pytest.raises(ValueError, match="before their cutoff"):
        build_alerts([finding()], score([finding()]), [], alert_policy(), actor="test", at=START)
    with pytest.raises(ValueError, match="matching priority"):
        changes([finding()], priorities=score([]))


def test_actor_is_required_even_for_empty_import():
    with pytest.raises(ValueError, match="actor"):
        build_alerts([], score([]), [], alert_policy(), actor="", at=END)


def test_priority_arithmetic_is_validated_even_with_recomputed_hashes():
    snapshot = score([finding()])
    account = snapshot["accounts"][0]
    account["score"] = 100
    account["priority_id"] = content_id({key: value for key, value in account.items() if key != "priority_id"})
    snapshot["snapshot_id"] = "priorities-" + content_id({key: value for key, value in snapshot.items() if key != "snapshot_id"})
    with pytest.raises(ValueError, match="arithmetic"):
        validate_priority_snapshot(snapshot)
