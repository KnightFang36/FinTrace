"""Distinct outgoing counterparties, separated by payment currency."""
from decimal import Decimal
from fintrace.rules.common import Outcome, directional_groups, exact_arithmetic, make_finding


@exact_arithmetic
def detect_fan_out(transactions, settings, policy, cutoff, context):
    result = Outcome()
    for (account, currency), rows in sorted(directional_groups(
        transactions, settings, cutoff, "outgoing", context
    ).items()):
        result.evaluated_groups += 1
        recipients = sorted({row.receiver for row in rows})
        if len(recipients) < settings["minimum_distinct_recipients"]:
            continue
        total = sum((row.amount_paid for row in rows), Decimal(0))
        result.add(make_finding(
            "fan_out", account, currency, rows,
            {"distinct_recipients": len(recipients), "outgoing_count": len(rows),
             "outgoing_total": total, "counterparties": recipients},
            settings, policy, cutoff,
            f"Sent {len(rows)} payments to {len(recipients)} distinct accounts in {currency}; "
            "dispersal requires contextual review.", role="distributor",
        ), policy)
    return result
