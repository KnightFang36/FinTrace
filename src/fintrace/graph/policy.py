"""Strict bounded graph policy, separate from transaction-rule thresholds."""
import tomllib
from pathlib import Path

FIELDS = {
    "window_minutes": (1, 10080), "minimum_hops": (2, 8), "maximum_hops": (2, 8),
    "minimum_cycle_length": (2, 8), "maximum_cycle_length": (2, 8),
    "max_input_transactions": (1, 1000000), "max_nodes": (1, 1000000),
    "max_seed_accounts": (1, 100), "max_expansions": (1, 1000000),
    "max_findings_per_feature": (1, 10000), "max_search_seconds": (1, 60),
    "context_max_nodes": (1, 2000), "context_max_edges": (1, 10000),
    "betweenness_samples": (1, 100), "layout_seed": (0, 1000000),
    "max_display_nodes": (1, 200), "max_display_edges": (1, 500),
    "coordination_window_minutes": (1, 1440), "coordination_bucket_minutes": (1, 60),
    "coordination_minimum_accounts": (3, 100), "coordination_repeated_windows": (2, 24),
}


def validate_graph_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {"schema_version", "policy_version", *FIELDS}:
        raise ValueError("Graph policy fields must match the versioned schema")
    if policy["schema_version"] != "1" or not isinstance(policy["policy_version"], str) or not policy["policy_version"].strip():
        raise ValueError("Invalid graph policy identity")
    for name, (low, high) in FIELDS.items():
        value = policy[name]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"Invalid bounded graph policy value: {name}")
    if policy["minimum_hops"] > policy["maximum_hops"] or policy["minimum_cycle_length"] > policy["maximum_cycle_length"]:
        raise ValueError("Minimum path/cycle length exceeds maximum")
    if policy["coordination_window_minutes"] % policy["coordination_bucket_minutes"]:
        raise ValueError("Coordination buckets must divide the window")
    return policy


def load_graph_policy(path):
    with Path(path).open("rb") as handle:
        return validate_graph_policy(tomllib.load(handle))
