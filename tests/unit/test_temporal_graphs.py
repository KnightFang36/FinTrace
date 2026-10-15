"""Temporal graph counterexamples, exact values, budgets and subject roles."""
import copy
import tomllib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from fintrace.contracts import AccountKey, canonical_json
from fintrace.graph import analyze_graph
from fintrace.graph.builder import build_account_summary, build_transaction_graph
from fintrace.graph.temporal_paths import SearchBudget

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = "2022-09-01T03:00:00Z"


def policy(**overrides):
    with (ROOT / "config/graph.toml").open("rb") as handle:
        return tomllib.load(handle) | overrides


def tx(identifier, sender, receiver, minute, *, currency="USD", receiving=None, amount="10.00", bank="1"):
    return {"transaction_id": identifier, "dataset_id": "fixture", "occurred_at": f"2022-09-01T{minute}:00Z",
            "sender_bank_id": bank, "sender_account_id": sender, "receiver_bank_id": "1", "receiver_account_id": receiver,
            "amount_paid": amount, "payment_currency": currency, "amount_received": amount,
            "receiving_currency": receiving or currency}


def run(rows, **overrides):
    return analyze_graph(rows, [], policy(**overrides), CUTOFF, dataset_id="fixture")


def test_parallel_edges_and_exact_large_amount_summaries():
    rows = [tx("a", "A", "B", "00:01", amount="99999999999999999999999999999.99999999"),
            tx("b", "A", "B", "00:02", amount="0.00000001")]
    graph = build_transaction_graph(rows, policy(), CUTOFF)
    assert graph.number_of_edges() == 2
    summary = build_account_summary(graph, "USD")
    edge = summary[AccountKey("1", "A")][AccountKey("1", "B")]
    assert edge["amount_paid"] == Decimal("100000000000000000000000000000")
    assert edge["transaction_ids"] == ["a", "b"]


def test_reverse_order_ties_and_future_do_not_make_paths():
    for second in ("00:01", "00:00", "03:00"):
        result = run([tx("a", "A", "B", "00:01"), tx("b", "B", "C", second)], minimum_hops=2)
        assert not result.findings


def test_path_roles_order_and_circular_evidence():
    rows = [tx("c", "C", "A", "00:03"), tx("a", "A", "B", "00:01"), tx("b", "B", "C", "00:02")]
    result = run(rows)
    cycles = [item for item in result.findings if item.rule_id == "circular_flow"]
    assert len(cycles) == 1
    assert cycles[0].transaction_ids == ("a", "b", "c")
    assert cycles[0].measurements["returning_account"] == AccountKey("1", "A")
    assert cycles[0].subject_roles == ("cycle_participant",) * 3
    path = run(rows[:2] + [tx("d", "B", "D", "00:02"), tx("e", "D", "E", "00:03")])
    chain = next(item for item in path.findings if item.transaction_ids == ("a", "d", "e"))
    assert chain.subject_accounts == (AccountKey("1", "B"), AccountKey("1", "D"))
    assert AccountKey("1", "E") not in chain.subject_accounts


def test_structural_cycle_with_ties_is_not_temporal_cycle():
    result = run([tx("a", "A", "B", "00:01"), tx("b", "B", "A", "00:01")])
    assert not result.findings


def test_currency_changes_and_self_transfers_not_used_as_paths():
    result = run([tx("a", "A", "B", "00:01"), tx("b", "B", "C", "00:02", currency="EUR"),
                  tx("c", "C", "A", "00:03", receiving="EUR"), tx("d", "A", "A", "00:04")], minimum_hops=2)
    assert not result.findings
    assert result.graph.number_of_edges() == 3
    assert result.artifact["excluded_self_transfers"] == 1


def test_input_order_invariance_and_future_cutoff_isolation():
    rows = [tx("a", "A", "B", "00:01"), tx("b", "B", "C", "00:02"), tx("c", "C", "D", "00:03")]
    a = run(rows).to_dict()
    b = run(list(reversed(rows)) + [tx("future", "A", "Z", "03:00")]).to_dict()
    assert canonical_json(a) == canonical_json(b)


def test_bank_identity_does_not_join_distinct_accounts():
    result = run([tx("a", "A", "B", "00:01"), tx("b", "B", "C", "00:02", bank="01")], minimum_hops=2)
    assert not result.findings


def test_expansion_result_and_seed_limits_are_visible():
    rows = [tx("a", "A", "B", "00:01"), tx("b", "B", "C", "00:02"), tx("c", "C", "D", "00:03")]
    result = run(rows, max_expansions=1, minimum_hops=2)
    assert result.artifact["coverage"]["layering"]["status"] == "truncated"
    result = run(rows, max_findings_per_feature=1, minimum_hops=2)
    assert result.artifact["coverage"]["layering"]["status"] == "truncated"
    assert len([item for item in result.findings if item.rule_id == "layering"]) == 1
    result = run(rows, max_seed_accounts=1)
    assert "seed_budget_exhausted" in result.artifact["coverage"]["layering"]["reason_codes"]


def test_runtime_budget_reports_incomplete_work():
    budget = SearchBudget(10, 10, 1)
    budget.deadline = 0
    assert not budget.step()
    assert budget.coverage()["reason_codes"] == ["runtime_budget_exhausted"]


def test_input_limit_fails_rather_than_sampling():
    with pytest.raises(ValueError, match="budget"):
        run([tx("a", "A", "B", "00:01"), tx("b", "B", "C", "00:02")], max_input_transactions=1)
    with pytest.raises(ValueError, match="node budget"):
        run([tx("a", "A", "B", "00:01")], max_nodes=1)


def test_context_size_limits_and_centrality_do_not_create_findings():
    result = run([tx("a", "A", "B", "00:01")], context_max_nodes=1)
    assert result.artifact["context"]["USD"]["metrics"]["status"] == "unavailable"
    assert result.artifact["context"]["USD"]["communities"]["status"] == "unavailable"
    assert not result.findings


def test_repeated_synchronized_group_needs_two_complete_windows():
    rows = [tx(f"{hour}-{account}", account, "HUB", f"0{hour}:10") for hour in (0, 1) for account in ("A", "B", "C")]
    findings = [item for item in run(rows).findings if item.rule_id == "coordinated_group"]
    assert len(findings) == 1
    assert len(findings[0].transaction_ids) == 6
    assert AccountKey("1", "HUB") not in findings[0].subject_accounts
    assert not [item for item in run(rows[:3]).findings if item.rule_id == "coordinated_group"]
    assert not [item for item in run(rows, window_minutes=120).findings if item.rule_id == "coordinated_group"]
    staggered = copy.deepcopy(rows)
    staggered[0]["occurred_at"] = "2022-09-01T00:11:00Z"
    assert not [item for item in run(staggered).findings if item.rule_id == "coordinated_group"]


def test_invalid_policy_labels_and_conflicting_ids_rejected():
    row = tx("a", "A", "B", "00:01")
    for changes in ({"maximum_hops": True}, {"minimum_hops": 5, "maximum_hops": 4}, {"unknown": 1}):
        with pytest.raises(ValueError):
            run([row], **changes)
    with pytest.raises(ValueError, match="label-free"):
        run([row | {"is_laundering": 1}])
    with pytest.raises(ValueError, match="Conflicting"):
        run([row, row | {"amount_paid": "11"}])
    with pytest.raises(ValueError, match="dataset"):
        run([row, tx("b", "B", "C", "00:02") | {"dataset_id": "different"}])


def test_seed_scope_and_empty_graph_are_explicit():
    result = analyze_graph([], [AccountKey("1", "MISSING")], policy(), CUTOFF, dataset_id="empty")
    assert result.artifact["node_count"] == 0
    assert result.artifact["coverage"]["layering"]["missing_seeds"] == [AccountKey("1", "MISSING")]
    with pytest.raises(ValueError, match="seed budget"):
        analyze_graph([], [AccountKey("1", "A"), AccountKey("1", "B")], policy(max_seed_accounts=1), CUTOFF, dataset_id="empty")
