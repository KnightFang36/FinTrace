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


def alerted_model(accounts):
    return {'priorities': {content_id(account): {'account': account, 'score': score}
                           for account, score, _ in accounts},
            'alerts': [{'subject': account, 'state': state} for account, _, state in accounts]}


def test_combined_network_ranks_unique_active_alert_subjects_and_reserves_top_ten():
    from fintrace.investigations.network import get_alerted_network_view
    accounts = [({'bank_id': '01', 'account_id': f'A{i:02}'}, 100-i, 'open') for i in range(12)]
    model = alerted_model(accounts)
    model['alerts'].append(dict(model['alerts'][0]))  # Two alerts do not count as two accounts.
    model['priorities'][content_id({'bank_id': '01', 'account_id': 'unalerted'})] = {
        'account': {'bank_id': '01', 'account_id': 'unalerted'}, 'score': 100}
    graph = {'edges': [edge(str(i), f'A{i:02}', 'hub') for i in range(12)]}
    view = get_alerted_network_view(graph, model, max_nodes=10, max_edges=5)
    assert len(view['nodes']) == 10 and all(item['seed'] for item in view['nodes'])
    assert [item['account']['account_id'] for item in view['ranked_accounts']] == [f'A{i:02}' for i in range(10)]
    assert view['ranked_accounts'][0]['active_alerts'] == 2
    assert not view['edges']  # The omitted hub is not replaced with invented direct links.
    assert view['partial']


def test_combined_network_missing_window_accounts_are_explicit_and_bank_keys_remain_distinct():
    from fintrace.investigations.network import get_alerted_network_view
    accounts = [({'bank_id': bank, 'account_id': 'A'}, 25, state)
                for bank, state in [('1', 'open'), ('01', 'in_review'), ('02', 'closed')]]
    view = get_alerted_network_view({'edges': [edge('t', 'A', 'B')]}, alerted_model(accounts))
    assert [item['account']['bank_id'] for item in view['ranked_accounts']] == ['01', '1']
    assert view['missing_seeds'] == [{'bank_id': '1', 'account_id': 'A'}]
    assert len([node for node in view['nodes'] if node['seed']]) == 2
    assert 'No transfers in the selected graph window' in network_html(view)
    assert 'Review priority 25/100' in network_html(view)
    assert all(row['transaction']['sender']['bank_id'] == '01' for row in view['edges'])


def test_combined_network_balances_neighbours_and_edges_and_is_input_order_independent():
    from fintrace.investigations.network import get_alerted_network_view
    accounts = [({'bank_id': '01', 'account_id': name}, score, 'open') for name, score in [('A', 50), ('B', 25)]]
    graph = {'edges': [edge(f'a{i}', 'A', f'X{i}') for i in range(20)] + [edge('b', 'B', 'Y')]}
    model = alerted_model(accounts)
    view = get_alerted_network_view(graph, model, max_nodes=4, max_edges=2, direction='outgoing')
    assert len(view['nodes']) == 4 and len(view['edges']) == 2
    assert 'Y' in {item['account']['account_id'] for item in view['nodes']}
    assert 'b' in {item['id'] for item in view['edges']}
    assert view == get_alerted_network_view({'edges': list(reversed(graph['edges']))}, model,
                                           max_nodes=4, max_edges=2, direction='outgoing')
    assert not get_alerted_network_view(graph, {'priorities': {}, 'alerts': []})['nodes']


def test_graph_layout_positions_are_stable_across_input_order():
    import json
    import re
    graph = {'edges': [edge('a', 'A', 'B'), edge('b', 'B', 'C')]}
    view = get_network_view(graph, {'bank_id': '01', 'account_id': 'A'}, hops=2)
    def positions(html):
        match = re.search(r'nodes = new vis.DataSet\((\[.*?\])\);', html)
        assert match
        return {item['id']: (item['x'], item['y']) for item in json.loads(match.group(1))}
    first = positions(network_html(view))
    reordered = {**view, 'nodes': list(reversed(view['nodes'])), 'edges': list(reversed(view['edges']))}
    assert first == positions(network_html(reordered))
    assert len(set(first.values())) == len(view['nodes'])


def test_six_hop_display_stops_at_depth_and_preserves_node_and_edge_budgets():
    import pytest
    graph = {'edges': [edge(str(i), str(i), str(i+1)) for i in range(8)]}
    seed = {'bank_id': '01', 'account_id': '0'}
    view = get_network_view(graph, seed, direction='outgoing')
    assert view['hops'] == 6 and view['limits']['max_nodes'] == 100
    assert {node['account']['account_id'] for node in view['nodes']} == {str(i) for i in range(7)}
    assert {item['id'] for item in view['edges']} == {str(i) for i in range(6)}
    bounded = get_network_view(graph, seed, hops=6, direction='outgoing', max_nodes=4, max_edges=2)
    assert len(bounded['nodes']) == 4 and len(bounded['edges']) == 2 and bounded['partial']
    with pytest.raises(ValueError, match='expansion'):
        get_network_view(graph, seed, hops=7)


def test_layout_gives_nodes_clearance_and_edges_real_length_in_dense_groups():
    import math
    from app.components.network import network_positions
    graph = {'edges': [edge(f'a{i}', 'A', f'X{i}') for i in range(24)] +
                     [edge(f'b{i}', 'B', f'Y{i}') for i in range(12)]}
    model = alerted_model([({'bank_id': '01', 'account_id': name}, 25, 'open') for name in ('A','B')])
    from fintrace.investigations.network import get_alerted_network_view
    view = get_alerted_network_view(graph, model)
    positions = network_positions(view)
    keys = sorted(positions)
    assert all(math.dist(positions[left], positions[right]) >= 179.99
               for index,left in enumerate(keys) for right in keys[index+1:])
    assert all(math.dist(positions[item['from']], positions[item['to']]) >= 279.99
               for item in view['edges'])
    assert len(view['nodes']) == 38 and len(view['edges']) == 36
