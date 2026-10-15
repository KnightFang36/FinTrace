"""Bounded network evidence, source strings, and exact currency totals."""
from fintrace.contracts import content_id
from fintrace.investigations.account import get_account_dossier
from fintrace.investigations.network import get_network_view
from app.components.network import network_html


def edge(identifier, sender, receiver, currency="USD", amount="10.00"):
    return {"transaction_id": identifier, "sender": {"bank_id": "01", "account_id": sender},
            "receiver": {"bank_id": "01", "account_id": receiver}, "occurred_at": "2022-09-01T00:00:00+00:00",
            "amount_paid": amount, "payment_currency": currency, "amount_received": amount, "receiving_currency": currency}


def test_graph_keeps_parallel_edges_and_highlights_exact_evidence():
    graph = {"edges": [edge("a", "A", "B"), edge("b", "A", "B"), edge("c", "B", "C")]}
    view = get_network_view(graph, {"bank_id": "01", "account_id": "A"}, finding={"transaction_ids": ["a", "c"]})
    assert len(view["edges"]) == 3
    assert {row["id"] for row in view["edges"] if row["highlighted"]} == {"a", "c"}
    assert view["evidence_complete"]


def test_node_edge_caps_and_missing_seed_are_explicit():
    graph = {"edges": [edge(str(i), "A", str(i)) for i in range(20)]}
    view = get_network_view(graph, {"bank_id": "01", "account_id": "A"}, max_nodes=5, max_edges=2)
    assert len(view["nodes"]) == 5 and len(view["edges"]) == 2 and view["partial"]
    missing = get_network_view(graph, {"bank_id": "1", "account_id": "A"})
    assert missing["missing_seed"] and not missing["nodes"]
    partial = get_network_view(graph, {"bank_id": "01", "account_id": "A"}, max_nodes=1, finding={"transaction_ids": ["0"]})
    assert not partial["evidence_complete"]


def test_incoming_outgoing_neighbour_expansion():
    graph = {"edges": [edge("in", "B", "A"), edge("out", "A", "C")]}
    incoming = get_network_view(graph, {"bank_id": "01", "account_id": "A"}, direction="incoming")
    outgoing = get_network_view(graph, {"bank_id": "01", "account_id": "A"}, direction="outgoing")
    assert {row["account"]["account_id"] for row in incoming["nodes"]} == {"A", "B"}
    assert {row["account"]["account_id"] for row in outgoing["nodes"]} == {"A", "C"}


def test_money_totals_remain_exact_and_currencies_separate():
    account = {"bank_id": "01", "account_id": "A"}
    model = {"priorities": {content_id(account): {"score": 25}}, "findings": {}, "alerts": []}
    graph = {"edges": [edge("a", "A", "B", amount="99999999999999999999999999999.99999999"),
                        edge("b", "A", "B", amount="0.00000001"), edge("c", "B", "A", "EUR", "4.00")]}
    dossier = get_account_dossier(account, model, graph)
    totals = {row["currency"]: row for row in dossier["currency_totals"]}
    assert totals["USD"]["paid"] == "100000000000000000000000000000.00000000"
    assert totals["EUR"]["received"] == "4.00"
    assert get_account_dossier({"bank_id": "1", "account_id": "A"}, model, graph) is None


def test_embedded_graph_escapes_external_labels_and_has_no_remote_script_sources():
    malicious = '</script><script>alert("unsafe")</script>'
    graph = {"edges": [edge(malicious, malicious, "B")]}
    view = get_network_view(graph, {"bank_id": "01", "account_id": malicious})
    html = network_html(view)
    assert malicious not in html
    assert 'src="https://' not in html and 'href="https://' not in html
    assert "vis.Network" in html
