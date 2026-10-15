"""Evidence factories, exact arithmetic, active windows and coverage checks."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import localcontext
from functools import wraps

from fintrace.contracts import AccountKey, Finding, Transaction, content_id, utc_instant
from fintrace.rules.policy import execution_limits

RULE_VERSION = "transaction-rules-v1"


def exact_arithmetic(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with localcontext() as context:
            context.prec = 60
            return function(*args, **kwargs)
    return wrapped


@dataclass
class Outcome:
    findings: list[Finding] = field(default_factory=list)
    skipped: Counter = field(default_factory=Counter)
    evaluated_groups: int = 0
    truncated_groups: int = 0

    def add(self, finding: Finding, policy: dict):
        limits = execution_limits(policy)
        if (
            len(self.findings) >= limits["max_findings_per_rule"]
            or len(finding.transaction_ids) > limits["max_evidence_transactions"]
            or len(finding.measurements.get("allocations", [])) > limits["max_allocation_entries"]
        ):
            self.truncated_groups += 1
        else:
            self.findings.append(finding)


def active_start(settings: dict, cutoff: datetime) -> datetime:
    minutes = settings.get("active_window_minutes", settings.get("window_minutes"))
    return cutoff - timedelta(minutes=minutes)


def active_records(transactions, settings, cutoff):
    start = active_start(settings, cutoff)
    return [row for row in transactions if start <= row.occurred_at < cutoff]


def eligible_subject(account: AccountKey, context: dict) -> bool:
    subjects = context.get("subject_accounts")
    return not subjects or account in subjects


def directional_groups(transactions, settings, cutoff, direction, context):
    groups = defaultdict(list)
    for transaction in active_records(transactions, settings, cutoff):
        account = transaction.receiver if direction == "incoming" else transaction.sender
        currency = transaction.receiving_currency if direction == "incoming" else transaction.payment_currency
        if eligible_subject(account, context):
            groups[account, currency].append(transaction)
    return groups


def account_events(transactions, context):
    groups = defaultdict(list)
    for transaction in transactions:
        for account in (transaction.sender, transaction.receiver):
            if eligible_subject(account, context):
                groups[account].append(transaction)
    return groups


def make_finding(rule, account, currency, transactions, measurements, settings, policy,
                 cutoff, explanation, *, role, limitations=(), extra_ids=()):
    start = active_start(settings, cutoff)
    ids = tuple(sorted({row.transaction_id for row in transactions} | set(extra_ids)))
    version = RULE_VERSION + ":" + policy["policy_version"] + "@" + content_id(policy)[:16]
    fields = {
        "rule": rule, "dataset_id": transactions[0].dataset_id,
        "account": account, "currency": currency, "ids": ids,
        "measurements": measurements, "thresholds": settings, "start": start,
        "end": cutoff, "version": version,
    }
    return Finding(
        finding_id=content_id(fields), rule_id=rule, rule_version=version,
        dataset_id=transactions[0].dataset_id,
        subject_accounts=(account,), subject_roles=(role,),
        window_start=start, window_end=cutoff, cutoff=cutoff, transaction_ids=ids,
        measurements=measurements, thresholds=dict(settings), currency=currency,
        explanation=explanation,
        limitations=(
            "A transaction pattern warrants review; it does not establish criminal intent.",
            "Self-transfers are excluded from movement and frequency indicators.",
            *limitations,
        ),
    )


def source_intervals(context: dict) -> tuple[list, list]:
    def parse(name):
        intervals = []
        for value in context.get(name, []):
            if not isinstance(value, dict) or set(value) != {"start", "end"}:
                raise ValueError(f"Invalid {name}")
            start, end = utc_instant(value["start"]), utc_instant(value["end"])
            if start >= end:
                raise ValueError(f"Invalid {name} interval")
            intervals.append((start, end))
        intervals.sort()
        if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
            raise ValueError(f"Overlapping {name}")
        return intervals
    return parse("observation_intervals"), parse("known_gaps")


def has_coverage(start, end, context):
    intervals, gaps = source_intervals(context)
    if any(a < end and start < b for a, b in gaps):
        return False
    cursor = start
    for left, right in intervals:
        if right <= cursor:
            continue
        if left > cursor:
            return False
        cursor = max(cursor, right)
        if cursor >= end:
            return True
    return False
