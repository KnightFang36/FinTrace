"""Present service coverage without treating missing analysis as zero findings."""
import streamlit as st


def render_coverage(coverage):
    rows = []
    for service, value in coverage.items():
        features = value.get("features", {})
        if isinstance(features, list):
            features = {item["feature_id"]: item for item in features}
        if not features:
            rows.append({"Service": service.replace("_", " "), "Feature": "Service availability",
                         "Status": value.get("status", "unknown"), "Reason": value.get("reason", "")})
        for name, feature in features.items():
            rows.append({"Service": service.replace("_", " "), "Feature": name.replace("_", " "),
                         "Status": feature["status"], "Reason": ", ".join(feature.get("reason_codes", []))})
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Unavailable, disabled and partial analysis is not a clean-account determination. Graph coverage is reported separately from standalone rule coverage.")
