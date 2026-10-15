"""Versioned fixed-weight account priorities with correlated-evidence suppression."""
import tomllib
from collections import defaultdict
from pathlib import Path

from fintrace.contracts import content_id, json_value, parse_finding, utc_instant

SUBJECT_ROLES = {
    "pass_through": "forwarder", "fan_in": "collector", "fan_out": "distributor",
    "repeated_splitting": "payer", "burst": "high_frequency_account",
    "dormant_activation": "reactivated_account", "layering": "intermediary",
    "circular_flow": "cycle_participant", "coordinated_group": "synchronized_participant",
}


def validate_scoring_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {
        "schema_version", "policy_version", "maximum_score", "low_minimum", "medium_minimum",
        "high_minimum", "critical_minimum", "families",
    }:
        raise ValueError("Invalid scoring policy fields")
    if policy["schema_version"] != "1" or not isinstance(policy["policy_version"], str) or not policy["policy_version"].strip():
        raise ValueError("Invalid scoring policy identity")
    bands = [policy[name + "_minimum"] for name in ("low", "medium", "high", "critical")]
    if (type(policy["maximum_score"]) is not int or policy["maximum_score"] != 100
            or any(type(value) is not int for value in bands)
            or bands[0] != 0 or not all(a < b for a, b in zip(bands, bands[1:])) or bands[-1] > 100):
        raise ValueError("Scoring bands must increase from zero within the 0-100 cap")
    rules = set()
    if not isinstance(policy["families"], dict) or not policy["families"]:
        raise ValueError("At least one scoring family is required")
    for family, settings in policy["families"].items():
        if (not isinstance(family, str) or not family or not isinstance(settings, dict)
                or set(settings) != {"weight", "rules"} or type(settings["weight"]) is not int
                or not 0 <= settings["weight"] <= 100 or not isinstance(settings["rules"], list)
                or not settings["rules"]):
            raise ValueError("Invalid scoring family/weight")
        for rule in settings["rules"]:
            if rule not in SUBJECT_ROLES or rule in rules:
                raise ValueError("Scoring rules must be supported and belong to exactly one family")
            rules.add(rule)
    return policy


def load_scoring_policy(path):
    with Path(path).open("rb") as handle:
        return validate_scoring_policy(tomllib.load(handle))


def unique_findings(findings):
    unique = {}
    for value in findings:
        finding = parse_finding(value)
        previous = unique.get(finding.finding_id)
        if previous is not None and previous != finding:
            raise ValueError("Conflicting findings share an ID")
        unique[finding.finding_id] = finding
    return sorted(unique.values(), key=lambda finding: finding.finding_id)


def score_accounts(findings, coverage, scoring_policy, window):
    """Score only explicit finding subjects; window must fully contain each finding."""
    policy = validate_scoring_policy(scoring_policy)
    if not isinstance(window, dict) or set(window) != {"start", "end"}:
        raise ValueError("A scoring window with start/end is required")
    start, end = utc_instant(window["start"]), utc_instant(window["end"])
    if start >= end:
        raise ValueError("Invalid scoring window")
    findings = unique_findings(findings)
    datasets = {finding.dataset_id for finding in findings}
    if len(datasets) > 1:
        raise ValueError("Priority snapshots cannot mix datasets")
    family_by_rule = {rule: family for family, settings in policy["families"].items() for rule in settings["rules"]}
    grouped = defaultdict(lambda: defaultdict(list))
    for finding in findings:
        if finding.cutoff != end or finding.window_start < start or finding.window_end > end:
            raise ValueError("Finding cutoff/window is incompatible with scoring window")
        if finding.rule_id not in family_by_rule:
            raise ValueError("Finding rule has no explicit scoring family")
        for account, role in zip(finding.subject_accounts, finding.subject_roles):
            if role != SUBJECT_ROLES[finding.rule_id]:
                raise ValueError("Finding subject role is not eligible for this rule")
            grouped[account][family_by_rule[finding.rule_id]].append(finding.finding_id)
    accounts = []
    for account, families in sorted(grouped.items()):
        contributions = []
        for family, ids in sorted(families.items()):
            ids = sorted(set(ids))
            contributions.append({"family_id": family, "eligible_finding_ids": ids,
                                  "selected_finding_ids": ids[:1], "suppressed_finding_ids": ids[1:],
                                  "applied_weight": policy["families"][family]["weight"]})
        raw = sum(item["applied_weight"] for item in contributions)
        score = min(100, raw)
        band = next(name for name in ("critical", "high", "medium", "low") if score >= policy[name + "_minimum"])
        record = {"account": account, "dataset_id": next(iter(datasets)), "window_start": start, "window_end": end,
                  "score": score, "uncapped_total": raw, "band": band, "contributions": contributions,
                  "scoring_policy_version": policy["policy_version"], "scoring_policy_hash": content_id(policy),
                  "coverage_summary": json_value(coverage),
                  "limitations": ["Fixed-policy investigation priority, not a probability or a finding of guilt.",
                                  "Missing and partial coverage does not establish that an account is clean."]}
        record["priority_id"] = content_id(record)
        accounts.append(record)
    result = {"schema_version": "1", "engine_version": "fixed-priority-v1", "policy": policy,
              "policy_hash": content_id(policy), "window": {"start": start, "end": end},
              "accounts": accounts, "coverage": json_value(coverage)}
    result["snapshot_id"] = "priorities-" + content_id(result)
    return json_value(result)


def validate_priority_snapshot(snapshot):
    """Reject altered ledgers at the alert-import boundary."""
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != "1":
        raise ValueError("Invalid priority snapshot")
    policy = validate_scoring_policy(snapshot["policy"])
    if snapshot["policy_hash"] != content_id(policy):
        raise ValueError("Priority policy integrity mismatch")
    if snapshot["snapshot_id"] != "priorities-" + content_id({key: value for key, value in snapshot.items() if key != "snapshot_id"}):
        raise ValueError("Priority snapshot integrity mismatch")
    accounts = set()
    for item in snapshot["accounts"]:
        from fintrace.contracts import AccountKey
        account = AccountKey(**item["account"])
        if account in accounts:
            raise ValueError("Duplicate account priorities")
        accounts.add(account)
        if item["priority_id"] != content_id({key: value for key, value in item.items() if key != "priority_id"}):
            raise ValueError("Priority ledger integrity mismatch")
        if item["scoring_policy_hash"] != snapshot["policy_hash"] or item["scoring_policy_version"] != policy["policy_version"]:
            raise ValueError("Inconsistent priority policy identity")
        families = set()
        total = 0
        for contribution in item["contributions"]:
            family = contribution["family_id"]
            eligible = contribution["eligible_finding_ids"]
            if (family in families or family not in policy["families"] or not eligible
                    or eligible != sorted(set(eligible)) or contribution["selected_finding_ids"] != eligible[:1]
                    or contribution["suppressed_finding_ids"] != eligible[1:]
                    or contribution["applied_weight"] != policy["families"][family]["weight"]):
                raise ValueError("Invalid family contribution ledger")
            families.add(family)
            total += contribution["applied_weight"]
        score = min(100, total)
        band = next(name for name in ("critical", "high", "medium", "low") if score >= policy[name + "_minimum"])
        if item["uncapped_total"] != total or item["score"] != score or item["band"] != band:
            raise ValueError("Priority arithmetic mismatch")
    return snapshot
