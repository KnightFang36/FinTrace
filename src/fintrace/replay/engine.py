"""Bounded chronological cutoff replay using the existing rule/graph/alert services."""
from datetime import timedelta
import json
import os
from pathlib import Path
import tempfile
from time import monotonic

from fintrace.alerts.runner import import_analysis, load_analysis_run
from fintrace.contracts import canonical_json, content_id, utc_instant
from fintrace.graph.runner import run_graph_snapshot
from fintrace.reporting.export import _safe_root
from fintrace.rules.runner import _hash, load_detection_snapshot, run_rule_snapshot

ENGINE_VERSION = 'historical-replay-v1'


def read_checkpoint(path):
    path = Path(path)
    if path.name != 'checkpoint.json' or path.is_symlink() or path.parent.is_symlink():
        raise ValueError('Use a local replay checkpoint.json')
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('Replay checkpoint exceeds the loading budget')
    value = json.loads(path.read_text())
    digest = value.get('checkpoint_hash')
    if content_id({k: v for k, v in value.items() if k != 'checkpoint_hash'}) != digest:
        raise ValueError('Replay checkpoint integrity mismatch')
    if value.get('schema_version') != '1' or value.get('engine_version') != ENGINE_VERSION:
        raise ValueError('Unsupported replay checkpoint version')
    if path.parent.name != value.get('replay_id') or 'replay-' + content_id(value['identity']) != value['replay_id']:
        raise ValueError('Conflicting replay identity')
    return value


def list_replays(output_root):
    root = Path(output_root)
    if not root.exists():
        return {'items': [], 'truncated': False}
    root = _safe_root(root)
    paths = sorted(root.glob('replay-*/checkpoint.json'))
    if len(paths) > 200:
        raise ValueError('Replay catalog exceeds 200 runs; use the CLI for an explicit checkpoint')
    return {'items': [read_checkpoint(p) for p in paths], 'truncated': False}


def _publish(path, checkpoint):
    checkpoint = {k: v for k, v in checkpoint.items() if k != 'checkpoint_hash'}
    checkpoint['checkpoint_hash'] = content_id(checkpoint)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(canonical_json(checkpoint)+'\n'); handle.flush(); os.fsync(handle.fileno())
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return checkpoint


def _event_progress(path, lower, cutoff):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    expression = ds.field('occurred_at') < pa.scalar(cutoff, type=pa.timestamp('us', tz='UTC'))
    if lower is not None:
        expression = expression & (ds.field('occurred_at') >= pa.scalar(lower, type=pa.timestamp('us', tz='UTC')))
    scanner = ds.dataset(path, format='parquet').scanner(filter=expression, use_threads=False, batch_size=16384,
        columns=['occurred_at', 'source_file_id', 'source_record_number', 'transaction_id'])
    count = 0; last = None
    for batch in scanner.to_batches():
        count += batch.num_rows
        if not batch.num_rows:
            continue
        latest = pc.max(batch.column(0)).as_py()
        if last is not None and latest < last[0]:
            continue
        ties = batch.filter(pc.equal(batch.column(0), pa.scalar(latest, type=batch.schema.field(0).type)))
        for row in ties.to_pylist():
            key = (row['occurred_at'], row['source_file_id'], row['source_record_number'], row['transaction_id'])
            if last is None or key > last:
                last = key
    return count, json.loads(canonical_json(last)) if last else None


def _verify_steps(state, target, cutoffs):
    from fintrace.investigations.dashboard import _connect
    from fintrace.scoring.priority import validate_priority_snapshot
    if len(state['steps']) > len(cutoffs):
        raise ValueError('Invalid replay step count')
    if not state['steps']:
        return
    with _connect(target/'alerts.duckdb') as connection:
        for index, step in enumerate(state['steps']):
            if step['cutoff'] != cutoffs[index].isoformat():
                raise ValueError('Replay checkpoint cutoff order mismatch')
            for kind, key in [('rules', 'rules_run_id'), ('graphs', 'graph_run_id')]:
                identifier = step.get(key)
                if not identifier:
                    if kind == 'graphs' and not state['identity']['policy_hashes']['graph']:
                        continue
                    raise ValueError('Replay checkpoint omits detector identity')
                prefix = 'rules-' if kind == 'rules' else 'graphs-'
                if not identifier.startswith(prefix) or len(identifier) != len(prefix)+64 or any(c not in '0123456789abcdef' for c in identifier[len(prefix):]):
                    raise ValueError('Invalid replay detector identity')
                payload, marker = load_analysis_run(target/({'rules': 'rule_runs', 'graphs': 'graph_runs'}[kind])/identifier, kind)
                if marker['input_hashes'] != state['identity']['input_hashes'] or utc_instant(payload['cutoff']) != cutoffs[index]:
                    raise ValueError('Replay detector input/cutoff mismatch')
            row = connection.execute('SELECT payload FROM ft_priority_runs WHERE id=?', [step['priority_snapshot_id']]).fetchone()
            if row is None or content_id(validate_priority_snapshot(json.loads(row[0]))) != step['priority_payload_hash']:
                raise ValueError('Replay priority checkpoint integrity mismatch')


def replay_transactions(transactions, rule_policy, scoring_policy, alert_policy, output_root, *,
                        start, end, step_minutes, actor, at, graph_policy=None, checkpoint=None, max_steps=None):
    """Replay exclusive UTC watermarks. max_steps bounds this invocation; resume is idempotent."""
    start = utc_instant(start); end = utc_instant(end); instant = utc_instant(at)
    if start > end or end > instant:
        raise ValueError('Replay requires start <= end <= explicit audit time')
    if type(step_minutes) is not int or not 1 <= step_minutes <= 1440:
        raise ValueError('step_minutes must be an integer from 1 to 1440')
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 200:
        raise ValueError('An explicit nonblank replay actor is required')
    if max_steps is not None and (type(max_steps) is not int or not 1 <= max_steps <= 100):
        raise ValueError('max_steps must be from 1 to 100')
    cutoffs = []; current = start
    while current < end:
        cutoffs.append(current); current += timedelta(minutes=step_minutes)
        if len(cutoffs) >= 100:
            raise ValueError('Replay exceeds the 100-cutoff budget; choose a smaller range')
    cutoffs.append(end)
    transactions = Path(transactions)
    if transactions.is_symlink():
        raise ValueError('Replay input must not be a symbolic link')
    _safe_root(transactions.parent)
    transactions = transactions.resolve()
    _, context, hashes = load_detection_snapshot(transactions, start, start=start, max_records=0)
    policies = {'rules': Path(rule_policy), 'scoring': Path(scoring_policy), 'alerts': Path(alert_policy),
                'graph': Path(graph_policy) if graph_policy else None}
    policy_hashes = {key: _hash(path) if path else None for key, path in policies.items()}
    identity = {'engine_version': ENGINE_VERSION, 'dataset_id': context['dataset_id'], 'input_hashes': hashes,
                'policy_hashes': policy_hashes, 'start': start.isoformat(), 'end': end.isoformat(),
                'step_minutes': step_minutes, 'timestamp_ties': 'atomic_exclusive_cutoff_groups',
                'late_events': 'reject_changed_source_on_resume'}
    replay_id = 'replay-' + content_id(identity); root = _safe_root(output_root); target = root/replay_id
    if checkpoint:
        previous = read_checkpoint(checkpoint)
        if previous['identity'] != identity or Path(checkpoint).resolve().parent != target:
            raise ValueError('Checkpoint inputs, policies or output location changed; resume rejected')
    root.mkdir(parents=True, exist_ok=True)
    lock = root/('.'+replay_id+'.lock')
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(descriptor)
    except FileExistsError as error:
        raise ValueError(f'Replay lock exists: {lock}. Confirm no replay is running before removing a stale lock.') from error
    try:
        if target.is_symlink():
            raise ValueError('Replay directory must not be a symbolic link')
        path = target/'checkpoint.json'
        if target.exists():
            state = read_checkpoint(path)
            if state['identity'] != identity or state['actor'] != actor or utc_instant(state['audit_at']) != instant:
                raise ValueError('Replay inputs or audit context changed')
            _verify_steps(state, target, cutoffs)
        else:
            target.mkdir()
            state = {'schema_version': '1', 'engine_version': ENGINE_VERSION, 'replay_id': replay_id,
                     'identity': identity, 'actor': actor, 'audit_at': instant.isoformat(),
                     'transactions_path': str(transactions), 'policy_paths': {k: str(v.resolve()) if v else None for k, v in policies.items()},
                     'status': 'in_progress', 'steps': [], 'watermark': None, 'seen_records': 0,
                     'last_event_ordering_key': None, 'total_cutoffs': len(cutoffs)}
            state = _publish(path, state)
        os.environ.setdefault('MPLCONFIGDIR', str(target/'.matplotlib'))
        pending = cutoffs[len(state['steps']):]
        for cutoff in pending[:max_steps] if max_steps else pending:
            clock = monotonic()
            rules = run_rule_snapshot(transactions, policies['rules'], cutoff, target/'rule_runs')
            graph = run_graph_snapshot(transactions, policies['graph'], cutoff, target/'graph_runs') if graph_policy else None
            imported = import_analysis(rules['output_directory'], graph['output_directory'] if graph else None,
                policies['scoring'], policies['alerts'], target/'alerts.duckdb', actor=actor, at=instant.isoformat())
            count, key = _event_progress(transactions, utc_instant(state['watermark']) if state['watermark'] else None, cutoff)
            # Input/policy checks happen before advancing the durable watermark.
            if any(_hash(transactions.parent/name) != expected for name, expected in hashes.items()):
                raise ValueError('Replay source changed; watermark was not advanced')
            if any(path_ and _hash(path_) != policy_hashes[name] for name, path_ in policies.items()):
                raise ValueError('Replay policy changed; watermark was not advanced')
            from fintrace.investigations.dashboard import _connect
            with _connect(target/'alerts.duckdb') as connection:
                payload = json.loads(connection.execute('SELECT payload FROM ft_priority_runs WHERE id=?',
                                                     [imported['priority_snapshot_id']]).fetchone()[0])
            state['steps'].append({'cutoff': cutoff.isoformat(), 'rules_run_id': rules['run_id'],
                'graph_run_id': graph['run_id'] if graph else None, 'priority_snapshot_id': imported['priority_snapshot_id'],
                'priority_payload_hash': content_id(payload), 'finding_count': rules['finding_count'] + (graph['finding_count'] if graph else 0),
                'scored_accounts': imported['scored_accounts'], 'persisted_alerts': imported['total_persisted_alerts'],
                'new_event_records': count, 'elapsed_seconds': round(monotonic()-clock, 6)})
            state['watermark'] = cutoff.isoformat(); state['seen_records'] += count
            if key:
                state['last_event_ordering_key'] = key
            state['status'] = 'completed' if len(state['steps']) == len(cutoffs) else 'in_progress'
            state = _publish(path, state)
        return state | {'output_directory': str(target), 'database_path': str(target/'alerts.duckdb')}
    finally:
        lock.unlink(missing_ok=True)
