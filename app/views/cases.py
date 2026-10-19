"""Explicit case actions over immutable evidence attachments and versioned history."""
from datetime import datetime, timezone
from uuid import uuid4
import streamlit as st
from fintrace.cases.service import apply_case_action, TRANSITIONS
from fintrace.storage.case_store import read_cases
from app.components.filters import account_label


def _alerts(model):
    return {x['alert_id']: x for x in model['alerts']}


def render(model, database, refresh):
    st.caption('INVESTIGATION OPERATIONS / CASES')
    st.title('Case workspace')
    st.write('Group review alerts, preserve evidence snapshots, and record explicit analyst actions.')
    st.caption('Current workflow history may postdate the selected analysis cutoff. Case participants are not confirmed suspects.')
    alerts = _alerts(model)
    label = lambda identifier: f"{account_label(alerts[identifier]['subject'])} · {identifier[-12:]}"
    with st.expander('Create a case'):
        with st.form('create_case'):
            title = st.text_input('Case title')
            selected = st.multiselect('Alerts to attach', list(alerts), format_func=label)
            actor = st.text_input('Case creator')
            reason = st.text_area('Creation rationale')
            submitted = st.form_submit_button('Create case')
        if submitted:
            request = st.session_state.setdefault('case_create_request', str(uuid4()))
            try:
                created = apply_case_action(database, None, 'create', actor=actor, at=datetime.now(timezone.utc).isoformat(),
                    reason=reason, expected_version=0, request_id=request,
                    payload={'title': title, 'snapshot_id': model['snapshot']['snapshot_id'], 'alert_ids': selected})
            except Exception as error:
                st.error(str(error))
            else:
                st.session_state.pop('case_create_request', None)
                st.session_state['review_saved'] = f"Created case {created['case_id']}"
                refresh(); st.rerun()
    try:
        catalog = read_cases(database)
    except Exception as error:
        st.error(str(error)); return
    if catalog['truncated']:
        st.warning('First 200 cases shown. Use scripts/manage_cases.py show for an explicit case ID.')
    if not catalog['items']:
        st.info('No cases yet. Create one by explicitly selecting alerts and entering a reviewer and rationale.'); return
    selected = st.selectbox('Case', catalog['items'], format_func=lambda c: f"{c['title']} · {c['state']} · {c['case_id'][-8:]}")
    detail = read_cases(database, selected['case_id']); case = detail['case']
    st.text(f"State: {case['state']} · Version: {case['version']} · Assignee: {case['assignee'] or 'Unassigned'}")
    st.code(case['case_id'], language=None)
    st.subheader('Frozen evidence attachments')
    st.dataframe([{'Snapshot reference': x['snapshot_id'][-12:], 'Cutoff': x['cutoff'], 'Alerts': len(x['alerts']),
                   'Findings': len(x['finding_ids'])} for x in case['evidence_snapshots']], hide_index=True, width='stretch')
    edit_key = 'case_edit_'+case['case_id']
    expected = st.session_state.setdefault(edit_key, case['version'])
    if st.button('Reload case version'):
        st.session_state[edit_key] = case['version']; st.rerun()
    st.caption(f'Action expected version: {expected}. A stale action is rejected; reload before retrying.')
    options = ['note', 'reopen'] if case['state'] == 'closed' else ['note', 'assign', 'attach', 'transition']
    action = st.selectbox('Case action', options)
    with st.form('case_action'):
        actor = st.text_input('Action reviewer'); reason = st.text_area('Action rationale')
        payload = {}
        if action == 'note':
            payload['text'] = st.text_area('Append note or correction')
        elif action == 'assign':
            payload['assignee'] = st.text_input('Assign to')
        elif action == 'attach':
            payload['snapshot_id'] = model['snapshot']['snapshot_id']
            payload['alert_ids'] = st.multiselect('Additional snapshot alerts', list(alerts), format_func=label)
        elif action == 'transition':
            payload['state'] = st.selectbox('New case state', sorted(TRANSITIONS[case['state']]))
            payload['disposition'] = st.text_input('Disposition (required when closing)')
        submitted = st.form_submit_button('Save case action')
    if submitted:
        request_key = edit_key+'_request'
        request = st.session_state.setdefault(request_key, str(uuid4()))
        try:
            apply_case_action(database, case['case_id'], action, actor=actor, at=datetime.now(timezone.utc).isoformat(),
                              reason=reason, expected_version=expected, request_id=request, payload=payload)
        except Exception as error:
            st.error(str(error))
        else:
            st.session_state.pop(edit_key, None); st.session_state.pop(request_key, None)
            st.session_state['review_saved'] = 'Case action saved with an immutable audit event.'
            refresh(); st.rerun()
    st.subheader('Notes and disposition')
    for note in case['notes']:
        st.text(note['text']); st.text(f"{note['actor']} · {note['at']} · version {note['version']}")
    if case['disposition']:
        st.json(case['disposition'])
    with st.expander('Audit history and previous versions'):
        st.dataframe([{'Version': x['version'], 'Action': x['action'], 'Reviewer': x['actor'],
                       'Time': x['at'], 'Previous state': x['previous_state'], 'New state': x['new_state'],
                       'Rationale': x['reason']} for x in detail['events']], hide_index=True, width='stretch')
        version = st.number_input('Historical case version', min_value=1, max_value=case['version'], value=case['version'], step=1)
        st.json(read_cases(database, case['case_id'], version=version)['case'])
