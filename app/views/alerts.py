"""Filter review incidents, inspect evidence, and submit explicit audited actions."""
from datetime import datetime, timezone
import streamlit as st
from app.components.filters import account_label, humanize
from fintrace.investigations.dashboard import filter_alerts, get_audit
from fintrace.storage.alert_store import AlertStore


def render_finding(finding):
    st.write(finding["explanation"])
    st.caption(f"{finding['rule_id']} · {finding['rule_version']} · {finding['window_start']} → {finding['window_end']} (exclusive)")
    st.code("\n".join(finding["transaction_ids"]), language=None)
    left, right = st.columns(2)
    with left:
        st.caption("Observed measurements")
        st.json(finding["measurements"], expanded=False)
    with right:
        st.caption("Policy thresholds")
        st.json(finding["thresholds"], expanded=False)
    for limitation in finding["limitations"]:
        st.caption(limitation)


def render(model, database, refresh):
    st.caption("WORKSPACE / ALERT REVIEW")
    st.title("The review queue")
    st.write("Prioritize a pattern. Inspect the source evidence. Record your review.")
    query = st.text_input("Search bank, account or alert ID", placeholder="e.g. 001 : 800042CB0", key="alert_query")
    a, b, c, d = st.columns(4)
    states = a.multiselect("Workflow status", ["open", "in_review", "escalated", "closed"], format_func=humanize)
    families = b.multiselect("Evidence family", sorted({item["family_id"] for item in model["alerts"]}), format_func=humanize)
    bands = c.multiselect("Priority band", ["low", "medium", "high", "critical"], format_func=humanize)
    currencies = d.multiselect("Evidence currency", sorted({currency for item in model["alerts"] for currency in item["currencies"]}))
    alerts = filter_alerts(model, query=query.replace(" : ", ":"), states=states, families=families, bands=bands, currencies=currencies)
    st.caption(f"{len(alerts)} of {len(model['alerts'])} incidents · evidence and scores from selected snapshot · workflow status is current")
    if not alerts:
        st.info("No alerts match these filters. Clear a filter or choose another analysis snapshot.")
        return
    st.dataframe([{"Account": account_label(item["subject"]), "Priority": item["score"], "Band": humanize(item["band"]),
                   "Family": humanize(item["family_id"]), "Status": humanize(item["state"]), "Transfers": len(item["transaction_ids"]),
                   "Alert ID": item["alert_id"]} for item in alerts], hide_index=True, width="stretch", height=310)
    selected = st.selectbox("Inspect an alert", alerts, format_func=lambda item: f"{account_label(item['subject'])} · {humanize(item['family_id'])} · {item['alert_id'][-8:]}", key="selected_alert")
    evidence_tab, score_tab, review_tab = st.tabs(["Evidence", "Priority ledger", "Review & audit"])
    with evidence_tab:
        for identifier in selected["finding_ids"]:
            finding = model["findings"][identifier]
            with st.expander(f"{humanize(finding['rule_id'])} · {len(finding['transaction_ids'])} transaction references", expanded=len(selected["finding_ids"]) == 1):
                render_finding(finding)
    with score_tab:
        priority = next(item for item in model["priorities"].values() if item["priority_id"] == selected["priority_id"])
        st.metric("Investigation priority", f"{priority['score']} / 100", help="Fixed weights, not a probability")
        st.caption(f"{priority['scoring_policy_version']} · {priority['scoring_policy_hash']}")
        st.dataframe([{"Family": humanize(item["family_id"]), "Points": item["applied_weight"],
                       "Eligible findings": len(item["eligible_finding_ids"]), "Suppressed correlations": len(item["suppressed_finding_ids"])}
                      for item in priority["contributions"]], hide_index=True, width="stretch")
        with st.expander("Full contribution references"):
            st.json(priority["contributions"])
    with review_tab:
        st.caption("Current workflow history may postdate the analysis cutoff. Saving appends one audited transition.")
        options = {"open": ["in_review"], "in_review": ["escalated", "closed"], "escalated": ["in_review", "closed"], "closed": ["open"]}[selected["state"]]
        with st.form(f"review_{selected['alert_id']}_{selected['version']}"):
            st.write(f"Current status: **{humanize(selected['state'])}** · version {selected['version']}")
            action = st.selectbox("Next status", options, format_func=humanize)
            actor = st.text_input("Reviewer", placeholder="Your investigator identifier")
            reason = st.text_area("Review reason", placeholder="Explain the evidence and your decision")
            reopen = st.checkbox("Explicitly reopen this closed alert") if selected["state"] == "closed" else False
            submitted = st.form_submit_button("Save audited review", type="primary")
        if submitted:
            if not actor.strip() or not reason.strip():
                st.error("Enter a reviewer and review reason before saving.")
            elif selected["state"] == "closed" and not reopen:
                st.error("Confirm the explicit reopen action before saving.")
            else:
                try:
                    with AlertStore(database) as store:
                        store.transition(selected["alert_id"], action, actor=actor.strip(), at=datetime.now(timezone.utc),
                                         reason=reason.strip(), expected_version=selected["version"], reopen=reopen)
                    refresh()
                    st.session_state["review_saved"] = "Review saved with an append-only audit event."
                    st.rerun()
                except Exception as error:
                    st.error(f"Review could not be saved. Refresh before retrying. {error}")
        audit = get_audit(database, selected["alert_id"])
        st.dataframe([{ "Version": item["version"], "When": item["timestamp"], "Actor": item["actor"],
                        "Action": humanize(item["action"]), "State": item["new_state"], "Reason": item["reason"]}
                      for item in audit["events"]], hide_index=True, width="stretch")
        if audit["truncated"]:
            st.warning("Only the first 1,000 audit events are shown.")
