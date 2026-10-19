"""Snapshot overview backed exclusively by service totals."""
import streamlit as st
from app.components.coverage import render_coverage
from app.components.filters import account_label, humanize


def render(model):
    st.caption("INVESTIGATION OPERATIONS / OVERVIEW")
    st.title("Investigation command center")
    st.write("Prioritize alerts, inspect transaction evidence, and track analyst review.")
    summary = model["summary"]
    cols = st.columns(4)
    for col, label, value in zip(cols, ("Accounts for review", "Review alerts", "Evidence findings", "Open / in review"),
                                  (summary["accounts"], summary["alerts"], summary["findings"], summary["open_alerts"])):
        col.metric(label, f"{value:,}")
    left, right = st.columns([1.4, 1])
    with left:
        with st.container(border=True):
            st.subheader("Priority distribution")
            st.bar_chart([{ "Band": humanize(band), "Accounts": count} for band, count in summary["by_band"].items()],
                         x="Band", y="Accounts", color="#38d9c5", sort=False, height=260)
            st.caption("Fixed policy points, capped at 100. Scores are investigation priorities, not probabilities.")
    with right:
        with st.container(border=True):
            st.subheader("Patterns in the queue")
            st.dataframe([{"Evidence family": humanize(name), "Alerts": count} for name, count in summary["by_family"].items()],
                         hide_index=True, width="stretch")
            st.caption("One account may have alerts from several evidence families.")
    st.subheader("Start with these accounts")
    top = sorted(model["priorities"].values(), key=lambda item: (-item["score"], account_label(item["account"])))[:8]
    st.dataframe([{"Bank / account": account_label(item["account"]), "Priority": item["score"], "Band": humanize(item["band"]),
                   "Evidence families": len(item["contributions"])} for item in top], hide_index=True, width="stretch")
    with st.expander("Analysis coverage and limitations"):
        render_coverage(model["snapshot"]["coverage"])
    st.info("IBM synthetic banking data. Findings flag patterns for review; they do not establish criminal intent or confirmed mule status.")
