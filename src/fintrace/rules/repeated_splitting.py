"""Descriptive repeated-payment episodes, without asserting reporting evasion."""
from collections import defaultdict
from decimal import Decimal
from fintrace.rules.common import Outcome, active_records, eligible_subject, exact_arithmetic, make_finding


@exact_arithmetic
def detect_repeated_splitting(transactions, settings, policy, cutoff, context):
    groups = defaultdict(list)
    for row in active_records(transactions, settings, cutoff):
        if eligible_subject(row.sender, context):
            groups[row.sender, row.receiver, row.payment_currency].append(row)
    result = Outcome()
    for (sender, receiver, currency), rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda row: (row.occurred_at, row.transaction_id))
        result.evaluated_groups += 1
        if len(rows) < settings["minimum_related_payments"]:
            continue
        total = sum((row.amount_paid for row in rows), Decimal(0))
        result.add(make_finding(
            "repeated_splitting", sender, currency, rows,
            {"payment_count": len(rows), "episode_total": total,
             "recipient": receiver, "payment_values": [row.amount_paid for row in rows]},
            settings, policy, cutoff,
            f"Made {len(rows)} repeated payments to one counterparty in {currency}; "
            "this descriptive episode may also be legitimate recurring activity.", role="payer",
            limitations=("No reporting threshold or deliberate evasion is inferred.",),
        ), policy)
    return result
