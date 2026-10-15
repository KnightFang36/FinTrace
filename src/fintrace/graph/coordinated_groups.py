"""Repeated synchronized directed-counterparty groups, without identity inference."""
from collections import defaultdict
from fintrace.graph.temporal_paths import new_budget


def find_coordinated_groups(graph, policy):
    budget = new_budget(policy)
    buckets = defaultdict(list)
    bucket_seconds = policy["coordination_bucket_minutes"] * 60
    window_seconds = policy["coordination_window_minutes"] * 60
    # Windows/buckets are UTC epoch-aligned, independent of the earliest input row.
    for *_, data in graph.edges(data=True):
        item = data["transaction"]
        if not budget.step():
            return [], budget.coverage()
        for direction, party, account, currency in (
            ("incoming", item.receiver, item.sender, item.payment_currency),
            ("outgoing", item.sender, item.receiver, item.receiving_currency),
        ):
            if item.payment_currency == item.receiving_currency:
                bucket = int(item.occurred_at.timestamp()) // bucket_seconds
                buckets[direction, party, currency, bucket].append((account, item))
    candidates = defaultdict(list)
    for (direction, party, currency, bucket), items in sorted(buckets.items()):
        if not budget.step():
            return [], budget.coverage()
        members = tuple(sorted({account for account, _ in items}))
        if len(members) >= policy["coordination_minimum_accounts"]:
            window = (bucket * bucket_seconds) // window_seconds
            candidates[direction, party, currency, members].append((window, bucket, items))
    results = []
    for (direction, party, currency, members), entries in sorted(candidates.items()):
        if not budget.step():
            break
        # Only complete fixed windows are comparable; partial boundary windows are withheld.
        start, end = graph.graph["start"].timestamp(), graph.graph["cutoff"].timestamp()
        entries = [entry for entry in entries if start <= entry[0] * window_seconds
                   and (entry[0] + 1) * window_seconds <= end]
        windows = sorted({entry[0] for entry in entries})
        if len(windows) < policy["coordination_repeated_windows"]:
            continue
        if not budget.result_allowed(len(results)):
            break
        results.append({"direction": direction, "counterparty": party, "currency": currency,
                        "participants": members, "windows": windows,
                        "buckets": sorted({entry[1] for entry in entries}),
                        "transactions": tuple(sorted({item.transaction_id: item for _, _, items in entries
                                                       for _, item in items}.values(),
                                                      key=lambda item: (item.occurred_at, item.transaction_id)))})
    return results, budget.coverage()
