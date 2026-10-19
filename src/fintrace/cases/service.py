"""Explicit, idempotent case actions with frozen evidence and append-only audit."""
from copy import deepcopy
import json
from fintrace.contracts import content_id, utc_instant
from fintrace.investigations.dashboard import load_dashboard
from fintrace.storage.case_store import CaseStore, read_cases

TRANSITIONS = {'open': {'investigating', 'closed'}, 'investigating': {'escalated', 'closed'},
               'escalated': {'investigating', 'closed'}, 'closed': set()}


def _text(value, name, maximum=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{name} must be nonblank text, at most {maximum} characters')
    return value.strip()


def _attachment(database, payload, at):
    model = load_dashboard(database, _text(payload.get('snapshot_id'), 'snapshot_id'))
    ids = payload.get('alert_ids')
    if not isinstance(ids, list) or not ids or len(ids) > 100 or any(not isinstance(x, str) for x in ids):
        raise ValueError('Select 1–100 alert IDs')
    selected = {a['alert_id']: a for a in model['alerts']}
    if set(ids) - set(selected):
        raise ValueError('Unknown alert or alert outside the selected snapshot')
    if utc_instant(model['snapshot']['window']['end']) > at:
        raise ValueError('Cannot attach evidence from after the action time')
    alerts = [selected[x] for x in sorted(set(ids))]
    value = {'snapshot_id': model['snapshot']['snapshot_id'], 'cutoff': model['snapshot']['window']['end'],
             'alerts': alerts, 'finding_ids': sorted({x for a in alerts for x in a['finding_ids']}),
             'accounts': [selected[x]['subject'] for x in sorted(set(ids))]}
    return value | {'evidence_hash': content_id(value)}


def apply_case_action(database, case_id, action, *, actor, at, reason, expected_version,
                      request_id, payload=None):
    """Create/attach/note/assign/transition/reopen; each successful request adds one version."""
    actor = _text(actor, 'actor', 200); reason = _text(reason, 'reason')
    request_id = _text(request_id, 'request_id', 200); instant = utc_instant(at)
    if type(expected_version) is not int or expected_version < 0:
        raise ValueError('expected_version must be a nonnegative integer')
    if payload is not None and not isinstance(payload, dict):
        raise ValueError('Case payload must be an object')
    payload = deepcopy(payload or {})
    if action not in {'create', 'attach', 'note', 'assign', 'transition', 'reopen'}:
        raise ValueError('Unsupported case action')
    allowed_payload = {'create': {'title', 'snapshot_id', 'alert_ids'}, 'attach': {'snapshot_id', 'alert_ids'},
                       'note': {'text'}, 'assign': {'assignee'}, 'transition': {'state', 'disposition'}, 'reopen': set()}
    if set(payload) - allowed_payload[action]:
        raise ValueError('Unexpected case payload fields')
    request_hash = content_id({'case_id': case_id, 'action': action, 'actor': actor, 'at': instant,
                               'reason': reason, 'expected_version': expected_version, 'payload': payload})
    # Evidence projection happens before opening the writer; it performs read-only queries.
    attachment = _attachment(database, payload, instant) if action in {'create', 'attach'} else None
    with CaseStore(database) as store:
        connection = store.connection
        connection.execute('BEGIN TRANSACTION')
        try:
            previous = connection.execute('SELECT request_hash,payload FROM ft_case_requests WHERE id=?', [request_id]).fetchone()
            if previous:
                if previous[0] != request_hash:
                    raise ValueError('Request ID already used for a different action')
                connection.execute('COMMIT')
                return json.loads(previous[1])
            if action == 'create':
                if case_id is not None or expected_version != 0:
                    raise ValueError('Creation requires no case ID and expected_version=0')
                case = {'schema_version': '1', 'case_id': 'case-' + content_id(request_id), 'version': 0,
                        'title': _text(payload.get('title'), 'title', 300), 'state': 'open', 'policy_version': 'case-workflow-v1',
                        'assignee': None, 'notes': [], 'evidence_snapshots': [], 'disposition': None,
                        'created_at': instant.isoformat(), 'updated_at': instant.isoformat()}
                previous_state = None
            else:
                case = store.get_case(case_id)
                if case['version'] != expected_version:
                    raise ValueError('Stale case version')
                if instant < utc_instant(case['updated_at']):
                    raise ValueError('Case action time cannot move backwards')
                previous_state = case['state']
                if case['state'] == 'closed' and action not in {'reopen', 'note'}:
                    raise ValueError('Explicitly reopen the closed case before changing it')
            if action in {'create', 'attach'}:
                if attachment['evidence_hash'] in {x['evidence_hash'] for x in case['evidence_snapshots']}:
                    raise ValueError('This evidence attachment is already present')
                if len(case['evidence_snapshots']) >= 100:
                    raise ValueError('Case evidence attachment budget exceeded')
                case['evidence_snapshots'].append(attachment)
            elif action == 'note':
                case['notes'].append({'text': _text(payload.get('text'), 'note'), 'actor': actor,
                                      'at': instant.isoformat(), 'version': case['version'] + 1})
            elif action == 'assign':
                case['assignee'] = _text(payload.get('assignee'), 'assignee', 200)
            elif action == 'transition':
                target = payload.get('state')
                if not isinstance(target, str) or target not in TRANSITIONS[case['state']]:
                    raise ValueError('Invalid case transition')
                if target == 'closed':
                    case['disposition'] = {'value': _text(payload.get('disposition'), 'disposition'),
                                           'reason': reason, 'actor': actor, 'at': instant.isoformat()}
                case['state'] = target
            elif action == 'reopen':
                if case['state'] != 'closed':
                    raise ValueError('Only a closed case can be reopened')
                case['state'] = 'investigating'
            case['version'] += 1; case['updated_at'] = instant.isoformat()
            if case['version'] > 1000:
                raise ValueError('Case version budget exceeded')
            event = {'schema_version': '1', 'event_id': 'case-event-' + content_id(request_id),
                     'case_id': case['case_id'], 'entity_type': 'case', 'entity_id': case['case_id'],
                     'version': case['version'], 'action': action,
                     'actor': actor, 'at': instant.isoformat(), 'reason': reason,
                     'previous_state': previous_state, 'new_state': case['state'],
                     'case_hash': content_id(case), 'request_id': request_id,
                     'evidence_hashes': [x['evidence_hash'] for x in case['evidence_snapshots']]}
            store.save_case(case, event, expected_version)
            connection.execute('INSERT INTO ft_case_requests VALUES (?,?,?)', [request_id, request_hash, json.dumps(case)])
            connection.execute('COMMIT')
            return case
        except Exception:
            connection.execute('ROLLBACK')
            raise
