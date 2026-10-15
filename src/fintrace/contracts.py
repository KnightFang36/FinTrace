"""Shared records for label-free deterministic transaction-pattern analysis."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


def utc_instant(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("An explicit timezone-aware instant is required")
    return value.astimezone(timezone.utc)


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, datetime):
        return utc_instant(value).isoformat()
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, Mapping):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_id(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class AccountKey:
    bank_id: str
    account_id: str

    def __post_init__(self):
        for value in (self.bank_id, self.account_id):
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError("Account keys require exact non-empty bank/account strings")


TRANSACTION_FIELDS = (
    "transaction_id", "dataset_id", "occurred_at", "sender_bank_id", "sender_account_id",
    "receiver_bank_id", "receiver_account_id", "amount_paid", "payment_currency",
    "amount_received", "receiving_currency",
)
TRANSACTION_METADATA = frozenset({
    "schema_version", "run_id", "source_file_id", "source_record_number", "source_row_hash",
    "normalization_version", "source_timestamp", "timestamp_precision", "payment_format",
    "is_self_transfer",
})


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    dataset_id: str
    occurred_at: datetime
    sender: AccountKey
    receiver: AccountKey
    amount_paid: Decimal
    payment_currency: str
    amount_received: Decimal
    receiving_currency: str

    @classmethod
    def from_mapping(cls, row: Mapping) -> Transaction:
        if not isinstance(row, Mapping):
            raise ValueError("A normalized transaction mapping is required")
        unexpected = set(row) - set(TRANSACTION_FIELDS) - TRANSACTION_METADATA
        if unexpected:
            raise ValueError("Unexpected transaction fields; only the label-free normalized schema is accepted")
        if not set(TRANSACTION_FIELDS) <= set(row):
            raise ValueError("Normalized transaction fields are missing")
        for key in ("transaction_id", "dataset_id", "payment_currency", "receiving_currency"):
            value = row[key]
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"{key} must be exact non-empty text")
        amounts = []
        for key in ("amount_paid", "amount_received"):
            value = row[key]
            if not isinstance(value, (str, Decimal)):
                raise ValueError("Amounts must be Decimal or decimal text, never binary floats")
            try:
                value = Decimal(value)
            except InvalidOperation as error:
                raise ValueError("Invalid decimal amount") from error
            if not value.is_finite() or value <= 0:
                raise ValueError("Amounts must be positive finite decimals")
            # The normalized boundary promises exact decimal(38,8) values.
            if value.as_tuple().exponent < -8 or value.adjusted() >= 30:
                raise ValueError("Amount exceeds the normalized decimal(38,8) contract")
            amounts.append(value)
        return cls(row["transaction_id"], row["dataset_id"], utc_instant(row["occurred_at"]),
                   AccountKey(row["sender_bank_id"], row["sender_account_id"]),
                   AccountKey(row["receiver_bank_id"], row["receiver_account_id"]),
                   amounts[0], row["payment_currency"], amounts[1], row["receiving_currency"])

    @property
    def is_self_transfer(self) -> bool:
        return self.sender == self.receiver


@dataclass(frozen=True)
class Finding:
    finding_id: str
    rule_id: str
    rule_version: str
    dataset_id: str
    subject_accounts: tuple[AccountKey, ...]
    subject_roles: tuple[str, ...]
    window_start: datetime
    window_end: datetime
    cutoff: datetime
    transaction_ids: tuple[str, ...]
    measurements: dict
    thresholds: dict
    currency: str | None
    explanation: str
    limitations: tuple[str, ...]
    coverage_status: str = "evaluated"
    evidence_graph_ref: str | None = None


@dataclass(frozen=True)
class FeatureCoverage:
    feature_id: str
    status: str
    reason_codes: tuple[str, ...]
    analysis_window: dict
    source_coverage: dict
    observed_work: dict = field(default_factory=dict)
    search_budget: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RuleResult:
    schema_version: str
    engine_version: str
    run_id: str
    dataset_id: str
    cutoff: datetime
    policy_version: str
    policy_hash: str
    findings: tuple[Finding, ...]
    coverage: tuple[FeatureCoverage, ...]
    scope: dict

    def to_dict(self) -> dict:
        return json_value(self)


def parse_finding(value) -> Finding:
    """Validate the public evidence boundary without accepting arbitrary enrichment fields."""
    from dataclasses import fields

    if isinstance(value, Finding):
        value = asdict(value)
    if not isinstance(value, Mapping) or set(value) != {item.name for item in fields(Finding)}:
        raise ValueError("Expected the exact label-free Finding schema")
    data = dict(value)
    for name in ("finding_id", "rule_id", "rule_version", "dataset_id", "explanation"):
        if not isinstance(data[name], str) or not data[name].strip():
            raise ValueError(f"Finding {name} must be non-empty text")
    data["subject_accounts"] = tuple(
        item if isinstance(item, AccountKey) else AccountKey(**item) for item in data["subject_accounts"]
    )
    data["subject_roles"] = tuple(data["subject_roles"])
    if (not data["subject_accounts"] or len(set(data["subject_accounts"])) != len(data["subject_accounts"])
            or len(data["subject_accounts"]) != len(data["subject_roles"])
            or any(not isinstance(role, str) or not role for role in data["subject_roles"])):
        raise ValueError("Finding subjects require distinct accounts and explicit matching roles")
    for name in ("window_start", "window_end", "cutoff"):
        data[name] = utc_instant(data[name])
    if not data["window_start"] < data["window_end"] <= data["cutoff"]:
        raise ValueError("Invalid finding window/cutoff")
    ids = data["transaction_ids"]
    if (not isinstance(ids, (tuple, list)) or not ids or len(set(ids)) != len(ids)
            or any(not isinstance(item, str) or not item for item in ids)):
        raise ValueError("Finding evidence requires distinct non-empty transaction IDs")
    data["transaction_ids"] = tuple(ids)
    if not isinstance(data["measurements"], dict) or not isinstance(data["thresholds"], dict):
        raise ValueError("Finding measurements and thresholds must be mappings")
    if data["currency"] is not None and (not isinstance(data["currency"], str) or not data["currency"]):
        raise ValueError("Invalid finding currency")
    if not isinstance(data["limitations"], (tuple, list)) or any(not isinstance(item, str) for item in data["limitations"]):
        raise ValueError("Finding limitations must be text entries")
    data["limitations"] = tuple(data["limitations"])
    if data["coverage_status"] not in ("evaluated", "truncated"):
        raise ValueError("Only evidence-backed evaluated/truncated findings are eligible")
    canonical_json(data)
    return Finding(**data)
