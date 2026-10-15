"""Work-bounded DFS; timestamp ties never establish a transfer order."""
from dataclasses import dataclass, field
from time import monotonic


@dataclass
class SearchBudget:
    max_expansions: int
    max_results: int
    seconds: int
    expansions: int = 0
    reasons: set = field(default_factory=set)

    def __post_init__(self):
        self.deadline = monotonic() + self.seconds

    def step(self):
        if monotonic() >= self.deadline:
            self.reasons.add("runtime_budget_exhausted")
            return False
        if self.expansions >= self.max_expansions:
            self.reasons.add("expansion_budget_exhausted")
            return False
        self.expansions += 1
        return True

    def result_allowed(self, count):
        if count >= self.max_results:
            self.reasons.add("finding_budget_exhausted")
            return False
        return True

    def coverage(self):
        return {"status": "truncated" if self.reasons else "evaluated",
                "reason_codes": sorted(self.reasons), "expansions": self.expansions,
                "limits": {"max_expansions": self.max_expansions, "max_results": self.max_results,
                           "max_search_seconds": self.seconds}}


def new_budget(policy):
    return SearchBudget(policy["max_expansions"], policy["max_findings_per_feature"], policy["max_search_seconds"])


def temporal_search(graph, seeds, minimum, maximum, budget, *, cycles=False, components=None):
    results = []
    adjacency = {
        node: sorted((data["transaction"] for *_, data in graph.out_edges(node, data=True)),
                     key=lambda row: (row.occurred_at, row.transaction_id))
        for node in graph
    }

    def walk(origin, node, path, visited, currency):
        for item in adjacency[node]:
            if not budget.step():
                return False
            if item.payment_currency != item.receiving_currency:
                continue
            if path and (item.occurred_at <= path[-1].occurred_at or item.payment_currency != currency):
                continue
            if cycles and components.get(item.receiver) != components.get(origin):
                continue
            closed = item.receiver == origin
            if item.receiver in visited and not (cycles and closed):
                continue
            next_path = path + (item,)
            if (cycles and closed and len(next_path) >= minimum) or (not cycles and len(next_path) >= minimum):
                if not budget.result_allowed(len(results)):
                    return False
                results.append(next_path)
            if closed or len(next_path) >= maximum:
                continue
            if not walk(origin, item.receiver, next_path, visited | {item.receiver}, item.payment_currency):
                return False
        return True

    for origin in seeds:
        if not walk(origin, origin, (), {origin}, None):
            break
    return results, budget.coverage()


def find_temporal_paths(graph, seeds, graph_policy):
    return temporal_search(graph, seeds, graph_policy["minimum_hops"], graph_policy["maximum_hops"],
                           new_budget(graph_policy))
