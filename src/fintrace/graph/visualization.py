"""Headless bounded graph rendering with stable account labels and visible limits."""
from pathlib import Path

import networkx as nx


def render_graph_png(graph, path, policy):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nodes = sorted(graph)[:policy["max_display_nodes"]]
    node_set = set(nodes)
    edges = sorted(((a, b, key) for a, b, key in graph.edges(keys=True) if a in node_set and b in node_set),
                   key=lambda edge: (edge[0], edge[1], edge[2]))[:policy["max_display_edges"]]
    display = nx.MultiDiGraph()
    display.add_nodes_from(nodes)
    display.add_edges_from(edges)
    partial = len(nodes) < len(graph) or len(edges) < graph.number_of_edges()
    fig, axis = plt.subplots(figsize=(14, 10))
    try:
        positions = nx.spring_layout(display, seed=policy["layout_seed"], iterations=40)
        nx.draw_networkx(display, positions, ax=axis, node_size=350, font_size=6, arrows=True,
                         labels={node: f"{node.bank_id}:{node.account_id}" for node in display},
                         connectionstyle="arc3,rad=0.10")
        axis.set_title(f"Observed transfers — {'PARTIAL VIEW' if partial else 'full bounded snapshot'}\n"
                       f"{len(nodes)}/{len(graph)} accounts; {len(edges)}/{graph.number_of_edges()} transfers; "
                       "relationships alone do not establish crime")
        axis.axis("off")
        fig.tight_layout()
        fig.savefig(Path(path), dpi=140)
    finally:
        plt.close(fig)
    return {"status": "truncated" if partial else "evaluated", "nodes_shown": len(nodes),
            "edges_shown": len(edges), "selection": "sorted_bank_account_then_edge_id", "layout_seed": policy["layout_seed"]}
