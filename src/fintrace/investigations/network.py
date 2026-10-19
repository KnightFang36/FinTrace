"""Bounded directed NetworkX views and exact evidence-path highlighting."""
from collections import deque
import networkx as nx
from fintrace.contracts import AccountKey, content_id


def get_network_view(graph, seed, *, hops=1, direction="both", max_nodes=60, max_edges=150, finding=None):
    return _network_view(graph, [seed], hops=hops, direction=direction, max_nodes=max_nodes,
                         max_edges=max_edges, finding=finding)


def get_alerted_network_view(graph, model, *, hops=1, direction="both", max_nodes=40, max_edges=150):
    """Top ten active-alert subjects by fixed-policy priority, with stable ties."""
    alerts = {}
    for alert in model['alerts']:
        if alert['state'] in ('open', 'in_review', 'escalated'):
            identifier = content_id(alert['subject'])
            alerts[identifier] = alerts.get(identifier, 0) + 1
    ranked = sorted((item for item in model['priorities'].values() if content_id(item['account']) in alerts),
                    key=lambda item: (-item['score'], item['account']['bank_id'], item['account']['account_id']))[:10]
    seeds = [item['account'] for item in ranked]
    if len(seeds) > max_nodes:
        raise ValueError('Display budget must retain every selected priority account')
    view = _network_view(graph, seeds, hops=hops, direction=direction, max_nodes=max_nodes,
                         max_edges=max_edges, include_missing=True)
    metadata = {content_id(item['account']): {'rank': rank, 'score': item['score'],
                                            'active_alerts': alerts[content_id(item['account'])]}
                for rank, item in enumerate(ranked, 1)}
    for node in view['nodes']:
        node.update(metadata.get(node['id'], {}))
    view['ranked_accounts'] = [{'account': item['account'], **metadata[content_id(item['account'])]}
                               for item in ranked]
    view['selection'] = 'up to ten active-alert accounts, descending fixed-policy priority; ties use exact bank/account strings'
    return view


def _network_view(graph, seeds, *, hops=1, direction="both", max_nodes=60, max_edges=150,
                  finding=None, include_missing=False):
    if direction not in ("both", "incoming", "outgoing") or type(hops) is not int or not 1 <= hops <= 3:
        raise ValueError("Invalid network expansion")
    if type(max_nodes) is not int or not 1 <= max_nodes <= 200 or type(max_edges) is not int or not 1 <= max_edges <= 500:
        raise ValueError("Invalid network display budget")
    seeds = [seed if isinstance(seed, dict) else {'bank_id': seed.bank_id, 'account_id': seed.account_id}
             for seed in seeds]
    for seed in seeds:
        AccountKey(**seed)
    network = nx.MultiDiGraph()
    rows = {}
    for row in graph["edges"]:
        sender, receiver = content_id(row["sender"]), content_id(row["receiver"])
        network.add_node(sender, account=row["sender"])
        network.add_node(receiver, account=row["receiver"])
        network.add_edge(sender, receiver, key=row["transaction_id"])
        rows[row["transaction_id"]] = row
    source_nodes = len(network)
    origins = [content_id(seed) for seed in seeds]
    missing = [seed for seed in seeds if content_id(seed) not in network]
    if include_missing:
        for seed in missing:
            network.add_node(content_id(seed), account=seed)
    highlight = set((finding or {}).get("transaction_ids", []))
    selected, chosen_edges = set(), []
    # Reserve every ranked account before expanding neighbours; no invented links.
    if include_missing:
        selected.update(origins)
    for identifier in (finding or {}).get("transaction_ids", []):
        row = rows.get(identifier)
        if row is None:
            continue
        ends = {content_id(row["sender"]), content_id(row["receiver"])}
        if len(selected | ends) <= max_nodes and len(chosen_edges) < max_edges:
            selected.update(ends)
            chosen_edges.append(identifier)
    frontier = []
    for origin in origins:
        if origin in network and len(selected | {origin}) <= max_nodes:
            selected.add(origin)
            frontier.append(origin)
    visited = set(frontier)
    # Breadth-first layers expand one neighbour per frontier account per round,
    # keeping a high-degree account from exhausting the combined display alone.
    for _ in range(hops):
        iterators = deque()
        for node in frontier:
            neighbors = set()
            if direction in ("both", "outgoing"):
                neighbors.update(network.successors(node))
            if direction in ("both", "incoming"):
                neighbors.update(network.predecessors(node))
            iterators.append(iter(sorted(neighbors)))
        frontier = []
        while iterators and len(selected) < max_nodes:
            iterator = iterators.popleft()
            for neighbor in iterator:
                if neighbor not in visited:
                    selected.add(neighbor)
                    visited.add(neighbor)
                    frontier.append(neighbor)
                    iterators.append(iterator)
                    break
        if not frontier or len(selected) >= max_nodes:
            break
    # Round-robin incident transfers gives each ranked subject display coverage.
    # Parallel source transactions retain distinct IDs.
    eligible = sorted((left, right, identifier) for left, right, identifier in network.edges(keys=True)
                      if left in selected and right in selected)
    groups = [[] for _ in origins] + [[]]
    origin_rank = {origin: rank for rank, origin in enumerate(origins)}
    for left, right, identifier in eligible:
        rank = min(origin_rank.get(left, len(origins)), origin_rank.get(right, len(origins)))
        groups[rank].append(identifier)
    iterators = deque(iter(group) for group in groups if group)
    chosen = set(chosen_edges)
    while iterators and len(chosen_edges) < max_edges:
        iterator = iterators.popleft()
        for identifier in iterator:
            if identifier not in chosen:
                chosen_edges.append(identifier)
                chosen.add(identifier)
                iterators.append(iterator)
                break
    missing_ids = {content_id(seed) for seed in missing}
    return {"nodes": [{"id": identifier, "account": network.nodes[identifier]["account"],
                       "seed": identifier in origins, 'missing_from_window': identifier in missing_ids}
                      for identifier in sorted(selected)],
            "edges": [{"id": identifier, "from": content_id(rows[identifier]["sender"]),
                       "to": content_id(rows[identifier]["receiver"]), "highlighted": identifier in highlight,
                       "transaction": rows[identifier]} for identifier in chosen_edges],
            "source_nodes": source_nodes, "source_edges": len(rows), "missing_seed": bool(missing),
            'missing_seeds': missing,
            "partial": len(selected - missing_ids) < source_nodes or len(chosen_edges) < len(rows),
            "evidence_complete": highlight <= chosen, "hops": hops, "direction": direction,
            "limits": {"max_nodes": max_nodes, "max_edges": max_edges},
            "scope": "bounded structural neighbourhood; reachability alone is not a chronological transfer path"}
