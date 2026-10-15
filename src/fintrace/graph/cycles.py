"""SCC candidate narrowing followed by chronological edge-level verification."""
import networkx as nx
from fintrace.graph.temporal_paths import new_budget, temporal_search


def find_temporal_cycles(graph, seeds, graph_policy):
    components = {}
    for number, nodes in enumerate(nx.strongly_connected_components(graph)):
        if len(nodes) >= graph_policy["minimum_cycle_length"]:
            components.update((node, number) for node in nodes)
    eligible = [node for node in seeds if node in components]
    return temporal_search(graph, eligible, graph_policy["minimum_cycle_length"],
                           graph_policy["maximum_cycle_length"], new_budget(graph_policy),
                           cycles=True, components=components)
