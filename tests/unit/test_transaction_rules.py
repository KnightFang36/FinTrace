"""Rule evidence tests use handcrafted records, not benchmark labels."""

import copy
import tomllib
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fintrace.contracts import AccountKey
from fintrace.rules.engine import evaluate_rules
from fintrace.rules.policy import validate_policy

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = datetime(2022, 9, 10, 13, tzinfo=timezone.utc)


def transaction(identifier, *, minutes=10, sender="S", receiver="A", amount="100",
                paid_currency="USD", received_currency="USD", received=None, when=None,
                sender_bank="1", receiver_bank="1"):
    return {
        "transaction_id": identifier, "dataset_id": "fixture",
        "occurred_at": when or CUTOFF - timedelta(minutes=minutes),
        "sender_bank_id": sender_bank, "sender_account_id": sender,
        "receiver_bank_id": receiver_bank, "receiver_account_id": receiver,
        "amount_paid": Decimal(amount), "payment_currency": paid_currency,
        "amount_received": Decimal(received if received is not None else amount),
        "receiving_currency": received_currency,
    }


def policy_for(*enabled, **overrides):
    with (ROOT / "config/rules.toml").open("rb") as handle:
        policy = tomllib.load(handle)
    for key, value in policy.items():
        if isinstance(value, dict) and "enabled" in value:
            value["enabled"] = key in enabled
    for key, value in overrides.items():
        policy[key].update(value)
    return policy


def run(rows, *rules, policy=None, context=None, history=None):
    return evaluate_rules(rows, history, policy=policy or policy_for(*rules), cutoff=CUTOFF,
                          context={"dataset_id": "fixture", **(context or {})})


class CounterpartyRuleTests(unittest.TestCase):
    def test_fan_in_counts_distinct_accounts_not_payment_count(self):
        rows = [transaction(str(i), sender=f"S{i}") for i in range(8)]
        result = run(rows, "fan_in")
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].measurements["distinct_senders"], 8)
        self.assertFalse(run([transaction(str(i), sender="S") for i in range(9)], "fan_in").findings)

    def test_currency_groups_are_not_combined(self):
        rows = [transaction(str(i), sender=f"S{i}", received_currency="USD" if i < 4 else "EUR")
                for i in range(8)]
        self.assertFalse(run(rows, "fan_in").findings)

    def test_bank_strings_are_part_of_counterparty_identity(self):
        rows = [transaction(str(i), sender="S", sender_bank=str(i)) for i in range(8)]
        self.assertEqual(len(run(rows, "fan_in").findings), 1)

    def test_fan_out_has_only_distributor_as_subject(self):
        rows = [transaction(str(i), sender="A", receiver=f"R{i}") for i in range(8)]
        finding = run(rows, "fan_out").findings[0]
        self.assertEqual(finding.subject_accounts, (AccountKey("1", "A"),))
        self.assertEqual(finding.subject_roles, ("distributor",))
        self.assertEqual(set(finding.transaction_ids), {str(i) for i in range(8)})

    def test_repeated_payments_are_descriptive_and_do_not_claim_evasion(self):
        rows = [transaction(str(i), sender="A", receiver="Payroll") for i in range(5)]
        finding = run(rows, "repeated_splitting").findings[0]
        self.assertIn("legitimate", finding.explanation)
        self.assertEqual(finding.measurements["episode_total"], Decimal("500"))

    def test_large_decimal_totals_are_exact(self):
        rows = [transaction(str(i), sender=f"S{i}", amount="10000000000000000000000000000.01")
                for i in range(8)]
        result = run(rows, "fan_in")
        self.assertEqual(str(result.findings[0].measurements["incoming_total"]),
                         "80000000000000000000000000000.08")


class PassThroughTests(unittest.TestCase):
    def incoming(self, **kwargs):
        return [transaction(f"in-{i}", minutes=40-i, sender=f"S{i}", **kwargs) for i in range(3)]

    def test_fifo_evidence_has_allocation_ledger_and_exact_denominator(self):
        rows = self.incoming() + [transaction("out", minutes=5, sender="A", receiver="R", amount="250")]
        finding = run(rows, "pass_through").findings[0]
        self.assertEqual(finding.measurements["incoming_total"], Decimal("300"))
        self.assertEqual(finding.measurements["allocated_forwarded_value"], Decimal("250"))
        self.assertEqual([item["allocated_amount"] for item in finding.measurements["allocations"]],
                         [Decimal("100"), Decimal("100"), Decimal("50")])
        self.assertEqual(set(finding.transaction_ids), {"in-0", "in-1", "in-2", "out"})
        self.assertTrue(all(item["elapsed_seconds"] > 0 for item in finding.measurements["allocations"]))

    def test_preceding_or_tied_outflow_cannot_consume_incoming(self):
        incoming = [transaction(f"in-{i}", minutes=10, sender=f"S{i}") for i in range(3)]
        for minute in (10, 20):
            rows = incoming + [transaction("out", minutes=minute, sender="A", receiver="R", amount="300")]
            with self.subTest(minute=minute):
                self.assertFalse(run(rows, "pass_through").findings)

    def test_no_cross_currency_attribution(self):
        rows = self.incoming() + [
            transaction("out", minutes=5, sender="A", receiver="R", amount="300", paid_currency="EUR")
        ]
        self.assertFalse(run(rows, "pass_through").findings)

    def test_inflow_is_never_allocated_twice(self):
        rows = self.incoming() + [
            transaction("out1", minutes=5, sender="A", receiver="R", amount="250"),
            transaction("out2", minutes=4, sender="A", receiver="R", amount="250"),
        ]
        finding = run(rows, "pass_through").findings[0]
        self.assertEqual(finding.measurements["allocated_forwarded_value"], Decimal("300"))
        self.assertEqual(sum(item["allocated_amount"] for item in finding.measurements["allocations"]),
                         Decimal("300"))

    def test_exact_ratio_boundary_uses_full_precision(self):
        rows = self.incoming() + [transaction("out", minutes=5, sender="A", receiver="R", amount="240")]
        self.assertEqual(len(run(rows, "pass_through").findings), 1)
        rows[-1]["amount_paid"] = Decimal("239.99999999")
        self.assertFalse(run(rows, "pass_through").findings)

    def test_allocation_budget_withholds_partial_evidence(self):
        rows = self.incoming() + [transaction("out", minutes=5, sender="A", receiver="R", amount="300")]
        policy = policy_for("pass_through")
        policy["execution"] = {"max_allocation_entries": 1}
        result = run(rows, policy=policy)
        self.assertFalse(result.findings)
        coverage = next(item for item in result.coverage if item.feature_id == "pass_through")
        self.assertEqual(coverage.status, "truncated")


class RuleBoundaryTests(unittest.TestCase):
    def test_self_transfers_are_not_movement_findings(self):
        rows = [transaction(str(i), sender="A", receiver="A") for i in range(20)]
        result = run(rows, "fan_in", "fan_out", "repeated_splitting", "pass_through")
        self.assertFalse(result.findings)
        self.assertEqual(result.scope["excluded_self_transfers"], 20)

    def test_half_open_window_and_cutoff(self):
        rows = [transaction(str(i), sender=f"S{i}", minutes=60) for i in range(7)]
        self.assertFalse(run(rows + [transaction("late", sender="S8", when=CUTOFF)], "fan_in").findings)
        self.assertFalse(run(rows + [transaction("old", sender="S8", minutes=61)], "fan_in").findings)
        self.assertEqual(len(run(rows + [transaction("edge", sender="S8", minutes=60)], "fan_in").findings), 1)

    def test_future_data_and_input_order_do_not_change_results(self):
        rows = [transaction(str(i), sender=f"S{i}") for i in range(8)]
        first = run(rows, "fan_in").to_dict()
        second = run(list(reversed(rows)) + [transaction("future", minutes=-1)], "fan_in").to_dict()
        self.assertEqual(first, second)

    def test_conflicting_ids_and_mixed_datasets_are_rejected(self):
        one = transaction("same")
        with self.assertRaises(ValueError):
            run([one, transaction("same", amount="200")], "fan_in")
        two = transaction("different")
        two["dataset_id"] = "other"
        with self.assertRaises(ValueError):
            run([one, two], "fan_in")

    def test_label_columns_and_label_context_are_rejected(self):
        row = transaction("one")
        row["is_laundering"] = 1
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            run([row], "fan_in")
        with self.assertRaisesRegex(ValueError, "Unknown context"):
            run([], "fan_in", context={"labels": [1]})

    def test_unknown_history_and_unimplemented_features_are_visible(self):
        policy = policy_for("burst", "dormant_activation", "layering", "cash_out")
        result = run([transaction("one")], policy=policy)
        status = {item.feature_id: item.status for item in result.coverage}
        self.assertEqual(status["burst"], "unavailable")
        self.assertEqual(status["dormant_activation"], "unavailable")
        self.assertEqual(status["layering"], "unavailable")
        self.assertEqual(status["cash_out"], "unavailable")

    def test_input_and_finding_evidence_budgets(self):
        policy = policy_for("fan_in")
        policy["execution"] = {"max_input_transactions": 1}
        with self.assertRaisesRegex(ValueError, "budget"):
            run([transaction("1"), transaction("2")], policy=policy)
        policy["execution"] = {"max_evidence_transactions": 7}
        result = run([transaction(str(i), sender=f"S{i}") for i in range(8)], policy=policy)
        self.assertFalse(result.findings)
        self.assertEqual(next(c for c in result.coverage if c.feature_id == "fan_in").status, "truncated")

    def test_invalid_policies_are_rejected_before_detection(self):
        base = policy_for("pass_through")
        for change in (
            {"minimum_forwarded_ratio": "NaN"}, {"minimum_forwarded_ratio": "1.1"},
            {"minimum_incoming_count": True}, {"require_strict_time_order": False},
        ):
            policy = copy.deepcopy(base)
            policy["pass_through"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_policy(policy)
        policy = policy_for("burst", burst={"minimum_complete_history_days": 9})
        with self.assertRaises(ValueError):
            validate_policy(policy)
