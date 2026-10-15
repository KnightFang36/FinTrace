"""Deterministic validation of the ten financial source fields, without labels."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Sequence
from zoneinfo import ZoneInfo

AMOUNT_PRECISION = 38
AMOUNT_SCALE = 8
KNOWN_FORMATS = frozenset({"ACH", "Bitcoin", "Cash", "Cheque", "Credit Card", "Reinvestment", "Wire"})
FIELD_NAMES = (
    "source_timestamp", "sender_bank_id", "sender_account_id",
    "receiver_bank_id", "receiver_account_id", "amount_received",
    "receiving_currency", "amount_paid", "payment_currency", "payment_format",
)


@dataclass(frozen=True)
class RowValidation:
    record: dict | None
    issues: tuple[dict, ...]


def _issue(field: str, code: str, message: str, severity: str = "error") -> dict:
    return {"field": field, "code": code, "message": message, "severity": severity}


def _amount(value: str) -> Decimal:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("Amount must be finite ordinary decimal text")
    whole, _, fraction = value.partition(".")
    if len(fraction) > AMOUNT_SCALE or len(whole.lstrip("0")) > AMOUNT_PRECISION - AMOUNT_SCALE:
        raise ValueError("Amount exceeds decimal(38,8); values are never rounded")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("Invalid decimal amount") from error
    if result <= 0:
        raise ValueError("Amount must be positive")
    return result


@lru_cache(maxsize=65536)
def _timestamp(value: str, zone_name: str, precision: str) -> datetime:
    pattern = r"[0-9]{4}/[0-9]{2}/[0-9]{2} [0-9]{2}:[0-9]{2}"
    if precision == "second":
        pattern += r":[0-9]{2}"
    if not re.fullmatch(pattern, value):
        raise ValueError("Timestamp does not match declared source precision")
    naive = datetime.fromisoformat(value.replace("/", "-"))
    zone = ZoneInfo(zone_name)
    first, second = naive.replace(tzinfo=zone, fold=0), naive.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        valid = {
            item.astimezone(timezone.utc)
            for item in (first, second)
            if item.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == naive
        }
        if not valid:
            raise ValueError("Nonexistent local timestamp at timezone transition")
        if len(valid) > 1:
            raise ValueError("Ambiguous local timestamp at timezone transition")
        return valid.pop()
    return first.astimezone(timezone.utc)


def validate_transaction_fields(
    fields: Sequence[str], *, timezone_policy: str, timestamp_precision: str,
) -> RowValidation:
    """Validate financial fields; preserve exact strings and fixed-point values."""
    ZoneInfo(timezone_policy)
    if timestamp_precision not in ("minute", "second"):
        raise ValueError("Unsupported timestamp precision policy")
    if len(fields) != 10:
        return RowValidation(None, (_issue("record", "field_count", "Expected ten financial source fields"),))
    record = dict(zip(FIELD_NAMES, fields))
    issues = []
    for field in (
        "sender_bank_id", "sender_account_id", "receiver_bank_id",
        "receiver_account_id", "receiving_currency", "payment_currency",
    ):
        value = record[field]
        if not value or value != value.strip():
            issues.append(_issue(field, "invalid_identifier_or_currency", "Required exact non-blank source text"))
    for field in ("amount_paid", "amount_received"):
        try:
            record[field] = _amount(record[field])
        except ValueError as error:
            issues.append(_issue(field, "invalid_amount", str(error)))
    try:
        record["occurred_at"] = _timestamp(record["source_timestamp"], timezone_policy, timestamp_precision)
    except ValueError as error:
        issues.append(_issue("source_timestamp", "invalid_timestamp", str(error)))
    if record["payment_format"] not in KNOWN_FORMATS:
        issues.append(_issue("payment_format", "unknown_payment_format",
                             "Unmapped source payment format; value is preserved", "warning"))
    record["timestamp_precision"] = timestamp_precision
    record["is_self_transfer"] = (
        record["sender_bank_id"], record["sender_account_id"]
    ) == (record["receiver_bank_id"], record["receiver_account_id"])
    return RowValidation(None if any(issue["severity"] == "error" for issue in issues) else record,
                         tuple(issues))
