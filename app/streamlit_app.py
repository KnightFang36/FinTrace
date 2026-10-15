"""Runnable scaffold status screen; investigation features are pending."""

import streamlit as st

st.set_page_config(page_title="FinTrace", page_icon="🔎", layout="wide")
st.title("FinTrace")
st.caption("IBM synthetic AML benchmark · Rule-based and temporal graph analysis")
st.info("Repository scaffold ready. Detection and investigation features are not implemented yet.")
st.write(
    "The planned application includes an alert queue, account and network "
    "investigations, cases, evidence exports, and benchmark evaluation."
)
st.write("See README.md and docs/features/ for the agreed feature contracts.")
