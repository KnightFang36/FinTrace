"""Descriptive connected communities, with an explicit unweighted projection."""
import networkx as nx


def find_communities(summary, policy):
    if summary.number_of_nodes() > policy["context_max_nodes"] or summary.number_of_edges() > policy["context_max_edges"]:
        return {"status": "unavailable", "reason": "context_size_budget_exceeded", "memberships": []}
    # Sorted insertion and seed stabilize label propagation across repeated runs.
    projection = nx.Graph()
    projection.add_nodes_from(sorted(summary))
    projection.add_edges_from(sorted({tuple(sorted((a, b))) for a, b in summary.edges()}))
    groups = nx.community.asyn_lpa_communities(projection, weight=None, seed=policy["layout_seed"])
    memberships = sorted((sorted(group) for group in groups), key=lambda group: tuple(group))
    return {"status": "evaluated", "method": "asyn_lpa_communities", "seed": policy["layout_seed"],
            "projection": "unweighted_undirected_distinct_account_pairs", "memberships": memberships,
            "limitations": ["Community membership alone is not suspicious activity."]}
