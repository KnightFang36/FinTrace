"""Historical rules require complete declared coverage and actual prior evidence."""
import unittest
from datetime import timedelta
from fintrace.contracts import AccountKey
from test_transaction_rules import CUTOFF, policy_for, run, transaction


def coverage(**extra):
    return {
        "subject_accounts": [AccountKey("1", "A")],
        "observation_intervals": [{
            "start": (CUTOFF - timedelta(days=10)).isoformat(),
            "end": CUTOFF.isoformat(),
        }],
        **extra,
    }


class HistoricalRuleTests(unittest.TestCase):
    def test_burst_compares_previous_complete_windows(self):
        rows = [transaction(f"active-{i}") for i in range(4)]
        history = [transaction(f"history-{i}", when=CUTOFF - timedelta(days=i, minutes=10))
                   for i in range(1, 8)]
        policy = policy_for("burst", burst={"minimum_count": 4})
        result = run(rows, policy=policy, history=history, context=coverage())
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]
        self.assertEqual(finding.measurements["historical_counts"], [1] * 7)
        self.assertEqual(finding.measurements["current_count"], 4)
        self.assertEqual(set(finding.transaction_ids),
                         {f"active-{i}" for i in range(4)} | {f"history-{i}" for i in range(1, 8)})
        for index, window in enumerate(finding.measurements["comparison_windows"], 1):
            self.assertEqual(window["transaction_ids"], [f"history-{index}"])
        # The reported window covers one active hour; the baseline IDs predate it, so say so.
        self.assertIn("outside the active window", " ".join(finding.limitations))
        self.assertTrue(any(identifier.startswith("history-") for identifier in finding.transaction_ids))
        self.assertEqual(finding.window_start, CUTOFF - timedelta(minutes=60))

    def test_zero_baseline_is_explicitly_unavailable(self):
        result = run([transaction(str(i)) for i in range(20)], "burst", context=coverage())
        status = next(item for item in result.coverage if item.feature_id == "burst")
        self.assertEqual(status.status, "unavailable")
        self.assertIn("zero_historical_baseline", status.reason_codes)

    def test_historical_counts_remain_aligned_with_their_windows(self):
        counts = [7, 1, 2, 3, 4, 5, 6]
        history = [transaction(f"history-{day}-{j}", when=CUTOFF - timedelta(days=day, minutes=10))
                   for day, count in enumerate(counts, 1) for j in range(count)]
        result = run([transaction(str(i)) for i in range(20)], "burst", history=history, context=coverage())
        finding = result.findings[0]
        self.assertEqual(finding.measurements["historical_counts"], counts)
        self.assertEqual(finding.measurements["historical_median_count"], 4)

    def test_a_gap_prevents_claiming_seven_complete_days(self):
        history = [transaction(f"history-{i}", when=CUTOFF - timedelta(days=i, minutes=10))
                   for i in range(1, 8)]
        context = coverage(known_gaps=[{
            "start": (CUTOFF - timedelta(days=2, hours=3)).isoformat(),
            "end": (CUTOFF - timedelta(days=2, hours=2)).isoformat(),
        }])
        result = run([transaction(str(i)) for i in range(20)], "burst", history=history, context=context)
        status = next(item for item in result.coverage if item.feature_id == "burst")
        self.assertEqual(status.status, "unavailable")
        self.assertIn("insufficient_complete_history", status.reason_codes)

    def test_normal_frequency_does_not_trigger_burst(self):
        history = [transaction(f"history-{i}", when=CUTOFF - timedelta(days=i, minutes=10))
                   for i in range(1, 8)]
        self.assertFalse(run([transaction("active")], "burst", history=history, context=coverage()).findings)

    def test_baseline_evidence_counts_toward_the_evidence_budget(self):
        history = [transaction(f"history-{i}", when=CUTOFF - timedelta(days=i, minutes=10))
                   for i in range(1, 8)]
        policy = policy_for("burst", burst={"minimum_count": 4})
        policy["execution"]["max_evidence_transactions"] = 10
        result = run([transaction(str(i)) for i in range(4)], policy=policy,
                     history=history, context=coverage())
        self.assertFalse(result.findings)
        self.assertEqual(next(c for c in result.coverage if c.feature_id == "burst").status, "truncated")

    def test_observed_reactivation_requires_historical_anchor(self):
        rows = [transaction(str(i), minutes=110-i) for i in range(3)]
        history = [transaction("prior", when=CUTOFF - timedelta(days=8))]
        policy = policy_for("dormant_activation", dormant_activation={"minimum_count": 3})
        result = run(rows, policy=policy, history=history, context=coverage())
        self.assertEqual(len(result.findings), 1)
        self.assertIn("prior", result.findings[0].transaction_ids)
        self.assertEqual(result.findings[0].measurements["previous_transaction_id"], "prior")

    def test_first_observation_is_not_dormancy(self):
        rows = [transaction(str(i), minutes=110-i) for i in range(10)]
        result = run(rows, "dormant_activation", context=coverage())
        self.assertFalse(result.findings)
        item = next(c for c in result.coverage if c.feature_id == "dormant_activation")
        self.assertIn("no_prior_observed_activity", item.reason_codes)

    def test_incomplete_gap_and_short_gap_do_not_trigger_dormancy(self):
        rows = [transaction(str(i), minutes=110-i) for i in range(10)]
        for day, context in (
            (4, coverage()),
            (8, coverage(known_gaps=[{
                "start": (CUTOFF - timedelta(days=5)).isoformat(),
                "end": (CUTOFF - timedelta(days=4)).isoformat(),
            }])),
        ):
            with self.subTest(day=day):
                history = [transaction("prior", when=CUTOFF - timedelta(days=day))]
                self.assertFalse(run(rows, "dormant_activation", history=history, context=context).findings)

    def test_future_events_do_not_rewrite_historical_result(self):
        rows = [transaction(str(i), minutes=110-i) for i in range(10)]
        history = [transaction("prior", when=CUTOFF - timedelta(days=8))]
        first = run(rows, "dormant_activation", history=history, context=coverage()).to_dict()
        history.append(transaction("future", minutes=-10))
        self.assertEqual(first, run(rows, "dormant_activation", history=history, context=coverage()).to_dict())
