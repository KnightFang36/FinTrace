"""Render an already-bounded network with inline PyVis resources and escaped labels."""
from html import escape
import json
import streamlit as st
from pyvis.network import Network
from fintrace.contracts import content_id


def network_html(view):
    network = Network(height="560px", width="100%", directed=True, bgcolor="#0b1420", font_color="#e8f0fa", cdn_resources="in_line")
    for node in view["nodes"]:
        account = node["account"]
        label = escape(f"{account['bank_id']}:{account['account_id']}")
        network.add_node(node["id"], label=label, title=label, color="#ffbf69" if node["seed"] else "#38d9c5", size=22 if node["seed"] else 14)
    for edge in view["edges"]:
        tx = edge["transaction"]
        title = escape(f"{tx['transaction_id']} | {tx['occurred_at']} | Paid {tx['amount_paid']} {tx['payment_currency']} | Received {tx['amount_received']} {tx['receiving_currency']}")
        network.add_edge(edge["from"], edge["to"], id=content_id(edge["id"]), title=title,
                         color="#ffbf69" if edge["highlighted"] else "#829cb8", width=3 if edge["highlighted"] else 1,
                         arrows="to", smooth={"enabled": True, "type": "dynamic"})
    network.set_options(json.dumps({"layout": {"randomSeed": 42}, "physics": {"stabilization": {"iterations": 100}},
                                   "interaction": {"hover": True, "navigationButtons": True}, "edges": {"arrows": {"to": {"enabled": True}}}}))
    html = network.generate_html()
    # PyVis's base template includes optional Bootstrap CDN references even with inline vis.js.
    import re
    html = re.sub(r'<link[^>]*href="https://[^>]+>', '', html)
    html = re.sub(r'<script[^>]*src="https://[^>]+>\s*</script>', '', html)
    html = html.replace("</head>", """<style>
      html, body, .card { margin: 0; background: #0b1420; color: #e8f0fa; }
      #mynetwork { border: 1px solid #2a3e55 !important; border-radius: 6px; }
      div.vis-tooltip { background: #17283b; color: #e8f0fa; border: 1px solid #62809f;
                        padding: 10px; font: 13px/1.5 sans-serif; max-width: 500px; overflow-wrap: anywhere; }
    </style></head>""")
    return html


def render_network(view):
    st.caption(f"{len(view['nodes'])} / {view['source_nodes']:,} accounts · {len(view['edges'])} / {view['source_edges']:,} transfers · orange edges = selected evidence")
    if view["partial"]:
        st.info("Bounded view of the selected graph window. Accounts and edges outside this view remain in the underlying evidence.")
    if not view["evidence_complete"]:
        st.warning("Some selected evidence is outside this graph or exceeds the display budget. Use the evidence transaction list for the complete references.")
    st.iframe(network_html(view), height=580, alt="Interactive directed transaction network")
    st.caption("Drag to explore · scroll to zoom · hover for transaction details. Structural links alone do not establish a temporal money flow.")
