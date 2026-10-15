"""Strict versioned policy loading; invalid thresholds fail before analysis."""

from __future__ import annotations

import tomllib
from decimal import Decimal, InvalidOperation
from pathlib import Path

CORE_RULES = ("pass_through", "fan_in", "fan_out", "repeated_splitting", "burst", "dormant_activation")
OPTIONAL_RULES = ("cash_out", "profile_mismatch", "known_exposure")
GRAPH_RULES = ("layering", "circular_flow", "coordinated_group")
ALL_RULES = CORE_RULES + OPTIONAL_RULES + GRAPH_RULES
DEFAULT_EXECUTION = {
    "max_input_transactions": 250000,
    "max_findings_per_rule": 10000,
    "max_evidence_transactions": 10000,
    "max_allocation_entries": 20000,
    "exclude_self_transfers": True,
}


def validate_policy(policy: dict) -> dict:
    if not isinstance(policy, dict) or policy.get("schema_version") != "1":
        raise ValueError("Expected rule policy schema_version='1'")
    if not isinstance(policy.get("policy_version"), str) or not policy["policy_version"].strip():
        raise ValueError("policy_version must be non-empty")
    if set(policy) - {"schema_version", "policy_version", "execution", *ALL_RULES}:
        raise ValueError("Unknown policy section")
    execution = policy.get("execution", {})
    if set(execution) - set(DEFAULT_EXECUTION):
        raise ValueError("Unknown execution limit")
    for key, default in DEFAULT_EXECUTION.items():
        value = execution.get(key, default)
        if type(default) is bool:
            if type(value) is not bool:
                raise ValueError(f"{key} must be boolean")
        elif type(value) is not int or not 1 <= value <= 1000000:
            raise ValueError(f"{key} must be a positive bounded integer")
    if execution.get("exclude_self_transfers", True) is not True:
        raise ValueError("This rule version excludes self-transfers from movement indicators")
    allowed = {
        "pass_through": {"window_minutes", "minimum_incoming_count", "minimum_forwarded_ratio",
                         "allocation_method", "require_strict_time_order"},
        "fan_in": {"window_minutes", "minimum_distinct_senders"},
        "fan_out": {"window_minutes", "minimum_distinct_recipients"},
        "repeated_splitting": {"window_minutes", "minimum_related_payments"},
        "burst": {"window_minutes", "minimum_count", "history_days",
                  "minimum_complete_history_days", "baseline_multiplier"},
        "dormant_activation": {"window_minutes", "observed_inactivity_days",
                              "active_window_minutes", "minimum_count", "require_complete_observation_interval"},
    }
    for rule in ALL_RULES:
        if rule not in policy:
            continue
        settings = policy[rule]
        if not isinstance(settings, dict) or type(settings.get("enabled")) is not bool:
            raise ValueError(f"{rule}.enabled must be explicit boolean")
        if rule not in CORE_RULES or not settings["enabled"]:
            continue
        if set(settings) - {"enabled", *allowed[rule]}:
            raise ValueError(f"Unknown parameter for {rule}")
        required = allowed[rule] - ({"window_minutes"} if rule == "dormant_activation" else set())
        if not required <= set(settings):
            raise ValueError(f"Missing parameter for {rule}")
        for key, value in settings.items():
            if key.endswith(("_count", "_days", "_minutes", "_senders", "_recipients", "_payments")):
                if type(value) is not int or not 1 <= value <= 1000000:
                    raise ValueError(f"Invalid positive integer {rule}.{key}")
        if rule == "pass_through":
            if settings["allocation_method"] != "fifo_observed_inflows" or settings["require_strict_time_order"] is not True:
                raise ValueError("Only strictly chronological observed-inflow FIFO allocation is supported")
            try:
                ratio = Decimal(settings["minimum_forwarded_ratio"])
            except (InvalidOperation, TypeError) as error:
                raise ValueError("Invalid pass-through ratio") from error
            if not isinstance(settings["minimum_forwarded_ratio"], str) or not ratio.is_finite() or not 0 < ratio <= 1:
                raise ValueError("Pass-through ratio must be decimal text in (0,1]")
        if rule == "burst":
            multiplier = settings["baseline_multiplier"]
            if not isinstance(multiplier, str):
                raise ValueError("Baseline multiplier must be decimal text")
            try:
                multiplier = Decimal(multiplier)
            except InvalidOperation as error:
                raise ValueError("Invalid baseline multiplier") from error
            if not multiplier.is_finite() or multiplier <= 0:
                raise ValueError("Baseline multiplier must be positive")
            if settings["minimum_complete_history_days"] > settings["history_days"]:
                raise ValueError("Required history cannot exceed requested history")
        if rule == "dormant_activation" and settings["require_complete_observation_interval"] is not True:
            raise ValueError("Dormancy requires complete observation coverage")
        if rule in ("fan_in", "fan_out", "repeated_splitting", "pass_through"):
            key = {"fan_in": "minimum_distinct_senders", "fan_out": "minimum_distinct_recipients",
                   "repeated_splitting": "minimum_related_payments", "pass_through": "minimum_incoming_count"}[rule]
            if settings[key] < 2:
                raise ValueError(f"{rule} needs at least two contributing payments/counterparties")
    return policy


def execution_limits(policy: dict) -> dict:
    return DEFAULT_EXECUTION | policy.get("execution", {})


def load_policy(path: Path) -> dict:
    with Path(path).open("rb") as handle:
        return validate_policy(tomllib.load(handle))
