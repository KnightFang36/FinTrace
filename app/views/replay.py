"""Explicit bounded replay steps; historical alerts stay in an isolated store."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import streamlit as st
from fintrace.contracts import utc_instant
from fintrace.replay.engine import list_replays, replay_transactions
from fintrace.investigations.dashboard import load_dashboard


def render(model, processed_root, repository_root):
    st.caption('INVESTIGATION OPERATIONS / REPLAY')
    st.title('Historical replay')
    st.write('Run the same deterministic services at ordered exclusive cutoffs, with durable checkpoints.')
    st.info('Replay alerts are stored separately and do not change the current investigation queue. Equal timestamps stay together. Changed inputs or policies invalidate resume.')
    root = Path(processed_root)/'replays'; repository_root = Path(repository_root)
    datasets = sorted({x['dataset_id'] for x in model['priorities'].values()})
    if not datasets:
        st.info('This snapshot has no dataset-bearing priorities. Use scripts/run_replay.py with an explicit completed detection artifact.'); return
    with st.expander('Start a replay'):
        with st.form('start_replay'):
            dataset = st.selectbox('Replay dataset', datasets)
            cutoff = utc_instant(model['snapshot']['window']['end'])
            start = st.text_input('First exclusive cutoff', cutoff.isoformat())
            end = st.text_input('Final exclusive cutoff', (cutoff+timedelta(hours=1)).isoformat())
            step = st.number_input('Cutoff step (minutes)', min_value=1, max_value=1440, value=30)
            actor = st.text_input('Replay operator')
            include_graph = st.checkbox('Include temporal graph analysis', value=True)
            submitted = st.form_submit_button('Start replay and process first cutoff')
        if submitted:
            try:
                with st.spinner('Processing one replay cutoff…'):
                    replay_transactions(Path(processed_root)/'datasets'/dataset/'transactions.parquet',
                        repository_root/'config/rules.toml', repository_root/'config/scoring.toml', repository_root/'config/alerts.toml',
                        root, start=start, end=end, step_minutes=int(step), actor=actor, at=datetime.now(timezone.utc).isoformat(),
                        graph_policy=repository_root/'config/graph.toml' if include_graph else None, max_steps=1)
            except Exception as error:
                st.error(str(error))
            else:
                st.session_state['review_saved'] = 'Replay cutoff committed. Continue from its durable checkpoint below.'; st.rerun()
    try:
        catalog = list_replays(root)
    except Exception as error:
        st.error(str(error)); return
    if not catalog['items']:
        st.info('No replay runs yet. Starting one requires an explicit operator and cutoff range.'); return
    state = st.selectbox('Replay run', catalog['items'], format_func=lambda x: f"{x['replay_id'][-10:]} · {x['status']} · {len(x['steps'])}/{x['total_cutoffs']} cutoffs")
    st.progress(len(state['steps'])/state['total_cutoffs'])
    st.caption(f"Watermark: {state['watermark'] or 'not advanced'} · Source records available: {state['seen_records']:,}")
    st.dataframe([{'Exclusive cutoff': x['cutoff'], 'Findings': x['finding_count'],
                   'Accounts': x['scored_accounts'], 'Stored alerts': x['persisted_alerts'],
                   'Newly available records': x['new_event_records'], 'Elapsed seconds': x['elapsed_seconds']}
                  for x in state['steps']], hide_index=True, width='stretch')
    st.caption('Elapsed seconds measure this local execution, not live banking latency. Detection windows and graph limits still apply.')
    if state['status'] != 'completed' and st.button('Process next replay cutoff'):
        policies = state['policy_paths']; identity = state['identity']
        try:
            # Only operator-selected repository policies and this workspace's dataset are accepted in the UI.
            dataset_path = Path(processed_root)/'datasets'/identity['dataset_id']/'transactions.parquet'
            with st.spinner('Resuming one replay cutoff…'):
                replay_transactions(dataset_path, repository_root/'config/rules.toml', repository_root/'config/scoring.toml',
                    repository_root/'config/alerts.toml', root, start=identity['start'], end=identity['end'],
                    step_minutes=identity['step_minutes'], actor=state['actor'], at=state['audit_at'],
                    graph_policy=repository_root/'config/graph.toml' if policies['graph'] else None,
                    checkpoint=root/state['replay_id']/'checkpoint.json', max_steps=1)
        except Exception as error:
            st.error(str(error))
        else:
            st.session_state['review_saved'] = 'Replay resumed without duplicating committed alerts.'; st.rerun()
    if state['steps']:
        step = st.selectbox('Inspect replay cutoff', state['steps'], format_func=lambda x: x['cutoff'])
        try:
            replay_model = load_dashboard(root/state['replay_id']/'alerts.duckdb', step['priority_snapshot_id'])
            columns = st.columns(4)
            for column, label, key in zip(columns, ['Accounts for review', 'Review alerts', 'Evidence findings', 'Open / in review'],
                                          ['accounts', 'alerts', 'findings', 'open_alerts']):
                column.metric(label, f"{replay_model['summary'][key]:,}")
            with st.expander('Replay analysis coverage and limitations'):
                st.json(replay_model['snapshot']['coverage'])
            st.dataframe([{'Bank': x['subject']['bank_id'], 'Account': x['subject']['account_id'],
                           'Family': x['family_id'], 'Priority': x['score'], 'Band': x['band'],
                           'State': x['state']} for x in replay_model['alerts']], hide_index=True, width='stretch')
            with st.expander('Replay source and run identifiers'):
                st.json({'identity': state['identity'], 'step': step, 'last_event_ordering_key': state['last_event_ordering_key']})
        except Exception as error:
            st.error(str(error))
