"""Interactive bounded transaction neighbourhood and selected finding highlight."""
import streamlit as st
from app.components.filters import account_label, humanize
from app.components.network import render_network
from fintrace.investigations.network import get_network_view


def render(model, get_graph):
    st.caption("WORKSPACE / NETWORK EXPLORER")
    st.title("Trace the connections")
    st.write("Explore a bounded neighbourhood or follow a finding's exact transfer references.")
    graph = get_graph()
    if graph is None:
        st.info("No temporal graph snapshot is linked to this analysis. Run scripts/run_graphs.py, then import matching snapshots with scripts/manage_alerts.py.")
        return
    accounts = sorted(model["priorities"].values(), key=lambda item: (-item["score"], account_label(item["account"])))
    if not accounts:
        st.info("No scored accounts are available as investigation seeds.")
        return
    selected = st.selectbox("Seed account", accounts, format_func=lambda item: account_label(item["account"]))
    findings = [None] + [item for item in model["findings"].values() if selected["account"] in item["subject_accounts"]]
    finding = st.selectbox("Highlight finding", findings, format_func=lambda item: "No highlight — neighbourhood only" if item is None else f"{humanize(item['rule_id'])} · {item['finding_id'][:12]}")
    a, b, c = st.columns(3)
    direction = a.selectbox("Direction", ["both", "incoming", "outgoing"], format_func=humanize)
    hops = b.slider("Neighbourhood hops", 1, 3, 1)
    max_nodes = c.slider("Account display limit", 10, 100, 40, step=10)
    view = get_network_view(graph, selected["account"], hops=hops, direction=direction, max_nodes=max_nodes, max_edges=150, finding=finding)
    if view["missing_seed"]:
        st.warning("This account is absent from the selected graph window. Its rule evidence may cover a different interval.")
    if not view["nodes"]:
        return
    render_network(view)
    with st.expander("Displayed transfers — precise amounts and source references"):
        st.dataframe([{ "Transaction ID": edge["id"], "Time": edge["transaction"]["occurred_at"],
                        "Sender": account_label(edge["transaction"]["sender"]), "Receiver": account_label(edge["transaction"]["receiver"]),
                        "Paid": edge["transaction"]["amount_paid"], "Currency": edge["transaction"]["payment_currency"],
                        "Received": edge["transaction"]["amount_received"], "Receiving currency": edge["transaction"]["receiving_currency"],
                        "Highlighted": edge["highlighted"]} for edge in view["edges"]], hide_index=True, width="stretch")
    st.caption(f"Graph run {graph['run_id']} · {graph['window_start']} → {graph['cutoff']} (exclusive)")
