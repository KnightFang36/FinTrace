"""Public evidence records and policy validation do not require the data stack."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from fintrace.contracts import AccountKey, Transaction, canonical_json, utc_instant
from fintrace.rules.policy import load_policy


class RuleContractTests(unittest.TestCase):
    def record(self):
        return {
            "transaction_id": "fixture-1", "dataset_id": "fixture",
            "occurred_at": datetime(2022, 9, 1, tzinfo=timezone.utc),
            "sender_bank_id": "010", "sender_account_id": "A",
            "receiver_bank_id": "10", "receiver_account_id": "A",
            "amount_paid": Decimal("0.00000001"), "payment_currency": "Bitcoin",
            "amount_received": Decimal("1.10"), "receiving_currency": "USD",
        }

    def test_exact_account_strings_and_money_roundtrip(self):
        transaction = Transaction.from_mapping(self.record())
        self.assertFalse(transaction.is_self_transfer)
        text = canonical_json(transaction)
        self.assertIn("0.00000001", text)
        self.assertIn('"bank_id":"010"', text)

    def test_binary_float_and_label_fields_are_rejected(self):
        row = self.record()
        row["amount_paid"] = 0.1
        with self.assertRaises(ValueError):
            Transaction.from_mapping(row)
        row = self.record()
        row["is_laundering"] = 1
        with self.assertRaises(ValueError):
            Transaction.from_mapping(row)

    def test_naive_cutoff_and_blank_account_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            utc_instant(datetime(2022, 1, 1))
        with self.assertRaises(ValueError):
            AccountKey("1", "")

    def test_checked_repository_policy_loads(self):
        root = Path(__file__).resolve().parents[2]
        self.assertEqual(load_policy(root / "config/rules.toml")["policy_version"], "demo-v1")
