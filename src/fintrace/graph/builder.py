"""Parallel transaction edges and exact, currency-specific summaries."""
from datetime import timedelta
from decimal import Decimal, localcontext

import networkx as nx

from fintrace.contracts import Transaction, utc_instant
from fintrace.graph.policy import validate_graph_policy


def build_transaction_graph(transactions, graph_policy, cutoff, *, dataset_id=None):
    validate_graph_policy(graph_policy)
    cutoff = utc_instant(cutoff)
    start = cutoff - timedelta(minutes=graph_policy["window_minutes"])
    unique = {}
    for row in transactions:
        # Revalidate even Transaction instances; direct dataclass construction is public.
        if isinstance(row, Transaction):
            row = dict(zip(("transaction_id", "dataset_id", "occurred_at", "sender_bank_id",
                            "sender_account_id", "receiver_bank_id", "receiver_account_id",
                            "amount_paid", "payment_currency", "amount_received", "receiving_currency"),
                           (row.transaction_id, row.dataset_id, row.occurred_at, row.sender.bank_id,
                            row.sender.account_id, row.receiver.bank_id, row.receiver.account_id,
                            row.amount_paid, row.payment_currency, row.amount_received, row.receiving_currency)))
        item = Transaction.from_mapping(row)
        if not start <= item.occurred_at < cutoff:
            continue
        if item.transaction_id in unique and unique[item.transaction_id] != item:
            raise ValueError("Conflicting graph transaction IDs")
        unique[item.transaction_id] = item
        if len(unique) > graph_policy["max_input_transactions"]:
            raise ValueError("Graph input transaction budget exceeded; no sampling is performed")
    datasets = {item.dataset_id for item in unique.values()}
    if len(datasets) > 1 or (datasets and dataset_id and datasets != {dataset_id}):
        raise ValueError("Graph input must have one dataset identity")
    dataset_id = next(iter(datasets), dataset_id)
    if not isinstance(dataset_id, str) or not dataset_id:
        raise ValueError("dataset_id is required for an empty graph")
    graph = nx.MultiDiGraph(dataset_id=dataset_id, start=start, cutoff=cutoff, excluded_self_transfers=0)
    for item in sorted(unique.values(), key=lambda item: (item.occurred_at, item.transaction_id)):
        if item.is_self_transfer:
            graph.graph["excluded_self_transfers"] += 1
            continue
        graph.add_edge(item.sender, item.receiver, key=item.transaction_id, transaction=item)
        if graph.number_of_nodes() > graph_policy["max_nodes"]:
            raise ValueError("Graph node budget exceeded; no sampling is performed")
    return graph


def build_account_summary(graph, currency):
    """Only same-currency edges; retain both side totals without assuming equality."""
    summary = nx.DiGraph(currency=currency)
    with localcontext() as context:
        context.prec = 60
        for sender, receiver, key, data in graph.edges(keys=True, data=True):
            item = data["transaction"]
            if item.payment_currency != currency or item.receiving_currency != currency:
                continue
            if not summary.has_edge(sender, receiver):
                summary.add_edge(sender, receiver, count=0, amount_paid=Decimal(0),
                                 amount_received=Decimal(0), transaction_ids=[])
            edge = summary[sender][receiver]
            edge["count"] += 1
            edge["amount_paid"] += item.amount_paid
            edge["amount_received"] += item.amount_received
            edge["transaction_ids"].append(key)
    for _, _, data in summary.edges(data=True):
        data["transaction_ids"].sort()
    return summary
