"""Deterministic snapshot evaluation with explicit eligibility and bounded evidence."""

from __future__ import annotations

from fintrace.contracts import (
    AccountKey, FeatureCoverage, RuleResult, Transaction, content_id, utc_instant,
)
from fintrace.rules.burst import detect_burst
from fintrace.rules.common import RULE_VERSION, active_start, source_intervals
from fintrace.rules.dormant_activation import detect_dormant_activation
from fintrace.rules.fan_in import detect_fan_in
from fintrace.rules.fan_out import detect_fan_out
from fintrace.rules.pass_through import detect_pass_through
from fintrace.rules.policy import ALL_RULES, CORE_RULES, execution_limits, validate_policy
from fintrace.rules.repeated_splitting import detect_repeated_splitting

ENGINE_VERSION = RULE_VERSION
DETECTORS = {
    "pass_through": detect_pass_through, "fan_in": detect_fan_in, "fan_out": detect_fan_out,
    "repeated_splitting": detect_repeated_splitting, "burst": detect_burst,
    "dormant_activation": detect_dormant_activation,
}


def evaluate_rules(transactions, history=None, *, policy, cutoff, context=None) -> RuleResult:
    """Evaluate one cutoff snapshot; all source events at cutoff or later are excluded.

    Active and history inputs must be normalized label-free mappings. If provided,
    history must include complete relevant records for the declared scope; the
    caller must not sample while declaring complete observation coverage.
    """
    validate_policy(policy)
    cutoff = utc_instant(cutoff)
    context = dict(context or {})
    if set(context) - {"dataset_id", "subject_accounts", "observation_intervals", "known_gaps",
                       "timezone_policy", "timezone_policy_basis"}:
        raise ValueError("Unknown context fields; benchmark or arbitrary enrichment inputs are not accepted")
    source_intervals(context)
    subjects = context.get("subject_accounts", ())
    context["subject_accounts"] = tuple(sorted({
        value if isinstance(value, AccountKey) else AccountKey(**value) for value in subjects
    }))
    limits = execution_limits(policy)
    unique = {}
    for source in (transactions, history if history is not None else ()):
        for row in source:
            transaction = Transaction.from_mapping(row)
            if transaction.occurred_at >= cutoff:
                continue
            previous = unique.get(transaction.transaction_id)
            if previous is not None and previous != transaction:
                raise ValueError("Conflicting records share a transaction ID")
            unique[transaction.transaction_id] = transaction
            if len(unique) > limits["max_input_transactions"]:
                raise ValueError("Input transaction budget exceeded; narrow the requested account scope")
    rows = sorted(unique.values(), key=lambda row: (row.occurred_at, row.transaction_id))
    datasets = {row.dataset_id for row in rows}
    declared_dataset = context.get("dataset_id")
    if len(datasets) > 1 or (datasets and declared_dataset and datasets != {declared_dataset}):
        raise ValueError("A rule snapshot must belong to exactly one declared dataset")
    dataset_id = next(iter(datasets), declared_dataset)
    if not isinstance(dataset_id, str) or not dataset_id:
        raise ValueError("dataset_id is required even for an empty snapshot")
    self_count = sum(row.is_self_transfer for row in rows)
    eligible = [row for row in rows if not row.is_self_transfer]
    policy_hash = content_id(policy)
    identity = {
        "engine": ENGINE_VERSION, "dataset_id": dataset_id, "policy_hash": policy_hash,
        "cutoff": cutoff, "scope": context, "input": content_id(rows),
    }
    run_id = "rules-" + content_id(identity)
    findings, coverage = [], []
    for rule in ALL_RULES:
        settings = policy.get(rule, {"enabled": False})
        window = ({"start": active_start(settings, cutoff), "end": cutoff} if rule in CORE_RULES
                  and settings.get("enabled") else {"end": cutoff})
        source_coverage = {
            "observation_intervals": context.get("observation_intervals", []),
            "known_gaps": context.get("known_gaps", []),
            "completeness": "declared" if context.get("observation_intervals") else "unknown",
        }
        if not settings.get("enabled"):
            status, reasons, work = "disabled", ("policy_disabled",), {}
        elif rule not in CORE_RULES:
            status, reasons, work = "unavailable", (
                "graph_phase_pending" if rule in ("layering", "circular_flow", "coordinated_group")
                else "verified_context_service_pending",
            ), {}
        elif rule in ("burst", "dormant_activation") and not context.get("observation_intervals"):
            status, reasons, work = "unavailable", ("unknown_observation_coverage",), {}
        else:
            result = DETECTORS[rule](eligible, settings, policy, cutoff, context)
            findings.extend(result.findings)
            reasons = tuple(sorted(result.skipped))
            if result.truncated_groups:
                status = "truncated"
                reasons += ("evidence_or_finding_budget_exceeded",)
            elif result.skipped and result.evaluated_groups == 0:
                status = "unavailable"
            else:
                status = "evaluated"
            work = {
                "evaluated_groups": result.evaluated_groups,
                "unavailable_groups_by_reason": dict(sorted(result.skipped.items())),
                "truncated_groups": result.truncated_groups, "findings": len(result.findings),
            }
        coverage.append(FeatureCoverage(rule, status, reasons, window, source_coverage, work, limits))
    return RuleResult(
        "1", ENGINE_VERSION, run_id, dataset_id, cutoff, policy["policy_version"], policy_hash,
        tuple(sorted(findings, key=lambda finding: (finding.rule_id, finding.finding_id))),
        tuple(coverage),
        {"mode": "cutoff_snapshot", "subjects": context["subject_accounts"] or "all_observed",
         "eligible_input_records": len(rows), "excluded_self_transfers": self_count,
         "source_timezone_policy": context.get("timezone_policy"),
         "source_timezone_basis": context.get("timezone_policy_basis"),
         "limitations": ["Unknown observation coverage is not a clean-account determination.",
                         "The snapshot covers each rule's configured interval ending at cutoff."]},
    )
