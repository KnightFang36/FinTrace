"""Atomic, local evidence reports from immutable snapshots and verified financial rows."""
import csv
from decimal import Decimal, localcontext
from html import escape
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

from fintrace.contracts import (AccountKey, TRANSACTION_FIELDS, TRANSACTION_METADATA,
                                canonical_json, content_id, json_value, utc_instant)
from fintrace.investigations.dashboard import load_dashboard
from fintrace.rules.runner import _detection_inventory, _hash
from fintrace.storage.case_store import read_cases

LIMITATIONS = ['IBM fully synthetic data; internal investigation evidence only.',
               'Findings warrant review and do not establish criminal intent or exact source of funds.',
               'Fixed-policy priorities are not probabilities. Evidence scope is limited to the selected snapshots.',
               'Case/alert workflow metadata is captured at export time and may postdate the evidence cutoff.']


def _safe_root(root):
    path = Path(root).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or {'raw', 'evaluation'} & set(path.resolve().parts):
        raise ValueError('Use a local export root outside raw/evaluation, without symbolic links')
    return path.resolve()


def _scope(database, snapshot_id, alert_ids, case_id, case_version):
    if case_id:
        if snapshot_id is not None or alert_ids:
            raise ValueError('Choose either a case version or a snapshot/alert scope')
        if type(case_version) is not int or case_version < 1:
            raise ValueError('Case exports require an explicit positive case_version')
        case = read_cases(database, case_id, version=case_version)['case']
        attachments = case['evidence_snapshots']
    else:
        if case_version is not None:
            raise ValueError('case_version requires a case ID')
        case = None
        model = load_dashboard(database, snapshot_id)
        chosen = sorted(set(alert_ids)) if alert_ids else [x['alert_id'] for x in model['alerts']]
        if not chosen:
            raise ValueError('No alerts selected for export')
        attachments = [{'snapshot_id': snapshot_id, 'alerts': [{'alert_id': x} for x in chosen]}]
    snapshots, findings, alerts = {}, {}, []
    for attachment in attachments:
        model = load_dashboard(database, attachment['snapshot_id'])
        if case:
            frozen = {k: v for k, v in attachment.items() if k != 'evidence_hash'}
            if content_id(frozen) != attachment['evidence_hash']:
                raise ValueError('Case evidence integrity mismatch')
        available = {x['alert_id']: x for x in model['alerts']}
        snapshots[attachment['snapshot_id']] = model['snapshot']
        for captured in attachment['alerts']:
            identifier = captured['alert_id']
            if identifier not in available:
                raise ValueError('Unknown alert or alert outside the selected snapshot')
            alert = captured if case else available[identifier]
            if case and set(alert['finding_ids']) - set(model['findings']):
                raise ValueError('Case references evidence outside its frozen snapshot')
            alerts.append(alert | {'snapshot_id': attachment['snapshot_id']})
            for identifier in alert['finding_ids']:
                findings[identifier] = model['findings'][identifier]
    if not findings or len(findings) > 10000 or len(alerts) > 1000:
        raise ValueError('Report requires 1–10,000 findings and at most 1,000 alert references')
    return case, snapshots, findings, alerts


def _transactions(processed_root, findings):
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq
    by_dataset = {}
    for finding in findings.values():
        by_dataset.setdefault(finding['dataset_id'], set()).update(finding['transaction_ids'])
    if sum(map(len, by_dataset.values())) > 50000:
        raise ValueError('Report transaction budget exceeds 50,000; select a smaller alert scope')
    rows, sources, integrity = {}, {}, []
    base = Path(processed_root).resolve()
    for dataset_id, ids in sorted(by_dataset.items()):
        if not dataset_id or Path(dataset_id).name != dataset_id or dataset_id in {'.', '..'}:
            raise ValueError('Invalid dataset identity')
        parent = base / 'datasets' / dataset_id
        if any(x.is_symlink() for x in (base, base/'datasets', parent)):
            raise ValueError('Dataset paths must not be symbolic links')
        completion_path = parent/'completion.json'; path = parent/'transactions.parquet'; quality_path = parent/'quality.json'
        if any(x.is_symlink() for x in (completion_path, path, quality_path)):
            raise ValueError('Detection artifacts must not be symbolic links')
        completion = json.loads(completion_path.read_text())
        if completion.get('status') != 'completed' or completion.get('dataset_id') != dataset_id:
            raise ValueError('Use a completed matching detection dataset')
        inventory = _detection_inventory(completion)
        for name in ('transactions.parquet', 'quality.json'):
            artifact = parent/name
            if _hash(artifact) != inventory[name]:
                raise ValueError('Detection input integrity mismatch')
            integrity.append((artifact, inventory[name]))
        fields = set(pq.read_schema(path).names)
        if not set(TRANSACTION_FIELDS) <= fields or fields - set(TRANSACTION_FIELDS) - TRANSACTION_METADATA:
            raise ValueError('Only label-free normalized transaction columns are accepted')
        quality = json.loads(quality_path.read_text())
        if quality['dataset_id'] != dataset_id:
            raise ValueError('Conflicting dataset identity')
        sources[dataset_id] = {'input_hashes': {k: inventory[k] for k in ('transactions.parquet', 'quality.json')},
                              'timestamp_policy': quality['timestamp_policy'],
                              'timestamp_policy_basis': quality.get('timestamp_policy_basis'),
                              'observation_intervals': quality['observation_intervals'], 'known_gaps': quality['known_gaps']}
        scanner = ds.dataset(path, format='parquet').scanner(filter=ds.field('transaction_id').isin(sorted(ids)),
                                                            batch_size=16384, use_threads=False)
        found = set()
        for batch in scanner.to_batches():
            for row in batch.to_pylist():
                identifier = row['transaction_id']
                if identifier in found or row['dataset_id'] != dataset_id:
                    raise ValueError('Duplicate transaction ID or conflicting dataset')
                found.add(identifier); rows[identifier] = json_value(row)
        if found != ids:
            raise ValueError('Report finding references missing source transactions')
    for finding in findings.values():
        for identifier in finding['transaction_ids']:
            if utc_instant(rows[identifier]['occurred_at']) >= utc_instant(finding['cutoff']):
                raise ValueError('Future transaction appears in frozen evidence')
    return [rows[key] for key in sorted(rows)], sources, integrity


def _totals(transactions):
    result = {}
    with localcontext() as context:
        context.prec = 80
        for row in transactions:
            for currency_key, amount_key, side in [('payment_currency', 'amount_paid', 'paid'),
                                                    ('receiving_currency', 'amount_received', 'received')]:
                currency = row[currency_key]
                item = result.setdefault(currency, {'paid': Decimal(0), 'received': Decimal(0), 'paid_count': 0, 'received_count': 0})
                item[side] += Decimal(row[amount_key]); item[side+'_count'] += 1
    return json_value(dict(sorted(result.items())))


def _cell(value):
    text = canonical_json(value) if isinstance(value, (dict, list)) else str(value)
    if text.startswith(('\t', '\r', '\n')) or text.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + text
    return text


def verify_report(directory):
    path = Path(directory)
    if path.is_symlink() or (path/'manifest.json').is_symlink():
        raise ValueError('Report must not be a symbolic link')
    manifest = json.loads((path/'manifest.json').read_text())
    if manifest.get('status') != 'completed' or path.name != manifest.get('report_id'):
        raise ValueError('Report is not complete or has a conflicting identity')
    expected_hash = manifest.get('manifest_hash')
    if content_id({k: v for k, v in manifest.items() if k != 'manifest_hash'}) != expected_hash:
        raise ValueError('Report manifest integrity mismatch')
    files = manifest.get('artifacts')
    if not isinstance(files, list) or not files or len({x['file'] for x in files}) != len(files):
        raise ValueError('Invalid report inventory')
    allowed = {'evidence.json', 'transactions.csv', 'findings.csv', 'summary.html', 'network.png'}
    for item in files:
        name = item['file']; artifact = path/name
        if name not in allowed or artifact.is_symlink() or _hash(artifact) != item['sha256']:
            raise ValueError('Report artifact integrity mismatch')
    return manifest


def export_evidence(database, processed_root, export_root, *, snapshot_id=None, alert_ids=(),
                    case_id=None, case_version=None, formats=('json', 'csv', 'html', 'png'), at):
    formats = tuple(sorted(set(formats)))
    if not formats or set(formats) - {'json', 'csv', 'html', 'png'}:
        raise ValueError('Unsupported report formats; choose json, csv, html, png')
    instant = utc_instant(at); root = _safe_root(export_root)
    case, snapshots, findings, alerts = _scope(database, snapshot_id, alert_ids, case_id, case_version)
    if any(utc_instant(s['window']['end']) > instant for s in snapshots.values()):
        raise ValueError('Export time precedes the analysis cutoff')
    if case and utc_instant(case['updated_at']) > instant:
        raise ValueError('Export time precedes the selected case version')
    transactions, sources, integrity = _transactions(processed_root, findings)
    bundle = {'schema_version': '1', 'export_policy_version': 'evidence-export-v1', 'synthetic': True, 'exported_at': instant.isoformat(),
              'case': case, 'snapshots': snapshots, 'alerts': alerts, 'findings': list(findings.values()),
              'transactions': transactions, 'sources': sources, 'currency_totals': _totals(transactions),
              'limitations': LIMITATIONS}
    identifier = 'report-' + content_id({'bundle': bundle, 'formats': formats})
    target = root/identifier
    if target.exists():
        return verify_report(target) | {'output_directory': str(target), 'status': 'reused'}
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.report-', dir=root) as temporary:
        stage = Path(temporary)
        (stage/'evidence.json').write_text(canonical_json(bundle)+'\n', encoding='utf-8')
        if 'csv' in formats:
            for name, records in [('transactions', transactions), ('findings', list(findings.values()))]:
                fields = sorted(records[0])
                with (stage/(name+'.csv')).open('w', encoding='utf-8', newline='') as handle:
                    writer = csv.writer(handle, quoting=csv.QUOTE_ALL); writer.writerow(fields)
                    for record in records:
                        writer.writerow([_cell(record[field]) for field in fields])
        if 'html' in formats:
            text = '<!doctype html><html><head><meta charset="utf-8"><title>FinTrace evidence report</title></head><body>'
            text += '<h1>FinTrace internal investigation report</h1><p>IBM fully synthetic data.</p>'
            text += '<p>'+escape(f'{len(findings)} findings; {len(transactions)} distinct evidence transfers. Review priorities are not probabilities.')+'</p>'
            if case:
                text += '<h2>'+escape(case['title'])+'</h2><pre>'+escape(json.dumps(case, indent=2))+'</pre>'
            text += '<h2>Totals by currency (distinct evidence transfers)</h2><pre>'+escape(json.dumps(bundle['currency_totals'], indent=2))+'</pre>'
            for finding in findings.values():
                text += '<h2>'+escape(finding['rule_id'])+'</h2><pre>'+escape(json.dumps(finding, indent=2))+'</pre>'
            text += '<h2>Coverage and provenance</h2><pre>'+escape(json.dumps({'snapshots': snapshots, 'sources': sources}, indent=2))+'</pre>'
            text += '<h2>Limitations</h2><ul>'+''.join('<li>'+escape(x)+'</li>' for x in LIMITATIONS)+'</ul></body></html>'
            (stage/'summary.html').write_text(text, encoding='utf-8')
        visualization = None
        if 'png' in formats:
            import networkx as nx
            from fintrace.graph.visualization import render_graph_png
            os.environ.setdefault('MPLCONFIGDIR', str(root/'.matplotlib'))
            graph = nx.MultiDiGraph()
            for row in transactions:
                graph.add_edge(AccountKey(row['sender_bank_id'], row['sender_account_id']),
                               AccountKey(row['receiver_bank_id'], row['receiver_account_id']), key=row['transaction_id'])
            visualization = render_graph_png(graph, stage/'network.png', {'max_display_nodes': 100, 'max_display_edges': 200, 'layout_seed': 42})
        for path, expected in integrity:
            if _hash(path) != expected:
                raise ValueError('Detection input changed during export')
        manifest = {'schema_version': '1', 'export_policy_version': 'evidence-export-v1', 'status': 'completed', 'report_id': identifier,
                    'exported_at': instant.isoformat(), 'snapshot_ids': sorted(snapshots),
                    'case_id': case_id, 'case_version': case_version, 'dataset_ids': sorted(sources),
                    'formats': formats, 'finding_count': len(findings), 'transaction_count': len(transactions),
                    'filters': {'snapshot_id': snapshot_id, 'alert_ids': sorted(set(alert_ids)), 'case_id': case_id, 'case_version': case_version},
                    'sources': sources, 'policy_snapshots': {k: v['policy'] for k, v in snapshots.items()},
                    'coverage': {k: v['coverage'] for k, v in snapshots.items()},
                    'currency_totals': bundle['currency_totals'], 'visualization': visualization,
                    'limitations': LIMITATIONS, 'artifacts': [{'file': p.name, 'sha256': _hash(p)} for p in sorted(stage.iterdir())]}
        manifest['manifest_hash'] = content_id(manifest)
        (stage/'manifest.json').write_text(canonical_json(manifest)+'\n', encoding='utf-8')
        stage.rename(target)
    return manifest | {'output_directory': str(target)}


def report_archive(directory):
    manifest = verify_report(directory); path = Path(directory)
    names = ['manifest.json'] + [x['file'] for x in manifest['artifacts']]
    if sum((path/name).stat().st_size for name in names) > 100 * 1024 * 1024:
        raise ValueError('Report exceeds the 100 MiB browser download budget; use local artifacts')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr(name, (path/name).read_bytes())
    return buffer.getvalue()
