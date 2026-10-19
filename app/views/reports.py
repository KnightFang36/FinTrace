"""Explicit local exports of verified snapshot evidence and immutable case versions."""
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from fintrace.reporting.export import export_evidence, report_archive
from fintrace.storage.case_store import read_cases
from app.components.filters import account_label, humanize


def render(model, database, processed_root, export_root):
    st.caption('INVESTIGATION OPERATIONS / REPORTS')
    st.title('Evidence reports')
    st.write('Generate local JSON, CSV, HTML and bounded PNG artifacts with a checksum manifest.')
    st.caption('Internal investigation use. No reports are transmitted or regulatory submissions filed. JSON preserves exact source strings; CSV formula prefixes are neutralized.')
    scope = st.radio('Report scope', ['Selected analysis snapshot', 'Case version'])
    arguments = {}
    if scope == 'Case version':
        catalog = read_cases(database)
        if not catalog['items']:
            st.info('Create a case before exporting a case version. Snapshot exports are available above.'); return
        case = st.selectbox('Report case', catalog['items'], format_func=lambda x: x['title']+' · '+x['case_id'][-8:])
        version = st.number_input('Report case version', min_value=1, max_value=case['version'], value=case['version'])
        arguments = {'case_id': case['case_id'], 'case_version': int(version)}
    else:
        available = {x['alert_id']: x for x in model['alerts']}
        selected = st.multiselect('Report alerts (empty selects all snapshot alerts)', list(available),
            format_func=lambda key: f"{account_label(available[key]['subject'])} · {humanize(available[key]['family_id'])} · priority {available[key]['score']}")
        arguments = {'snapshot_id': model['snapshot']['snapshot_id'], 'alert_ids': selected}
    formats = st.multiselect('Export formats', ['json', 'csv', 'html', 'png'], default=['json', 'csv', 'html', 'png'])
    st.caption('Every completed report includes authoritative evidence.json plus manifest.json. Large scopes fail visibly instead of dropping evidence.')
    if st.button('Generate evidence report'):
        try:
            with st.spinner('Verifying source evidence and generating report…'):
                result = export_evidence(database, processed_root, export_root, at=datetime.now(timezone.utc).isoformat(), formats=formats, **arguments)
            st.session_state['completed_report_directory'] = result['output_directory']
        except Exception as error:
            st.error(str(error))
    if directory := st.session_state.get('completed_report_directory'):
        try:
            data = report_archive(directory)
        except Exception as error:
            st.error(str(error)); return
        st.success('Completed report is ready. Its source scope is frozen independently of current filters.')
        st.code(str(directory), language=None)
        st.download_button('Download verified report ZIP', data, file_name=Path(directory).name+'.zip', mime='application/zip')
