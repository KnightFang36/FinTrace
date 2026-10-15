"""Descriptive directed connectivity and bounded sampled betweenness."""
from decimal import Decimal, localcontext
import networkx as nx


def compute_metrics(summary, policy):
    if summary.number_of_nodes() > policy["context_max_nodes"] or summary.number_of_edges() > policy["context_max_edges"]:
        return {"status": "unavailable", "reason": "context_size_budget_exceeded", "accounts": []}
    samples = min(len(summary), policy["betweenness_samples"])
    centrality = nx.betweenness_centrality(summary, k=samples, seed=policy["layout_seed"], weight=None) if samples else {}
    accounts = []
    with localcontext() as context:
        context.prec = 60
        for node in sorted(summary):
            incoming = [data for *_, data in summary.in_edges(node, data=True)]
            outgoing = [data for *_, data in summary.out_edges(node, data=True)]
            accounts.append({"account": node, "distinct_senders": summary.in_degree(node),
                             "distinct_receivers": summary.out_degree(node),
                             "amount_received": sum((data["amount_received"] for data in incoming), Decimal(0)),
                             "amount_paid": sum((data["amount_paid"] for data in outgoing), Decimal(0)),
                             "betweenness": centrality[node]})
    return {"status": "evaluated", "accounts": accounts, "currency": summary.graph["currency"],
            "betweenness": {"directed": True, "weight": None, "normalized": True,
                            "samples": samples, "approximate": samples < len(summary), "seed": policy["layout_seed"]},
            "limitations": ["Connectivity and centrality do not independently create findings."]}
