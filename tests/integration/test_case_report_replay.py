"""Synthetic end-to-end case audit, verified exports and checkpoint replay."""
import csv
import json
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch

import pytest

from fintrace.alerts.runner import import_analysis
from fintrace.cases.service import apply_case_action
from fintrace.contracts import content_id
from fintrace.ingestion.ibm import ingest_ibm
from fintrace.ingestion.manifest import IBM_HEADER, create_manifest, write_manifest
from fintrace.investigations.dashboard import load_dashboard
from fintrace.replay.engine import read_checkpoint, replay_transactions
from fintrace.reporting.export import export_evidence, verify_report, report_archive
from fintrace.rules.runner import run_rule_snapshot
from fintrace.storage.case_store import read_cases

ROOT = Path(__file__).resolve().parents[2]
AT = '2026-10-20T00:00:00Z'
CUTOFF = '2022-09-01T01:00:00Z'


@pytest.fixture
def prepared(tmp_path):
    raw = tmp_path/'raw'; raw.mkdir()
    source = raw/'source.csv'
    rows = [
        ['2022/09/01 00:05', '=1', 'S1', '001', 'A', '10.00', 'USD', '10.00', 'USD', 'ACH', '1'],
        ['2022/09/01 00:10', '=1', 'S2', '001', 'A', '10.00', 'USD', '10.00', 'USD', 'ACH', '0'],
        ['2022/09/01 00:15', '=1', 'S3', '001', 'A', '10.00', 'USD', '10.00', 'USD', 'ACH', '0'],
        ['2022/09/01 00:20', '001', 'A', '002', 'B', '29.00', 'USD', '29.00', 'USD', 'ACH', '0'],
        ['2022/09/01 00:25', '001', 'A', '002', 'B', '1.25', 'EUR', '1.25', 'EUR', 'ACH', '0'],
        ['2022/09/01 00:30', '003', 'X', '001', 'A', '2.00', 'EUR', '2.00', 'EUR', 'ACH', '0'],
        ['2022/09/01 00:31', '003', 'Y', '001', 'A', '3.00', 'EUR', '3.00', 'EUR', 'ACH', '0'],
        ['2022/09/01 01:00', '=1', 'S4', '001', 'A', '10.00', 'USD', '10.00', 'USD', 'ACH', '1'],
        ['2022/09/01 01:00', '001', 'A', '004', 'C', '10.00', 'USD', '10.00', 'USD', 'ACH', '0'],
        ['2022/09/01 01:05', '001', 'A', '004', 'D', '10.00', 'USD', '10.00', 'USD', 'ACH', '1'],
    ]
    with source.open('w', newline='') as handle:
        writer = csv.writer(handle); writer.writerow(IBM_HEADER); writer.writerows(rows)
    manifest = create_manifest(source, raw, variant='HI-Medium', acquired_at=None,
        timezone_policy='UTC', timestamp_precision='minute', source_terms='Generated test fixture')
    manifest_path = write_manifest(manifest, raw/'manifest.json', raw)
    processed = tmp_path/'processed'; ingest_ibm(manifest_path, raw, processed)
    transactions = processed/'datasets'/manifest['dataset_id']/'transactions.parquet'
    policy = tmp_path/'rules.toml'
    policy.write_text((ROOT/'config/rules.toml').read_text().replace('minimum_distinct_senders = 8', 'minimum_distinct_senders = 2'))
    rules = run_rule_snapshot(transactions, policy, CUTOFF, processed/'rule_runs')
    database = processed/'alerts.duckdb'
    imported = import_analysis(rules['output_directory'], None, ROOT/'config/scoring.toml', ROOT/'config/alerts.toml', database, actor='fixture', at=AT)
    model = load_dashboard(database, imported['priority_snapshot_id'])
    assert model['alerts']
    return {'root': tmp_path, 'processed': processed, 'database': database, 'model': model,
            'transactions': transactions, 'policy': policy, 'dataset_id': manifest['dataset_id']}


def action(fixture, case, verb, payload, request, *, version=None):
    return apply_case_action(fixture['database'], case['case_id'] if case else None, verb,
        actor='analyst', at=AT, reason='Synthetic review rationale', expected_version=version if version is not None else (case['version'] if case else 0),
        request_id=request, payload=payload)


def create(fixture):
    return action(fixture, None, 'create', {'title': '<script>fixture</script>',
        'snapshot_id': fixture['model']['snapshot']['snapshot_id'],
        'alert_ids': [x['alert_id'] for x in fixture['model']['alerts']]}, 'create')


def test_case_versions_notes_close_reopen_idempotency_and_stale_rollback(prepared):
    case = create(prepared)
    assert create(prepared) == case
    assert case['version'] == 1
    original = case
    case = action(prepared, case, 'note', {'text': 'First note: evidence warrants review.'}, 'note')
    with pytest.raises(ValueError, match='Stale'):
        action(prepared, original, 'assign', {'assignee': 'other'}, 'stale')
    case = action(prepared, case, 'assign', {'assignee': 'reviewer-2'}, 'assign')
    case = action(prepared, case, 'transition', {'state': 'investigating'}, 'investigate')
    case = action(prepared, case, 'transition', {'state': 'closed', 'disposition': 'No further action on this fixture'}, 'close')
    closed_version = case['version']
    with pytest.raises(ValueError, match='reopen'):
        action(prepared, case, 'assign', {'assignee': 'other'}, 'closed-assign')
    case = action(prepared, case, 'note', {'text': 'Correction appended while retaining closure.'}, 'closed-note')
    assert case['state'] == 'closed'
    case = action(prepared, case, 'reopen', {}, 'reopen')
    assert case['state'] == 'investigating' and case['assignee'] == 'reviewer-2'
    assert case['notes'][0]['text'].startswith('First note')
    history = read_cases(prepared['database'], case['case_id'])
    assert len(history['events']) == 7
    assert read_cases(prepared['database'], case['case_id'], version=closed_version)['case']['state'] == 'closed'
    assert read_cases(prepared['database'], case['case_id'], version=1)['case'] == original
    with pytest.raises(ValueError, match='Request ID'):
        action(prepared, case, 'note', {'text': 'Different request'}, 'reopen')
    assert len(read_cases(prepared['database'], case['case_id'])['events']) == 7


def test_case_rejects_unknown_alert_and_empty_actor_without_partial_case(prepared):
    payload = {'title': 'bad', 'snapshot_id': prepared['model']['snapshot']['snapshot_id'], 'alert_ids': ['unknown']}
    with pytest.raises(ValueError, match='Unknown alert'):
        action(prepared, None, 'create', payload, 'bad')
    assert read_cases(prepared['database'])['items'] == []
    with pytest.raises(ValueError, match='actor'):
        apply_case_action(prepared['database'], None, 'create', actor='', at=AT, reason='test', expected_version=0, request_id='x', payload=payload)
    missing = prepared['root']/'not-created.duckdb'
    assert read_cases(missing)['items'] == [] and not missing.exists()


def test_exports_resolve_lineage_currency_totals_html_csv_and_tamper(prepared):
    case = create(prepared)
    result = export_evidence(prepared['database'], prepared['processed'], prepared['root']/'exports',
        case_id=case['case_id'], case_version=1, at=AT)
    directory = Path(result['output_directory']); bundle = json.loads((directory/'evidence.json').read_text())
    ids = {x['transaction_id'] for x in bundle['transactions']}
    assert ids == {t for f in bundle['findings'] for t in f['transaction_ids']}
    assert all(x['source_file_id'] and x['source_record_number'] and x['source_timestamp'] for x in bundle['transactions'])
    assert 'is_laundering' not in json.dumps(bundle)
    assert Decimal(bundle['currency_totals']['USD']['paid']) == Decimal('59.00')
    assert Decimal(bundle['currency_totals']['EUR']['paid']) == Decimal('5.00')
    assert "'=1" in (directory/'transactions.csv').read_text()
    assert '<script>fixture</script>' not in (directory/'summary.html').read_text()
    assert '&lt;script&gt;fixture&lt;/script&gt;' in (directory/'summary.html').read_text()
    assert (directory/'network.png').read_bytes().startswith(b'\x89PNG')
    assert report_archive(directory).startswith(b'PK')
    assert export_evidence(prepared['database'], prepared['processed'], prepared['root']/'exports', case_id=case['case_id'], case_version=1, at=AT)['status'] == 'reused'
    (directory/'transactions.csv').write_text('tampered')
    with pytest.raises(ValueError, match='integrity'):
        verify_report(directory)


def test_report_failure_does_not_publish_and_evaluation_is_never_read(prepared):
    evaluation = prepared['processed']/'evaluation'/prepared['dataset_id']/'labels.parquet'
    evaluation.write_bytes(b'labels must never be read')
    kwargs = {'snapshot_id': prepared['model']['snapshot']['snapshot_id'], 'at': AT, 'formats': ['json']}
    export_evidence(prepared['database'], prepared['processed'], prepared['root']/'good', **kwargs)
    with patch('fintrace.reporting.export._totals', side_effect=ValueError('simulated failure')):
        with pytest.raises(ValueError, match='simulated'):
            export_evidence(prepared['database'], prepared['processed'], prepared['root']/'failed', **kwargs)
    assert not (prepared['root']/'failed').exists()
    with patch('fintrace.graph.visualization.render_graph_png', side_effect=OSError('simulated renderer failure')):
        with pytest.raises(OSError, match='renderer failure'):
            export_evidence(prepared['database'], prepared['processed'], prepared['root']/'staged-failure',
                snapshot_id=kwargs['snapshot_id'], at=AT)
    assert list((prepared['root']/'staged-failure').iterdir()) == []
    with pytest.raises(ValueError, match='Unsupported'):
        export_evidence(prepared['database'], prepared['processed'], prepared['root']/'bad', formats=['exe'], snapshot_id=kwargs['snapshot_id'], at=AT)
    with pytest.raises(ValueError, match='raw/evaluation'):
        export_evidence(prepared['database'], prepared['processed'], prepared['root']/'raw', **kwargs)
    # A financially valid row at the exclusive cutoff must not enter the earlier report.
    bundle = json.loads(next((prepared['root']/'good').glob('report-*/evidence.json')).read_text())
    assert all(x['occurred_at'] < '2022-09-01T01:00:00+00:00' for x in bundle['transactions'])


def replay(fixture, root, **kwargs):
    return replay_transactions(fixture['transactions'], fixture['policy'], ROOT/'config/scoring.toml', ROOT/'config/alerts.toml', root,
        start=CUTOFF, end='2022-09-01T01:10:00Z', step_minutes=5, actor='fixture-replay', at=AT, **kwargs)


def test_replay_resume_equals_uninterrupted_and_ties_are_atomic(prepared):
    root = prepared['root']/'replays'
    first = replay(prepared, root, max_steps=1)
    assert first['status'] == 'in_progress' and first['seen_records'] == 7
    assert first['watermark'] == '2022-09-01T01:00:00+00:00'
    first_run = Path(first['output_directory'])/'rule_runs'/first['steps'][0]['rules_run_id']/'findings.json'
    frozen = first_run.read_bytes()
    checkpoint = Path(first['output_directory'])/'checkpoint.json'
    finished = replay(prepared, root, checkpoint=checkpoint)
    assert finished['status'] == 'completed' and finished['seen_records'] == 10
    assert [x['new_event_records'] for x in finished['steps']] == [7, 2, 1]
    assert first_run.read_bytes() == frozen
    direct = replay(prepared, prepared['root']/'direct')
    from fintrace.storage.alert_store import AlertStore
    with AlertStore(finished['database_path']) as left, AlertStore(direct['database_path']) as right:
        assert left.list_alerts() == right.list_alerts()
        for alert in left.list_alerts():
            assert left.events(alert['alert_id']) == right.events(alert['alert_id'])
    assert [s['rules_run_id'] for s in finished['steps']] == [s['rules_run_id'] for s in direct['steps']]
    assert replay(prepared, root, checkpoint=checkpoint)['steps'] == finished['steps']


def test_replay_recovers_import_before_checkpoint_without_duplicate_events(prepared):
    root = prepared['root']/'interrupted'
    from fintrace.replay import engine
    publish = engine._publish
    calls = 0
    def fail_after_import(path, value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('interrupted after commit')
        return publish(path, value)
    with patch.object(engine, '_publish', fail_after_import):
        with pytest.raises(RuntimeError, match='interrupted'):
            replay(prepared, root, max_steps=1)
    state = read_checkpoint(next(root.glob('replay-*/checkpoint.json')))
    assert state['steps'] == []
    result = replay(prepared, root)
    direct = replay(prepared, prepared['root']/'direct')
    from fintrace.storage.alert_store import AlertStore
    with AlertStore(result['database_path']) as left, AlertStore(direct['database_path']) as right:
        assert left.list_alerts() == right.list_alerts()
        assert sum(len(left.events(a['alert_id'])) for a in left.list_alerts()) == sum(len(right.events(a['alert_id'])) for a in right.list_alerts())


def test_replay_changed_policy_and_corrupt_checkpoint_are_rejected(prepared):
    state = replay(prepared, prepared['root']/'replays', max_steps=1)
    checkpoint = Path(state['output_directory'])/'checkpoint.json'
    prepared['policy'].write_text(prepared['policy'].read_text()+'\n# changed policy bytes\n')
    with pytest.raises(ValueError, match='changed'):
        replay(prepared, prepared['root']/'replays', checkpoint=checkpoint)
    value = json.loads(checkpoint.read_text()); value['watermark'] = '2099-01-01T00:00:00Z'
    checkpoint.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='integrity'):
        read_checkpoint(checkpoint)


def test_replay_graph_matches_batch_and_never_orders_tied_events(prepared):
    from fintrace.graph.runner import run_graph_snapshot
    graph_policy = prepared['root']/'graph.toml'
    graph_policy.write_text((ROOT/'config/graph.toml').read_text().replace('minimum_hops = 3', 'minimum_hops = 2'))
    (prepared['processed']/'evaluation'/prepared['dataset_id']/'labels.parquet').write_bytes(b'not detector input')
    result = replay(prepared, prepared['root']/'graph-replay', graph_policy=graph_policy)
    batch = run_graph_snapshot(prepared['transactions'], graph_policy, CUTOFF, prepared['root']/'batch-graph')
    first = json.loads((Path(result['output_directory'])/'graph_runs'/result['steps'][0]['graph_run_id']/'graph.json').read_text())
    expected = json.loads((Path(batch['output_directory'])/'graph.json').read_text())
    assert first['findings'] == expected['findings'] and first['findings']
    from fintrace.contracts import utc_instant
    for step in result['steps']:
        graph = json.loads((Path(result['output_directory'])/'graph_runs'/step['graph_run_id']/'graph.json').read_text())
        times = {row['transaction_id']: utc_instant(row['occurred_at']) for row in graph['edges']}
        for finding in graph['findings']:
            evidence = [times[x] for x in finding['transaction_ids']]
            assert all(a < b for a, b in zip(evidence, evidence[1:]))
            assert all(value < utc_instant(step['cutoff']) for value in evidence)


def test_report_missing_source_fails_without_completed_publication(prepared):
    path = prepared['transactions']
    with path.open('ab') as handle:
        handle.write(b'corrupted source')
    with pytest.raises(ValueError, match='integrity'):
        export_evidence(prepared['database'], prepared['processed'], prepared['root']/'reports',
                        snapshot_id=prepared['model']['snapshot']['snapshot_id'], at=AT)
    assert not list((prepared['root']/'reports').glob('report-*'))


def test_new_workspace_pages_and_explicit_case_creation(prepared, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('FINTRACE_ALERT_DATABASE', str(prepared['database']))
    monkeypatch.setenv('FINTRACE_PROCESSED_ROOT', str(prepared['processed']))
    monkeypatch.setenv('FINTRACE_EXPORT_ROOT', str(prepared['root']/'ui-reports'))
    at = AppTest.from_file(ROOT/'app/streamlit_app.py', default_timeout=60).run()
    for route in ['Cases', 'Reports', 'Replay']:
        at.radio(key='navigation').set_value(route).run()
        assert not at.exception
    assert not (prepared['processed']/'replays').exists()
    assert not (prepared['root']/'ui-reports').exists()
    at.radio(key='navigation').set_value('Cases').run()
    next(x for x in at.text_input if x.label == 'Case title').set_value('UI synthetic case')
    next(x for x in at.text_input if x.label == 'Case creator').set_value('ui-analyst')
    next(x for x in at.text_area if x.label == 'Creation rationale').set_value('Review this synthetic evidence')
    next(x for x in at.multiselect if x.label == 'Alerts to attach').set_value([prepared['model']['alerts'][0]['alert_id']])
    next(x for x in at.button if x.label == 'Create case').click().run()
    assert not at.exception
    cases = read_cases(prepared['database'])['items']; assert len(cases) == 1
    at.run()
    assert read_cases(prepared['database'], cases[0]['case_id'])['case']['version'] == 1
    # Explicit reports write artifacts once, rerender keeps the completed report frozen.
    at.radio(key='navigation').set_value('Reports').run()
    next(x for x in at.button if x.label == 'Generate evidence report').click().run()
    assert not at.exception and len(list((prepared['root']/'ui-reports').glob('report-*'))) == 1
    at.run()
    assert len(list((prepared['root']/'ui-reports').glob('report-*'))) == 1


def test_replay_rejects_changed_future_source_without_touching_frozen_step(prepared):
    import pyarrow.parquet as pq
    from fintrace.rules.runner import _hash
    state = replay(prepared, prepared['root']/'replays', max_steps=1)
    checkpoint = Path(state['output_directory'])/'checkpoint.json'
    evidence = Path(state['output_directory'])/'rule_runs'/state['steps'][0]['rules_run_id']/'findings.json'
    frozen = evidence.read_bytes()
    table = pq.read_table(prepared['transactions'])
    # Re-encoding a newly supplied source changes input identity even if financial values agree.
    pq.write_table(table, prepared['transactions'], compression='snappy')
    marker_path = prepared['transactions'].parent/'completion.json'
    marker = json.loads(marker_path.read_text())
    for artifact in marker['detection_artifacts']:
        if artifact['file'] == 'transactions.parquet':
            artifact['sha256'] = _hash(prepared['transactions'])
    marker_path.write_text(json.dumps(marker))
    with pytest.raises(ValueError, match='changed'):
        replay(prepared, prepared['root']/'replays', checkpoint=checkpoint)
    assert evidence.read_bytes() == frozen and len(read_checkpoint(checkpoint)['steps']) == 1


def test_case_close_requires_disposition_and_export_old_version_stays_frozen(prepared):
    case = create(prepared)
    with pytest.raises(ValueError, match='Unexpected case payload'):
        action(prepared, case, 'note', {'text': 'fixture', 'typo': True}, 'bad-payload')
    with pytest.raises(ValueError, match='disposition'):
        action(prepared, case, 'transition', {'state': 'closed'}, 'bad-close')
    assert read_cases(prepared['database'], case['case_id'])['case']['version'] == 1
    action(prepared, case, 'note', {'text': 'Later correction is not in version one.'}, 'later-note')
    result = export_evidence(prepared['database'], prepared['processed'], prepared['root']/'reports',
        case_id=case['case_id'], case_version=1, formats=['json'], at=AT)
    payload = json.loads((Path(result['output_directory'])/'evidence.json').read_text())
    assert payload['case']['version'] == 1 and payload['case']['notes'] == []


def test_replay_page_explicit_start_continue_and_no_repeat_write(prepared, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('FINTRACE_ALERT_DATABASE', str(prepared['database']))
    monkeypatch.setenv('FINTRACE_PROCESSED_ROOT', str(prepared['processed']))
    at = AppTest.from_file(ROOT/'app/streamlit_app.py', default_timeout=60).run()
    at.radio(key='navigation').set_value('Replay').run()
    next(x for x in at.text_input if x.label == 'Replay operator').set_value('ui-replay')
    next(x for x in at.checkbox if x.label == 'Include temporal graph analysis').set_value(False)
    next(x for x in at.button if x.label == 'Start replay and process first cutoff').click().run()
    assert not at.exception
    checkpoint = next((prepared['processed']/'replays').glob('replay-*/checkpoint.json'))
    assert len(read_checkpoint(checkpoint)['steps']) == 1
    at.run()
    assert len(read_checkpoint(checkpoint)['steps']) == 1
    next(x for x in at.button if x.label == 'Process next replay cutoff').click().run()
    assert not at.exception and len(read_checkpoint(checkpoint)['steps']) == 2
