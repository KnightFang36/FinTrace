"""Previously observed accounts reactivated after a completely covered quiet gap."""
from datetime import timedelta
from fintrace.rules.common import (
    Outcome, account_events, active_records, active_start, exact_arithmetic,
    has_coverage, make_finding,
)


@exact_arithmetic
def detect_dormant_activation(transactions, settings, policy, cutoff, context):
    result = Outcome()
    start = active_start(settings, cutoff)
    current = account_events(active_records(transactions, settings, cutoff), context)
    historical = account_events([row for row in transactions if row.occurred_at < start], context)
    for account, rows in sorted(current.items()):
        prior_rows = historical.get(account, [])
        if not prior_rows:
            result.skipped["no_prior_observed_activity"] += 1
            continue
        prior = max(prior_rows, key=lambda row: (row.occurred_at, row.transaction_id))
        first = min(rows, key=lambda row: (row.occurred_at, row.transaction_id))
        if not has_coverage(prior.occurred_at, cutoff, context):
            result.skipped["incomplete_observed_gap"] += 1
            continue
        result.evaluated_groups += 1
        gap = first.occurred_at - prior.occurred_at
        if gap < timedelta(days=settings["observed_inactivity_days"]) or len(rows) < settings["minimum_count"]:
            continue
        result.add(make_finding(
            "dormant_activation", account, None, rows,
            {"active_count": len(rows), "previous_observed_at": prior.occurred_at,
             "previous_transaction_id": prior.transaction_id,
             "first_activation_at": first.occurred_at, "observed_gap_seconds": int(gap.total_seconds())},
            settings, policy, cutoff,
            f"A previously observed account made {len(rows)} transfers after an observed "
            f"quiet gap of {int(gap.total_seconds())} seconds.", role="reactivated_account",
            extra_ids=(prior.transaction_id,),
            limitations=("Observed inactivity is not a verified bank dormancy status or account age.",
                         "The earlier activity transaction is historical evidence outside the activation window."),
        ), policy)
    return result
