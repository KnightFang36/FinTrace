"""Frequency comparison with complete, fixed 24-hour-offset historical windows."""
from datetime import timedelta
from decimal import Decimal
from fintrace.rules.common import (
    Outcome, account_events, active_records, active_start, exact_arithmetic,
    has_coverage, make_finding,
)


@exact_arithmetic
def detect_burst(transactions, settings, policy, cutoff, context):
    result = Outcome()
    start = active_start(settings, cutoff)
    current = account_events(active_records(transactions, settings, cutoff), context)
    if not has_coverage(start, cutoff, context):
        result.skipped["incomplete_active_window"] += max(len(current), 1)
        return result
    windows = []
    for day in range(1, settings["history_days"] + 1):
        # Days mean fixed 24-hour UTC offsets, not local calendar dates.
        if has_coverage(start - timedelta(days=day), start - timedelta(days=day - 1), context):
            windows.append((start - timedelta(days=day), cutoff - timedelta(days=day)))
    if len(windows) < settings["minimum_complete_history_days"]:
        result.skipped["insufficient_complete_history"] += max(len(current), 1)
        return result
    historical = account_events(transactions, context)
    for account, rows in sorted(current.items()):
        window_rows = [[row for row in historical[account] if left <= row.occurred_at < right]
                       for left, right in windows]
        counts = [len(items) for items in window_rows]
        ordered = sorted(counts)
        middle = len(counts) // 2
        baseline = (Decimal(ordered[middle]) if len(ordered) % 2
                    else (Decimal(ordered[middle - 1]) + Decimal(ordered[middle])) / 2)
        if baseline == 0:
            result.skipped["zero_historical_baseline"] += 1
            continue
        result.evaluated_groups += 1
        if len(rows) < settings["minimum_count"] or Decimal(len(rows)) < baseline * Decimal(settings["baseline_multiplier"]):
            continue
        result.add(make_finding(
            "burst", account, None, rows,
            {"current_count": len(rows), "historical_counts": counts,
             "historical_median_count": baseline, "complete_comparison_days": len(windows),
             "comparison_windows": [
                 {"start": a, "end": b, "transaction_ids": [row.transaction_id for row in items]}
                 for (a, b), items in zip(windows, window_rows)
             ]},
            settings, policy, cutoff,
            f"Observed {len(rows)} transfers versus a median of {baseline} in "
            f"{len(windows)} complete comparable historical windows.", role="high_frequency_account",
            extra_ids=tuple(row.transaction_id for items in window_rows for row in items),
            limitations=("Historical comparison days are fixed 24-hour UTC offsets.",
                         "Baseline comparison transactions are historical evidence outside the active window.",
                         "Frequency alone can also reflect legitimate business activity."),
        ), policy)
    return result
