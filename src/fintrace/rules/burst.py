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
        counts = sorted(sum(left <= row.occurred_at < right for row in historical[account])
                        for left, right in windows)
        middle = len(counts) // 2
        baseline = (Decimal(counts[middle]) if len(counts) % 2
                    else (Decimal(counts[middle - 1]) + Decimal(counts[middle])) / 2)
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
             "comparison_windows": [{"start": a, "end": b} for a, b in windows]},
            settings, policy, cutoff,
            f"Observed {len(rows)} transfers versus a median of {baseline} in "
            f"{len(windows)} complete comparable historical windows.", role="high_frequency_account",
            limitations=("Historical comparison days are fixed 24-hour UTC offsets.",
                         "Frequency alone can also reflect legitimate business activity."),
        ), policy)
    return result
