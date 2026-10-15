"""FinTrace local investigation workspace over immutable analysis snapshots."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import streamlit as st
from fintrace.investigations.dashboard import list_snapshots, load_dashboard, load_graph_evidence

st.set_page_config(page_title="FinTrace · Investigation workspace", page_icon="🔎", layout="wide")
st.html(ROOT / "app/style.css")

PROCESSED = Path(os.environ.get("FINTRACE_PROCESSED_ROOT", ROOT / "data/processed"))
DATABASE = Path(os.environ.get("FINTRACE_ALERT_DATABASE", PROCESSED / "alerts.duckdb"))


@st.cache_data(ttl=30, show_spinner=False)
def read_dashboard(database, identifier):
    return load_dashboard(database, identifier)


@st.cache_data(ttl=60, show_spinner="Verifying graph evidence…")
def read_graph(processed_root, model):
    return load_graph_evidence(processed_root, model)


def refresh():
    read_dashboard.clear()
    read_graph.clear()


with st.sidebar:
    st.html('<div class="ft-brand"><span class="ft-mark">FT</span>FinTrace</div>')
    st.caption("INVESTIGATION WORKSPACE")
    st.html('<div class="ft-rule"></div>')
    page = st.radio("Workspace", ["Overview", "Alert review", "Account evidence", "Network explorer"], label_visibility="collapsed", key="navigation")
    st.html('<div class="ft-rule"></div>')
    st.caption("ANALYSIS SNAPSHOT")
    if st.button("Refresh workspace", width="stretch"):
        refresh()
    try:
        catalog = list_snapshots(DATABASE)
    except Exception as error:
        catalog = {"items": [], "truncated": False}
        source_error = str(error)
    else:
        source_error = None
    identifier = st.selectbox("Snapshot", catalog["items"],
                              format_func=lambda item: f"{item['cutoff'][:16].replace('T', ' ')} UTC · {item['id'][-8:]}",
                              disabled=not catalog["items"], key="snapshot_selection")
    if catalog["truncated"]:
        st.warning("Snapshot catalog limited to 200 entries.")
    st.caption("IBM SYNTHETIC DATA")
    st.caption("Deterministic rules · NetworkX · Fixed policy priorities")

if not identifier:
    st.caption("WORKSPACE / GETTING STARTED")
    st.title("An evidence-first workspace.")
    st.write("Connect completed analysis snapshots to review alerts and explore transaction relationships.")
    if source_error:
        st.info(source_error)
    else:
        st.info("The alert store has no imported priority snapshots yet.")
    st.code(".venv/bin/python scripts/manage_alerts.py import \\\n  --rules-run data/processed/rule_runs/RULE_RUN_ID \\\n  --graph-run data/processed/graph_runs/GRAPH_RUN_ID \\\n  --actor local-investigator --at YOUR_TIME_WITH_TIMEZONE", language="bash")
    st.caption("Prepare the dataset and run the rule/graph CLIs first. No data is downloaded or processed automatically by this page.")
    st.stop()

try:
    model = read_dashboard(str(DATABASE), identifier["id"])
except Exception as error:
    st.error(f"The selected snapshot could not be loaded: {error}")
    st.button("Clear cached views", on_click=refresh)
    st.stop()

with st.sidebar:
    st.caption(f"Exclusive cutoff: {model['snapshot']['window']['end']}")
    st.caption(f"Scoring policy: {model['snapshot']['policy']['policy_version']}")
    with st.expander("Snapshot identity"):
        st.code(identifier["id"], language=None)
    st.caption("Cases, report workflows, replay and benchmark evaluation are pending.")

if message := st.session_state.pop("review_saved", None):
    st.success(message)


def get_graph():
    try:
        return read_graph(str(PROCESSED), model)
    except Exception as error:
        st.error(f"Graph evidence is unavailable: {error}")
        return None


if page == "Overview":
    from app.views.overview import render
    render(model)
elif page == "Alert review":
    from app.views.alerts import render
    render(model, DATABASE, refresh)
elif page == "Account evidence":
    from app.views.account import render
    render(model, get_graph)
else:
    from app.views.network import render
    render(model, get_graph)
