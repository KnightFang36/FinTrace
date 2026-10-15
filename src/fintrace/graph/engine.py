"""Evidence-backed temporal NetworkX snapshot analysis."""
from dataclasses import dataclass

import networkx as nx

from fintrace.contracts import AccountKey, Finding, content_id, json_value
from fintrace.graph.builder import build_account_summary, build_transaction_graph
from fintrace.graph.communities import find_communities
from fintrace.graph.coordinated_groups import find_coordinated_groups
from fintrace.graph.cycles import find_temporal_cycles
from fintrace.graph.metrics import compute_metrics
from fintrace.graph.temporal_paths import find_temporal_paths

ENGINE_VERSION = "temporal-graphs-v1"


@dataclass(frozen=True)
class GraphAnalysisResult:
    graph: nx.MultiDiGraph
    artifact: dict
    findings: tuple[Finding, ...]

    def to_dict(self):
        return json_value(self.artifact | {"findings": self.findings})


def analyze_graph(transactions, seed_accounts, graph_policy, cutoff, *, dataset_id=None):
    """Seeds restrict chain/cycle origins, never the input graph or group/metric scope."""
    graph = build_transaction_graph(transactions, graph_policy, cutoff, dataset_id=dataset_id)
    policy = graph_policy
    supplied = tuple(sorted({seed if isinstance(seed, AccountKey) else AccountKey(**seed) for seed in seed_accounts}))
    if len(supplied) > policy["max_seed_accounts"]:
        raise ValueError("Graph seed budget exceeded")
    missing = [seed for seed in supplied if seed not in graph]
    seeds = [seed for seed in supplied if seed in graph] if supplied else sorted(graph, key=lambda node: (-graph.out_degree(node), node))
    seed_partial = not supplied and len(seeds) > policy["max_seed_accounts"]
    seeds = seeds[:policy["max_seed_accounts"]]
    identity = {"engine": ENGINE_VERSION, "networkx_version": nx.__version__, "policy": policy,
                "dataset_id": graph.graph["dataset_id"], "cutoff": graph.graph["cutoff"],
                "input": sorted((data["transaction"] for *_, data in graph.edges(data=True)),
                                key=lambda item: item.transaction_id),
                "excluded_self_transfers": graph.graph["excluded_self_transfers"], "seeds": supplied,
                "selected_origins": seeds, "origin_ranking": "outgoing_edge_count_descending_then_bank_account"}
    run_id = "graphs-" + content_id(identity)
    paths, path_coverage = find_temporal_paths(graph, seeds, policy)
    cycles, cycle_coverage = find_temporal_cycles(graph, seeds, policy)
    groups, group_coverage = find_coordinated_groups(graph, policy)
    for coverage in (path_coverage, cycle_coverage):
        coverage["seed_scope"] = "explicit_origins" if supplied else "outgoing_edge_count_descending_then_bank_account"
        coverage["seeds_searched"] = seeds
        coverage["missing_seeds"] = missing
        if seed_partial:
            coverage["status"] = "truncated"
            coverage["reason_codes"].append("seed_budget_exhausted")
    findings = []

    def finding(rule, rows, subjects, roles, measurements, currency):
        fields = {"run_id": run_id, "rule": rule, "ids": [row.transaction_id for row in rows],
                  "subjects": subjects, "measurements": measurements}
        explanation = {
            "layering": f"Observed a strictly chronological {len(rows)}-transfer chain in {currency}.",
            "circular_flow": f"Observed a strictly chronological {len(rows)}-transfer return to the starting account in {currency}.",
            "coordinated_group": "Observed the same participant set sharing a directed counterparty in repeated synchronized buckets.",
        }[rule]
        findings.append(Finding(
            content_id(fields), rule, ENGINE_VERSION + ":" + policy["policy_version"] + "@" + content_id(policy)[:16],
            graph.graph["dataset_id"], tuple(subjects), tuple(roles), graph.graph["start"], graph.graph["cutoff"],
            graph.graph["cutoff"], tuple(row.transaction_id for row in rows), measurements, dict(policy), currency,
            explanation,
            ("Pattern evidence warrants review; it does not establish criminal intent or confirmed mule status.",
             "Ordered edges do not prove exact source-of-funds attribution through commingled balances.",
             "Timestamp ties are excluded; elapsed times reflect source precision.",
             "Cross-currency edges remain in the graph but are excluded from pattern searches."),
            evidence_graph_ref=run_id,
        ))

    for path in paths:
        # Intermediaries are review subjects; endpoints are contextual, not automatically flagged.
        subjects = tuple(row.receiver for row in path[:-1])
        finding("layering", path, subjects, ["intermediary"] * len(subjects),
                {"hop_count": len(path), "ordered_transaction_ids": [row.transaction_id for row in path],
                 "ordered_times": [row.occurred_at for row in path],
                 "accounts": [path[0].sender] + [row.receiver for row in path]}, path[0].payment_currency)
    for cycle in cycles:
        subjects = tuple(row.sender for row in cycle)
        finding("circular_flow", cycle, subjects, ["cycle_participant"] * len(subjects),
                {"hop_count": len(cycle), "returning_account": cycle[0].sender,
                 "initial_amount_paid": cycle[0].amount_paid, "return_amount_received": cycle[-1].amount_received,
                 "value_comparison_basis": "same_currency_observed_endpoints_no_provenance_claim",
                 "ordered_transaction_ids": [row.transaction_id for row in cycle],
                 "ordered_times": [row.occurred_at for row in cycle]}, cycle[0].payment_currency)
    for group in groups:
        finding("coordinated_group", group["transactions"], group["participants"],
                ["synchronized_participant"] * len(group["participants"]),
                {key: value for key, value in group.items() if key != "transactions"}, group["currency"])
    currencies = sorted({data["transaction"].payment_currency for *_, data in graph.edges(data=True)
                         if data["transaction"].payment_currency == data["transaction"].receiving_currency})
    context = {}
    for currency in currencies:
        summary = build_account_summary(graph, currency)
        context[currency] = {"communities": find_communities(summary, policy), "metrics": compute_metrics(summary, policy)}
    artifact = {"schema_version": "1", "engine_version": ENGINE_VERSION, "networkx_version": nx.__version__,
                "run_id": run_id, "dataset_id": graph.graph["dataset_id"], "cutoff": graph.graph["cutoff"],
                "window_start": graph.graph["start"], "policy_version": policy["policy_version"],
                "policy_hash": content_id(policy), "policy": policy,
                "node_count": len(graph), "edge_count": graph.number_of_edges(),
                "excluded_self_transfers": graph.graph["excluded_self_transfers"],
                "edges": [data["transaction"] for *_, data in graph.edges(data=True)],
                "coverage": {"layering": path_coverage, "circular_flow": cycle_coverage,
                             "coordinated_group": group_coverage,
                             "known_exposure": {"status": "disabled", "reason_codes": ["independent_dated_reference_required"]}},
                "context": context,
                "limitations": ["Observation completeness is unknown unless declared by the source snapshot.",
                                "Coordination uses identical participant sets and complete epoch-aligned windows.",
                                "Search limits describe work completed; absence of findings is not a clean-account decision."]}
    return GraphAnalysisResult(graph, artifact, tuple(sorted(findings, key=lambda item: (item.rule_id, item.finding_id))))
