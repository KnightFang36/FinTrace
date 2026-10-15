"""Distinct incoming counterparties, separated by receiving currency."""
from decimal import Decimal
from fintrace.rules.common import Outcome, directional_groups, exact_arithmetic, make_finding


@exact_arithmetic
def detect_fan_in(transactions, settings, policy, cutoff, context):
    result = Outcome()
    for (account, currency), rows in sorted(directional_groups(
        transactions, settings, cutoff, "incoming", context
    ).items()):
        result.evaluated_groups += 1
        senders = sorted({row.sender for row in rows})
        if len(senders) < settings["minimum_distinct_senders"]:
            continue
        total = sum((row.amount_received for row in rows), Decimal(0))
        result.add(make_finding(
            "fan_in", account, currency, rows,
            {"distinct_senders": len(senders), "incoming_count": len(rows),
             "incoming_total": total, "counterparties": senders},
            settings, policy, cutoff,
            f"Received {len(rows)} payments from {len(senders)} distinct accounts in {currency}; "
            "collection concentration requires contextual review.", role="collector",
        ), policy)
    return result
