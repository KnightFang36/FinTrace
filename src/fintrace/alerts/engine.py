"""Stable incident grouping and explicit audited lifecycle transitions."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fintrace.contracts import AccountKey, content_id, json_value, utc_instant
from fintrace.scoring.priority import SUBJECT_ROLES, unique_findings, validate_priority_snapshot


def validate_alert_policy(policy):
    if (not isinstance(policy, dict) or set(policy) != {"schema_version", "policy_version", "incident_window_minutes", "minimum_priority"}
            or policy["schema_version"] != "1" or not isinstance(policy["policy_version"], str) or not policy["policy_version"].strip()
            or type(policy["incident_window_minutes"]) is not int or not 1 <= policy["incident_window_minutes"] <= 10080
            or type(policy["minimum_priority"]) is not int or not 0 <= policy["minimum_priority"] <= 100):
        raise ValueError("Invalid alert policy")
    return policy


def _event(alert, actor, at, action, previous, reason, artifact_ids):
    if not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
        raise ValueError("Audit actor and reason are required")
    event = {"entity_type": "alert", "entity_id": alert["alert_id"], "version": alert["version"],
             "actor": actor, "timestamp": utc_instant(at), "action": action, "previous_state": previous,
             "new_state": alert["state"], "reason": reason, "artifact_ids": sorted(artifact_ids)}
    event["event_id"] = content_id(event)
    return json_value(event)


def build_alerts(findings, priorities, existing_alerts, alert_policy, *, actor, at):
    """Group by dataset/subject/family and epoch-aligned incident containing evidence end.

    A finding spanning an incident boundary stays together in the bucket containing
    its last evidence interval instant; it is never split into unsupported fragments.
    """
    policy = validate_alert_policy(alert_policy)
    findings = unique_findings(findings)
    validate_priority_snapshot(priorities)
    at = utc_instant(at)
    priority_accounts = {AccountKey(**item["account"]): item for item in priorities["accounts"]}
    if len(priority_accounts) != len(priorities["accounts"]):
        raise ValueError("Conflicting priority account entries")
    old = {item["deduplication_key"]: deepcopy(item) for item in existing_alerts}
    if len(old) != len(existing_alerts):
        raise ValueError("Duplicate persisted incident keys")
    grouped = {}
    diagnostics = []
    for finding in findings:
        if finding.cutoff > at:
            raise ValueError("Cannot import findings before their cutoff")
        for account, role in zip(finding.subject_accounts, finding.subject_roles):
            if role != SUBJECT_ROLES.get(finding.rule_id):
                raise ValueError("Unsupported finding subject role")
            priority = priority_accounts.get(account)
            if priority is None or priority["dataset_id"] != finding.dataset_id:
                raise ValueError("Every finding subject needs a matching priority snapshot")
            eligible = [item for item in priority["contributions"] if finding.finding_id in item["eligible_finding_ids"]]
            if len(eligible) != 1:
                raise ValueError("Finding is absent or ambiguous in priority contribution ledger")
            if priority["score"] < policy["minimum_priority"]:
                diagnostics.append({"finding_id": finding.finding_id, "account": json_value(account), "reason": "below_priority_threshold"})
                continue
            family = eligible[0]["family_id"]
            if finding.rule_id not in priorities["policy"]["families"][family]["rules"]:
                raise ValueError("Finding rule does not belong to priority family")
            if finding.cutoff != utc_instant(priority["window_end"]) or finding.window_start < utc_instant(priority["window_start"]):
                raise ValueError("Finding is outside priority window")
            seconds = policy["incident_window_minutes"] * 60
            # Microsecond arithmetic avoids placing an exclusive midnight end in the next day.
            last = finding.window_end - timedelta(microseconds=1)
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            bucket = (last - epoch) // timedelta(seconds=seconds)
            key = content_id({"dataset": finding.dataset_id, "subject": account, "family": family,
                              "bucket": bucket, "alert_policy_hash": content_id(policy)})
            entry = grouped.setdefault(key, {"findings": [], "priority": priority, "account": account,
                                             "family": family, "bucket": bucket, "seconds": seconds})
            entry["findings"].append(finding)
    changes, events = [], []
    unchanged = 0
    for key, entry in sorted(grouped.items()):
        previous = old.get(key)
        ids = sorted({finding.finding_id for finding in entry["findings"]})
        transaction_ids = sorted({txid for finding in entry["findings"] for txid in finding.transaction_ids})
        priority = entry["priority"]
        if previous and set(ids) <= set(previous["finding_ids"]) and priority["priority_id"] in previous["priority_snapshot_ids"]:
            unchanged += 1
            continue
        if previous:
            alert = deepcopy(previous)
            if at < utc_instant(alert["updated_at"]):
                raise ValueError("Alert updates cannot move audit time backwards")
            alert["version"] += 1
            alert["finding_ids"] = sorted(set(alert["finding_ids"]) | set(ids))
            alert["transaction_ids"] = sorted(set(alert["transaction_ids"]) | set(transaction_ids))
            alert["priority_snapshot_ids"] = sorted(set(alert["priority_snapshot_ids"]) | {priority["priority_id"]})
            alert["last_observed_at"] = max(alert["last_observed_at"], max(finding.window_end.isoformat() for finding in entry["findings"]))
            alert["first_observed_at"] = min(alert["first_observed_at"], min(finding.window_start.isoformat() for finding in entry["findings"]))
            action = "evidence_updated"
        else:
            alert = {"alert_id": "alert-" + key, "deduplication_key": key, "dataset_id": entry["findings"][0].dataset_id,
                     "subject": json_value(entry["account"]), "family_id": entry["family"],
                     "incident_bucket": entry["bucket"], "incident_window_seconds": entry["seconds"],
                     "alert_policy_version": policy["policy_version"], "alert_policy_hash": content_id(policy),
                     "finding_ids": ids, "transaction_ids": transaction_ids, "priority_snapshot_ids": [priority["priority_id"]],
                     "state": "open", "version": 1, "assigned_to": None, "case_id": None,
                     "first_observed_at": min(finding.window_start.isoformat() for finding in entry["findings"]),
                     "last_observed_at": max(finding.window_end.isoformat() for finding in entry["findings"]),
                     "created_at": at.isoformat()}
            action = "created"
        alert["updated_at"] = at.isoformat()
        alert["explanation"] = (f"{len(alert['finding_ids'])} finding(s) in the {entry['family']} evidence family; "
                                f"{len(alert['transaction_ids'])} referenced transactions. Review priority {priority['score']}/100 "
                                f"({priority['band']}). Review each linked finding's measurements, thresholds and limitations. "
                                "This alert is a suspicion for review, not confirmed illicit activity.")
        changes.append(alert)
        events.append(_event(alert, actor, at, action, previous["state"] if previous else None,
                             "Imported verified evidence and fixed-policy priority", ids + [priority["priority_id"]]))
    return {"alerts": changes, "events": events, "unchanged": unchanged, "diagnostics": diagnostics}


def transition_alert(alert, new_state, *, actor, at, reason, expected_version, reopen=False):
    if expected_version != alert["version"]:
        raise ValueError("Stale alert version")
    allowed = {"open": {"in_review"}, "in_review": {"escalated", "closed"}, "escalated": {"in_review", "closed"}, "closed": set()}
    previous = alert["state"]
    if reopen:
        valid = previous == "closed" and new_state == "open"
    else:
        valid = new_state in allowed.get(previous, set())
    if not valid:
        raise ValueError("Illegal alert lifecycle transition; closed alerts need explicit reopen")
    at = utc_instant(at)
    if at < utc_instant(alert["updated_at"]):
        raise ValueError("Audit timestamps cannot move backwards")
    updated = deepcopy(alert)
    updated.update(state=new_state, version=alert["version"] + 1, updated_at=at.isoformat())
    event = _event(updated, actor, at, "reopened" if reopen else "status_changed", previous, reason, alert["finding_ids"])
    return updated, event
