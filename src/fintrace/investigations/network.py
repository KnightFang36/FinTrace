"""Bounded directed NetworkX neighbourhoods and exact evidence-path highlighting."""
from collections import deque
import networkx as nx
from fintrace.contracts import AccountKey, content_id


def get_network_view(graph, seed, *, hops=1, direction="both", max_nodes=60, max_edges=150, finding=None):
    if direction not in ("both", "incoming", "outgoing") or type(hops) is not int or not 1 <= hops <= 3:
        raise ValueError("Invalid network expansion")
    if type(max_nodes) is not int or not 1 <= max_nodes <= 200 or type(max_edges) is not int or not 1 <= max_edges <= 500:
        raise ValueError("Invalid network display budget")
    seed = seed if isinstance(seed, dict) else {"bank_id": seed.bank_id, "account_id": seed.account_id}
    AccountKey(**seed)
    network = nx.MultiDiGraph()
    rows = {}
    for row in graph["edges"]:
        sender, receiver = content_id(row["sender"]), content_id(row["receiver"])
        network.add_node(sender, account=row["sender"])
        network.add_node(receiver, account=row["receiver"])
        network.add_edge(sender, receiver, key=row["transaction_id"])
        rows[row["transaction_id"]] = row
    origin = content_id(seed)
    highlight = set((finding or {}).get("transaction_ids", []))
    selected, chosen_edges = set(), []
    # Highlighted evidence has display precedence, preserving parallel transfer IDs.
    for identifier in (finding or {}).get("transaction_ids", []):
        row = rows.get(identifier)
        if row is None:
            continue
        ends = {content_id(row["sender"]), content_id(row["receiver"])}
        if len(selected | ends) <= max_nodes and len(chosen_edges) < max_edges:
            selected.update(ends)
            chosen_edges.append(identifier)
    if origin in network:
        if len(selected | {origin}) <= max_nodes:
            selected.add(origin)
        queue = deque([(origin, 0)])
        visited = {origin}
        while queue and len(selected) < max_nodes:
            node, depth = queue.popleft()
            if depth >= hops:
                continue
            neighbors = set()
            if direction in ("both", "outgoing"):
                neighbors.update(network.successors(node))
            if direction in ("both", "incoming"):
                neighbors.update(network.predecessors(node))
            for neighbor in sorted(neighbors):
                if neighbor not in visited:
                    if len(selected) >= max_nodes:
                        break
                    selected.add(neighbor)
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
    for left, right, identifier in sorted(network.edges(keys=True)):
        if left in selected and right in selected and identifier not in chosen_edges and len(chosen_edges) < max_edges:
            chosen_edges.append(identifier)
    evidence_complete = highlight <= set(chosen_edges)
    return {"nodes": [{"id": identifier, "account": network.nodes[identifier]["account"], "seed": identifier == origin}
                       for identifier in sorted(selected)],
            "edges": [{"id": identifier, "from": content_id(rows[identifier]["sender"]),
                       "to": content_id(rows[identifier]["receiver"]), "highlighted": identifier in highlight,
                       "transaction": rows[identifier]} for identifier in chosen_edges],
            "source_nodes": len(network), "source_edges": len(rows), "missing_seed": origin not in network,
            "partial": len(selected) < len(network) or len(chosen_edges) < len(rows),
            "evidence_complete": evidence_complete, "hops": hops, "direction": direction,
            "limits": {"max_nodes": max_nodes, "max_edges": max_edges},
            "scope": "bounded structural neighbourhood; reachability alone is not a chronological transfer path"}
