"""Strictly later outgoing transfers allocated to observed inflows by FIFO."""
from collections import defaultdict, deque
from decimal import Decimal
from fintrace.rules.common import (
    Outcome, active_records, eligible_subject, exact_arithmetic, make_finding,
)


@exact_arithmetic
def detect_pass_through(transactions, settings, policy, cutoff, context):
    groups = defaultdict(lambda: {"incoming": [], "outgoing": []})
    for row in active_records(transactions, settings, cutoff):
        if eligible_subject(row.receiver, context):
            groups[row.receiver, row.receiving_currency]["incoming"].append(row)
        if eligible_subject(row.sender, context):
            groups[row.sender, row.payment_currency]["outgoing"].append(row)
    result = Outcome()
    for (account, currency), sides in sorted(groups.items()):
        result.evaluated_groups += 1
        incoming, outgoing = sides["incoming"], sides["outgoing"]
        if len(incoming) < settings["minimum_incoming_count"] or not outgoing:
            continue
        total = sum((row.amount_received for row in incoming), Decimal(0))
        events = []
        # Outflows precede inflows at tied timestamps: ties cannot prove forwarding.
        events.extend((row.occurred_at, 1, row.transaction_id, row) for row in incoming)
        events.extend((row.occurred_at, 0, row.transaction_id, row) for row in outgoing)
        available = deque()
        ledger = []
        forwarded = Decimal(0)
        allocation_budget = policy.get("execution", {}).get("max_allocation_entries", 20000)
        truncated = False
        for _, direction, _, row in sorted(events):
            if direction == 1:
                available.append([row, row.amount_received])
                continue
            remaining = row.amount_paid
            while remaining > 0 and available:
                inflow, balance = available[0]
                allocated = min(remaining, balance)
                if len(ledger) >= allocation_budget:
                    truncated = True
                    break
                ledger.append({
                    "incoming_transaction_id": inflow.transaction_id,
                    "outgoing_transaction_id": row.transaction_id,
                    "allocated_amount": allocated,
                    "elapsed_seconds": int((row.occurred_at - inflow.occurred_at).total_seconds()),
                })
                forwarded += allocated
                remaining -= allocated
                available[0][1] -= allocated
                if available[0][1] == 0:
                    available.popleft()
            if truncated:
                break
        if truncated:
            result.truncated_groups += 1
            continue
        if forwarded < total * Decimal(settings["minimum_forwarded_ratio"]):
            continue
        reported_ratio = (forwarded / total).quantize(Decimal("0.000001"))
        involved_outgoing = {entry["outgoing_transaction_id"] for entry in ledger}
        evidence = incoming + [row for row in outgoing if row.transaction_id in involved_outgoing]
        result.add(make_finding(
            "pass_through", account, currency, evidence,
            {"incoming_count": len(incoming), "incoming_total": total,
             "allocated_forwarded_value": forwarded, "reported_forwarded_ratio": reported_ratio,
             "ratio_reporting_decimal_places": 6, "allocations": ledger,
             "allocation_method": "fifo_observed_inflows"},
            settings, policy, cutoff,
            f"Forwarded an estimated {forwarded} of {total} observed incoming {currency} "
            f"using strictly later transfers (reported ratio {reported_ratio}).", role="forwarder",
            limitations=(
                "FIFO is a declared attribution assumption; opening balance and exact provenance are unknown.",
                "Outflows at the same timestamp as an inflow cannot consume that inflow.",
                "Same-time outflows use stable identifier order for bookkeeping, not inferred chronology.",
                "The displayed ratio is rounded; the threshold comparison uses exact cross multiplication.",
            ),
        ), policy)
    return result
