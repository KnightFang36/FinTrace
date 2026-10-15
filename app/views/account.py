"""Evidence-scoped account dossier and graph-window transfer timeline."""
import streamlit as st
from app.components.filters import account_label, humanize
from app.views.alerts import render_finding
from fintrace.investigations.account import get_account_dossier


def render(model, get_graph):
    st.caption("WORKSPACE / ACCOUNT EVIDENCE")
    st.title("An account, in context")
    priorities = sorted(model["priorities"].values(), key=lambda item: (-item["score"], account_label(item["account"])))
    if not priorities:
        st.info("This snapshot has no scored accounts.")
        return
    selected = st.selectbox("Bank / account", priorities, format_func=lambda item: f"{account_label(item['account'])} · {item['score']}/100")
    dossier = get_account_dossier(selected["account"], model)
    cols = st.columns(3)
    cols[0].metric("Priority", f"{selected['score']} / 100")
    cols[1].metric("Subject findings", len(dossier["findings"]))
    cols[2].metric("Linked alerts", len(dossier["alerts"]))
    st.caption(dossier["profile_status"])
    evidence, transfers = st.tabs(["Findings & contributions", "Observed transfers"])
    with evidence:
        st.dataframe([{"Family": humanize(item["family_id"]), "Points": item["applied_weight"],
                       "Finding references": len(item["eligible_finding_ids"])} for item in selected["contributions"]], hide_index=True, width="stretch")
        for finding in dossier["findings"]:
            with st.expander(f"{humanize(finding['rule_id'])} · {finding['finding_id'][:12]}"):
                render_finding(finding)
    with transfers:
        if st.button("Load graph-window transfers", key="load_account_transfers"):
            st.session_state["transfers_for"] = account_label(selected["account"])
        if st.session_state.get("transfers_for") == account_label(selected["account"]):
            graph = get_graph()
            if graph is None:
                st.info("No graph snapshot is linked. Rule findings above remain available; transfer history is not loaded from raw data.")
            else:
                dossier = get_account_dossier(selected["account"], model, graph)
                st.caption(dossier["transaction_scope"])
                st.dataframe(dossier["currency_totals"], hide_index=True, width="stretch")
                rows = dossier["transactions"]
                st.caption(f"Showing {min(len(rows), 500)} of {len(rows)} observed graph-window transfers. Amounts remain decimal text and currencies stay separate.")
                st.dataframe([{ "Time": row["occurred_at"], "Sender": account_label(row["sender"]), "Receiver": account_label(row["receiver"]),
                                "Paid": row["amount_paid"], "Payment currency": row["payment_currency"], "Received": row["amount_received"],
                                "Receiving currency": row["receiving_currency"], "Transaction ID": row["transaction_id"]} for row in rows[:500]],
                             hide_index=True, width="stretch")
        else:
            st.caption("Load the linked graph window to inspect observed transfers. This does not reconstruct balances or complete account history.")
