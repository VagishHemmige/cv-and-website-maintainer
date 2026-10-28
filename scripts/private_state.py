"""Reviewed profile updates and per-source discovery checkpoints (standard library).

Approval/coverage arguments are operator assertions, not authentication or proof
that a connector searched. Host permissions and actual human approval still apply.
Run with --help; see references/private-state.md for commands and recovery.
"""
import argparse
import contextlib
import copy
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
import importlib.util

_approval_spec = importlib.util.spec_from_file_location('academic_approval_evidence',
    Path(__file__).with_name('approval_evidence.py'))
approvals = importlib.util.module_from_spec(_approval_spec)
_approval_spec.loader.exec_module(approvals)


def now():
    return dt.datetime.now(dt.timezone.utc)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO string with timezone')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp needs an explicit timezone')
    return parsed.astimezone(dt.timezone.utc)


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def reject_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key: ' + key)
        value[key] = item
    return value


def decode(raw):
    def invalid(value):
        raise ValueError('Non-finite JSON number: ' + value)
    return json.loads(raw, object_pairs_hook=reject_duplicates, parse_constant=invalid)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_hash(path):
    return sha(path.read_bytes()) if path.exists() else None


def plain(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Use an absolute path without traversal')
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and part.resolve() != part):
            raise ValueError('Redirected state/evidence path refused')
    return path


def inside(state, path):
    path = plain(path)
    if state not in path.parents:
        raise ValueError('State/evidence path must be inside the private state directory')
    return path


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be nonblank text')
    return value


def valid_id(value):
    if not re.fullmatch('[0-9a-f]{32}', value):
        raise ValueError('Invalid operation/proposal/run ID')
    return value


def private_root(state, config):
    state = plain(state)
    if not isinstance(config, dict):
        raise ValueError('Profile must be a JSON object')
    project = plain(text(config.get('project_root'), 'project_root')).resolve(strict=True)
    if not state.is_dir() or state == project or project in state.parents:
        raise ValueError('Private state must exist outside the project')
    plugin = Path(__file__).resolve().parents[1]
    if state == plugin or plugin in state.parents:
        raise ValueError('Private state must be outside the plugin package')
    return state


def profile(state):
    state = plain(state)
    path = plain(state / 'config.json')
    raw = path.read_bytes()
    config = decode(raw)
    if not isinstance(config, dict):
        raise ValueError('Profile must be a JSON object')
    private_root(state, config)
    return config, raw


def exclusive(path, raw):
    path = plain(path)
    with path.open('xb') as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


@contextlib.contextmanager
def writer_lock(state, initial_config=None):
    if (state / 'config.json').exists():
        profile(state)
    elif initial_config is not None:
        private_root(state, initial_config)
    else:
        raise ValueError('Existing valid private profile required for state writes')
    path = plain(state / '.private-state-writer.lock')
    token = uuid.uuid4().hex
    try:
        exclusive(path, encoded(dict(token=token, pid=os.getpid(), created=now().isoformat())))
    except FileExistsError as error:
        raise ValueError('Private-state writer is locked; inspect active/interrupted writer, never break blindly') from error
    try:
        yield
    finally:
        # Only remove our own lock. A killed process deliberately leaves its lock.
        if path.exists() and decode(path.read_bytes()).get('token') == token:
            path.unlink()


def atomic_install(target, raw, expected):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.private-state-',
                                         suffix='.tmp', delete=False) as out:
            temporary = Path(out.name)
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        if decode(temporary.read_bytes()) != decode(raw):
            raise ValueError('Temporary JSON verification failed')
        if file_hash(target) != expected:
            raise ValueError('Concurrent state change; refusing replacement')
        if expected is None:
            # Atomic exclusive installation: no partially written initial JSON.
            if os.name == 'nt':
                os.rename(temporary, target)  # Windows rename refuses existing destinations.
            else:
                os.link(temporary, target)
        else:
            os.replace(temporary, target)
        if target.read_bytes() != raw:
            raise ValueError('Committed state differs; inspect operation status')
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def commit(state, target, before, value, kind, assertions, evidence=None, precondition=None,
           approval_raw=None):
    """Caller holds writer_lock; immutable intent permits post-crash inspection."""
    target = inside(state, target)
    raw = encoded(value)
    ident = uuid.uuid4().hex
    directory = inside(state, state / 'state-history')
    directory.mkdir(exist_ok=True)
    operation = directory / ident
    operation.mkdir()
    if before is not None:
        exclusive(operation / 'before.json', before)
        if (operation / 'before.json').read_bytes() != before:
            raise ValueError('Backup verification failed')
    exclusive(operation / 'after.json', raw)
    if (operation / 'after.json').read_bytes() != raw:
        raise ValueError('Operation candidate verification failed')
    intent = dict(id=ident, kind=kind, target=str(target), before_sha256=sha(before) if before else None,
                  after_sha256=sha(raw), created=now().isoformat(), assertions=assertions,
                  evidence=evidence or [])
    if kind == 'profile':
        expected_approval = approvals.target('profile', assertions['proposal_id'], sha(raw), target)
        if approval_raw is None:
            raise ValueError('Approval evidence required for preference commit')
        intent['approval_evidence'] = approvals.persist(operation, approval_raw, expected_approval)
    exclusive(operation / 'intent.json', encoded(intent))
    expected = sha(before) if before is not None else None
    try:
        if file_hash(target) != expected:
            raise ValueError('Concurrent state change')
        if precondition:
            precondition()
        if kind == 'profile':
            approvals.verify(operation, intent['approval_evidence'], expected_approval)
        atomic_install(target, raw, expected)
        if kind == 'profile':
            approvals.verify(operation, intent['approval_evidence'], expected_approval)
        receipt = dict(id=ident, verified=now().isoformat(), after_sha256=sha(raw))
        if kind == 'profile':
            receipt['approval_evidence'] = intent['approval_evidence']
        exclusive(operation / 'committed.json', encoded(receipt))
    except Exception as error:
        raise ValueError('Private-state update interrupted; operation=' + ident +
                         '. Inspect status before retry; bytes may already be committed. ' + str(error)) from error
    return dict(operation_id=ident, status='committed_verified', target=str(target))


def operation_status(state, ident):
    folder = inside(state, state / 'state-history' / valid_id(ident))
    intent = decode((folder / 'intent.json').read_bytes())
    if intent['id'] != ident:
        raise ValueError('Operation identity mismatch')
    target = inside(state, Path(intent['target']))
    if sha((folder / 'after.json').read_bytes()) != intent['after_sha256']:
        raise ValueError('Operation candidate was modified')
    if intent['before_sha256'] is not None and file_hash(folder / 'before.json') != intent['before_sha256']:
        raise ValueError('Operation backup was modified')
    current = file_hash(target)
    historical = (folder / 'committed.json').is_file()
    if historical:
        receipt = decode((folder / 'committed.json').read_bytes())
        if receipt.get('id') != ident or receipt.get('after_sha256') != intent['after_sha256']:
            raise ValueError('Operation completion receipt does not match intent')
        if intent.get('approval_evidence') is not None and receipt.get('approval_evidence') != intent['approval_evidence']:
            raise ValueError('Operation receipt approval evidence does not match intent')
    if current == intent['after_sha256']:
        status = 'committed_verified' if historical else 'committed_unverified'
    elif historical:
        status = 'changed_after_commit'
    elif current == intent['before_sha256']:
        status = 'not_committed'
    else:
        status = 'conflict'
    evidence_status = 'not_applicable'
    if intent['kind'] == 'profile':
        expected = approvals.target('profile', intent['assertions']['proposal_id'], intent['after_sha256'], target)
        evidence_status = approvals.status(folder, intent.get('approval_evidence'), expected)
    return folder, intent, dict(operation_id=ident, status=status, historical_commit_verified=historical,
                              approval_evidence_status=evidence_status)


def verify_operation(state, ident):
    with writer_lock(state):
        folder, intent, result = operation_status(state, ident)
        if intent['kind'] == 'profile' and (result['status'] == 'committed_unverified' or
                                           intent.get('approval_evidence') is not None):
            expected = approvals.target('profile', intent['assertions']['proposal_id'],
                                        intent['after_sha256'], intent['target'])
            approvals.verify(folder, intent.get('approval_evidence'), expected)
        if result['status'] == 'committed_verified':
            return dict(result, state_rewritten=False)
        if result['status'] != 'committed_unverified':
            raise ValueError('Only matching committed bytes can be verified; status=' + result['status'])
        for evidence in intent['evidence']:
            path = inside(state, Path(evidence['path']))
            if file_hash(path) != evidence['sha256']:
                raise ValueError('Saved evidence changed; reconcile before verification')
        receipt = dict(id=ident, verified=now().isoformat(), after_sha256=intent['after_sha256'],
                       recovered=True, state_rewritten=False)
        if intent.get('approval_evidence') is not None:
            receipt['approval_evidence'] = intent['approval_evidence']
        exclusive(folder / 'committed.json', encoded(receipt))
        return dict(result, status='committed_verified', state_rewritten=False)


def merge(current, patch):
    result = copy.deepcopy(current)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def propose_profile(state, patch, provenance, create=False):
    if not isinstance(patch, dict) or not isinstance(provenance, dict):
        raise ValueError('Patch and provenance must be JSON objects')
    text(provenance.get('source'), 'provenance.source')
    timestamp(provenance.get('recorded_at'))
    with writer_lock(state, initial_config=patch if create else None):
        target = plain(state / 'config.json')
        if create:
            if target.exists():
                raise ValueError('Profile already exists; do not reinitialize')
            before, config = None, {}
        else:
            config, before = profile(state)
        candidate = merge(config, patch)
        private_root(state, candidate)
        after = encoded(candidate)
        if before is not None and decode(before) == candidate:
            raise ValueError('No preference change to propose')
        ident = uuid.uuid4().hex
        parent = inside(state, state / 'profile-proposals')
        parent.mkdir(exist_ok=True)
        folder = parent / ident
        folder.mkdir()
        if before is not None:
            exclusive(folder / 'before.json', before)
        exclusive(folder / 'after.json', after)
        diff = ''.join(difflib.unified_diff((before.decode('utf-8') if before else '').splitlines(True),
            after.decode('utf-8').splitlines(True), fromfile='config.json (current)', tofile='config.json (proposed)'))
        exclusive(folder / 'proposal.json', encoded(dict(id=ident, before_sha256=sha(before) if before else None,
            after_sha256=sha(after), provenance=provenance, created=now().isoformat())))
        return dict(id=ident, status='awaiting_approval', before=config, after=candidate, diff=diff,
                    provenance=provenance)


def apply_profile(state, ident, approval, approval_reference, approval_evidence=None):
    if approval != valid_id(ident):
        raise ValueError('Approval must identify this exact preference proposal')
    text(approval_reference, 'approval_reference')
    # Validate the proposed private boundary before any initial-profile lock write.
    proposed = inside(state, state / 'profile-proposals' / ident / 'after.json')
    initial_config = decode(proposed.read_bytes())
    private_root(state, initial_config)
    with writer_lock(state, initial_config=initial_config):
        folder = inside(state, state / 'profile-proposals' / ident)
        item = decode((folder / 'proposal.json').read_bytes())
        if item['id'] != ident:
            raise ValueError('Preference proposal identity mismatch')
        raw = (folder / 'after.json').read_bytes()
        if sha(raw) != item['after_sha256']:
            raise ValueError('Preference proposal changed; approval invalid')
        candidate = decode(raw)
        private_root(state, candidate)
        target = plain(state / 'config.json')
        before = target.read_bytes() if target.exists() else None
        if (sha(before) if before is not None else None) != item['before_sha256']:
            raise ValueError('Profile changed or proposal already applied; inspect history and create a fresh proposal')
        if before is not None:
            profile(state)
        expected = approvals.target('profile', ident, item['after_sha256'], target)
        approval_raw = approvals.read(state, approval_evidence, expected)
        return commit(state, target, before, candidate, 'profile', dict(
            proposal_id=ident, approval_assertion=approval, approval_reference=approval_reference,
            provenance=item['provenance']), approval_raw=approval_raw)


# Runtime progress is not a preference. Keep the exception list deliberately small.
CHECK_IN_RUNTIME_KEYS = ('last_cycle_id', 'manual_submission_state', 'output_freshness')


def search_scope_hash(config):
    scope = copy.deepcopy(config)
    review = scope.get('review')
    if isinstance(review, dict):
        review.pop('last_broader_completed_at', None)
        check_in = review.get('check_in')
        if isinstance(check_in, dict):
            for key in CHECK_IN_RUNTIME_KEYS:
                check_in.pop(key, None)
            if not check_in:
                review.pop('check_in', None)
        if not review:
            scope.pop('review', None)
    return sha(json.dumps(scope, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8'))


def checkpoint_profile_matches(run, config, raw):
    version = run.get('scope_hash_version')
    if version is None:
        return sha(raw) == run['config_sha256']  # Never relabel legacy active runs.
    if version != 1:
        raise ValueError('Unsupported search-scope fingerprint version')
    return search_scope_hash(config) == run['search_scope_sha256']


def legacy_check_in(config):
    review = config.get('review', {})
    check_in = review.get('check_in', {}) if isinstance(review, dict) else {}
    legacy = {}
    if isinstance(check_in, dict):
        for key in ('last_cycle_id', 'manual_submission_state'):
            if check_in.get(key) is not None:
                legacy[key] = check_in[key]
    if isinstance(review, dict) and review.get('last_broader_completed_at') is not None:
        legacy['last_broader_completed_at'] = review['last_broader_completed_at']
    return legacy


def check_in_document(state):
    path = inside(state, state / 'reviews' / 'check-in-state.json')
    raw = path.read_bytes() if path.exists() else None
    doc = decode(raw) if raw is not None else dict(schema_version=1, cycles={}, events={})
    if (not isinstance(doc, dict) or doc.get('schema_version') != 1 or
            not isinstance(doc.get('cycles'), dict) or not isinstance(doc.get('events'), dict) or
            any(not isinstance(c, dict) for c in doc['cycles'].values()) or
            any(not isinstance(e, dict) for e in doc['events'].values())):
        raise ValueError('Malformed check-in state; reviewed recovery required')
    return path, raw, doc


def no_change_document(state):
    path = inside(state, state / 'reviews' / 'no-change-confirmations.json')
    raw = path.read_bytes() if path.exists() else None
    doc = decode(raw) if raw is not None else dict(schema_version=1, revision=0, confirmations={})
    if (not isinstance(doc, dict) or doc.get('schema_version') != 1 or
            type(doc.get('revision')) is not int or doc['revision'] < 0 or
            not isinstance(doc.get('confirmations'), dict) or
            any(not isinstance(c, dict) for c in doc['confirmations'].values())):
        raise ValueError('Malformed no-change history; reviewed recovery required')
    return path, raw, doc


def check_in_status(state):
    config, _ = profile(state)
    path, raw, doc = check_in_document(state)
    legacy = legacy_check_in(config) if raw is None else {}
    observations = {}
    output_events = [event for event in doc['events'].values() if event.get('action') == 'output_observed']
    for event in sorted(output_events, key=lambda e: (timestamp(e['occurred_at']), e['event_id'])):
        observation = event['output_observation']
        report = inside(state, Path(observation['report_path']))
        try:
            evidence_status = ('matches_saved_report' if file_hash(report) == observation['report_sha256']
                               else 'missing_or_changed_report')
        except OSError:
            evidence_status = 'inaccessible_report'
        observations[observation['kind']] = dict(event_id=event['event_id'], cycle_id=event['cycle_id'],
            occurred_at=event['occurred_at'], observation=copy.deepcopy(observation),
            evidence_status=evidence_status, output_freshness='must_recheck_current_output')
    confirmations_path, confirmations_raw, confirmations = no_change_document(state)
    return dict(path=str(path), exists=raw is not None, state=doc, output_observations=observations,
                no_change_confirmations=dict(path=str(confirmations_path), exists=confirmations_raw is not None,
                                             state=confirmations),
                legacy_progress=legacy, migration_required=bool(legacy))


def record_check_in(state, event):
    fields = {'event_id', 'cycle_id', 'expected_revision', 'action', 'actor',
              'reference', 'occurred_at', 'categories', 'output_observation'}
    if not isinstance(event, dict) or set(event) - fields:
        raise ValueError('Check-in events accept operational fields only, never preferences or records')
    event_id = valid_id(event.get('event_id', ''))
    cycle_id = event.get('cycle_id')
    if not isinstance(cycle_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', cycle_id):
        raise ValueError('Use a stable nonsecret cycle identifier')
    if type(event.get('expected_revision')) is not int or event['expected_revision'] < 0:
        raise ValueError('Expected cycle revision required')
    action = event.get('action')
    if action not in ('dispatched', 'selected', 'closed', 'ignored', 'broader_due', 'broader_completed', 'output_observed'):
        raise ValueError('Unsupported check-in action')
    actor = event.get('actor')
    if actor not in ('user', 'system') or (action in ('selected', 'closed') and actor != 'user'):
        raise ValueError('Selection/closure requires an actual user response reference')
    text(event.get('reference'), 'Actual event evidence reference')
    when = timestamp(event.get('occurred_at'))
    if when > now():
        raise ValueError('Check-in event cannot be in the future')
    categories = event.get('categories')
    if action == 'selected':
        if (not isinstance(categories, list) or not categories or
                any(not isinstance(c, str) or not c.strip() for c in categories) or
                len(set(categories)) != len(categories)):
            raise ValueError('Unique selected categories required')
    elif 'categories' in event:
        raise ValueError('Categories apply only to selection events')
    evidence = []
    if action == 'output_observed':
        observation = event.get('output_observation')
        if (not isinstance(observation, dict) or set(observation) != {'kind', 'report_path', 'report_sha256'}
                or observation['kind'] not in ('cv', 'website')):
            raise ValueError('Output observation requires kind, report_path and report_sha256')
        if not isinstance(observation['report_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', observation['report_sha256']):
            raise ValueError('Output report needs a SHA256 hash')
        report = inside(state, Path(text(observation['report_path'], 'Output report path')))
        if report in (state / 'config.json', state / 'reviews' / 'check-in-state.json'):
            raise ValueError('Profile/check-in state is not an output observation report')
        if not report.is_file() or report.stat().st_size == 0 or file_hash(report) != observation['report_sha256']:
            raise ValueError('Nonempty matching output observation report required')
        evidence = [dict(path=str(report), sha256=observation['report_sha256'])]
    elif 'output_observation' in event:
        raise ValueError('Output observation applies only to output_observed events')
    with writer_lock(state):
        config, _ = profile(state)
        path, before, doc = check_in_document(state)
        if before is None and legacy_check_in(config):
            raise ValueError('Legacy check-in progress needs reviewed migration; profile unchanged')
        if event_id in doc['events']:
            if doc['events'][event_id] != event:
                raise ValueError('Event ID already records different evidence')
            return dict(status='already_recorded', event_id=event_id,
                        cycle=doc['cycles'][cycle_id], state_rewritten=False)
        cycle = doc['cycles'].get(cycle_id, dict(revision=0, manual_submission_state='pending',
            selected_categories=[], broader_review_state='not_recorded'))
        if cycle.get('revision') != event['expected_revision']:
            raise ValueError('Cycle changed; inspect current revision before recording')
        if cycle.get('last_occurred_at') and when < timestamp(cycle['last_occurred_at']):
            raise ValueError('Event predates current cycle progress')
        if action == 'dispatched':
            if cycle.get('dispatched_at'):
                raise ValueError('Reminder already dispatched for this cycle')
            cycle['dispatched_at'] = event['occurred_at']
            cycle['manual_submission_state'] = 'open'
        elif action in ('selected', 'closed', 'ignored'):
            if not cycle.get('dispatched_at') or cycle.get('manual_submission_state') == 'closed':
                raise ValueError('No open dispatched check-in')
            if action == 'selected':
                cycle['selected_categories'] = categories
                cycle['manual_submission_state'] = 'open'
            else:
                cycle['manual_submission_state'] = action
        elif action == 'broader_due':
            if cycle['broader_review_state'] != 'not_recorded':
                raise ValueError('Broader review already recorded for this cycle')
            cycle['broader_review_state'] = 'due'
        elif action == 'output_observed':
            cycle.setdefault('output_observation_event_ids', {})[event['output_observation']['kind']] = event_id
        else:
            if cycle['broader_review_state'] != 'due':
                raise ValueError('Broader review must be due before completion')
            cycle['broader_review_state'] = 'completed'
            cycle['broader_completed_at'] = event['occurred_at']
        cycle.update(revision=cycle['revision'] + 1, last_event_id=event_id,
                     last_occurred_at=event['occurred_at'])
        doc['cycles'][cycle_id] = cycle
        doc['events'][event_id] = copy.deepcopy(event)
        path.parent.mkdir(exist_ok=True)
        def verify_output_evidence():
            for item in evidence:
                if file_hash(inside(state, Path(item['path']))) != item['sha256']:
                    raise ValueError('Output observation report changed before commit')
        result = commit(state, path, before, doc, 'check_in_event',
                        dict(event_id=event_id, action=action, evidence_reference=event['reference']),
                        evidence=evidence, precondition=verify_output_evidence)
        return dict(result, cycle=cycle, event_id=event_id)



def checkpoint_document(state, config):
    discovery = config.get('discovery')
    if not isinstance(discovery, dict):
        raise ValueError('Discovery settings are unresolved or malformed')
    configured = discovery.get('checkpoint_path')
    path = inside(state, Path(configured) if configured else state / 'reviews' / 'discovery-checkpoints.json')
    raw = path.read_bytes() if path.exists() else None
    document = decode(raw) if raw is not None else dict(schema_version=1, sources={}, runs={})
    if not isinstance(document, dict) or document.get('schema_version') != 1 or not isinstance(document.get('sources'), dict):
        raise ValueError('Unsupported checkpoint document; reviewed migration required')
    if not isinstance(document.setdefault('runs', {}), dict):
        raise ValueError('Invalid checkpoint runs')
    if any(not isinstance(value, dict) for value in document['sources'].values()) or any(
            not isinstance(value, dict) for value in document['runs'].values()):
        raise ValueError('Malformed source/run state; reviewed recovery required')
    return path, raw, document


def source_key(source):
    if not isinstance(source, dict) or set(source) != {'provider', 'identity', 'scope_version', 'query'}:
        raise ValueError('Source needs provider, identity, scope_version and query')
    for key, value in source.items():
        text(value, 'source.' + key)
    return sha(json.dumps(source, sort_keys=True, ensure_ascii=False).encode('utf-8'))


def positive_days(value, label, allow_zero=False):
    if type(value) is not int or value < (0 if allow_zero else 1):
        raise ValueError(label + ' needs a confirmed integer number of days')
    return value


def checkpoint_sources(state):
    """Read saved definitions verbatim; never create state, locks or history."""
    config, _ = profile(state)
    path, _, document = checkpoint_document(state, config)
    sources = []
    for key, saved in sorted(document['sources'].items()):
        sources.append(dict(source_key=key, definition=copy.deepcopy(saved),
                            active_run_ids=sorted(ident for ident, run in document['runs'].items()
                                                  if run.get('source_key') == key and run.get('status') == 'running')))
    return dict(checkpoint_path=str(path), sources=sources)


def begin_checkpoint(state, request, source_approved=False, acknowledge_new_scope=False,
                     scope_change_reference=None):
    if not source_approved:
        raise ValueError('Actual source/scope approval required before search; flag is only an assertion')
    if not isinstance(request, dict):
        raise ValueError('Search request must be a JSON object')
    with writer_lock(state):
        config, config_raw = profile(state)
        path, before, document = checkpoint_document(state, config)
        key = source_key(request['source'])
        text(request.get('cycle_id'), 'cycle_id')
        text(request.get('timezone_interpretation'), 'timezone_interpretation')
        subqueries = request.get('subqueries')
        if (not isinstance(subqueries, list) or not subqueries or
                any(not isinstance(q, str) or not q.strip() for q in subqueries) or len(set(subqueries)) != len(subqueries)):
            raise ValueError('Declare unique nonempty subqueries before search')
        end = timestamp(request['end'])
        if end > now():
            raise ValueError('Search cutoff cannot be in the future')
        source = document['sources'].get(key, {})
        related = sorted(old_key for old_key, saved in document['sources'].items()
                         if old_key != key and isinstance(saved.get('source'), dict)
                         and all(saved['source'].get(field) == request['source'][field]
                                 for field in ('provider', 'identity')))
        scope_change = None
        if key not in document['sources'] and related:
            if not acknowledge_new_scope:
                raise ValueError('New search definition for an existing provider/account. Inspect checkpoint-sources '
                                 'and reuse the saved definition, or acknowledge an intentional new scope with '
                                 '--acknowledge-new-scope and --scope-change-reference after applicable approval. '
                                 'Related source keys: ' + ', '.join(related))
            text(scope_change_reference, 'scope_change_reference')
            scope_change = dict(acknowledged=True, reference=scope_change_reference,
                                related_source_keys=related)
        if source and source.get('source') != request['source']:
            raise ValueError('Source identity mismatch; reconcile legacy checkpoint')
        if source and sorted(source.get('subqueries', [])) != sorted(subqueries):
            raise ValueError('Declared subquery scope changed; use a reviewed new scope version')
        if any(run.get('source_key') == key and run.get('status') == 'running' for run in document['runs'].values()):
            raise ValueError('This source already has an active run; inspect/fail it before restarting')
        previous = source.get('last_successful_cutoff')
        discovery = config.get('discovery', {})
        if discovery.get('window_policy', 'per_source_last_successful_cutoff_minus_overlap') != 'per_source_last_successful_cutoff_minus_overlap':
            raise ValueError('Unsupported search window policy; reviewed adapter required')
        overlap = positive_days(discovery.get('overlap_days'), 'overlap_days', allow_zero=True)
        if previous:
            cutoff = timestamp(previous)
            if end <= cutoff:
                raise ValueError('Fixed cutoff must be later than successful coverage')
            start = cutoff - dt.timedelta(days=overlap)
        else:
            days = positive_days(discovery.get('initial_window_days'), 'initial_window_days')
            start = end - dt.timedelta(days=days)
            if source.get('initial_coverage_start'):
                start = min(start, timestamp(source['initial_coverage_start']))
        ident = uuid.uuid4().hex
        run = dict(id=ident, source_key=key, cycle_id=request['cycle_id'], status='running',
            window_start=start.isoformat(), window_end=end.isoformat(), created=now().isoformat(),
            previous_successful_cutoff=previous, config_sha256=sha(config_raw),
            scope_hash_version=1, search_scope_sha256=search_scope_hash(config),
            timezone_interpretation=request['timezone_interpretation'], subqueries=subqueries,
            source_approval_assertion=True)
        if scope_change is not None:
            run['scope_change_assertion'] = scope_change
        document['runs'][ident] = run
        document['sources'][key] = {**source, 'source':request['source'],
                                   'subqueries':subqueries, 'last_attempt_run_id':ident}
        if not previous:
            document['sources'][key]['initial_coverage_start'] = start.isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        details = dict(source_approval_assertion=True)
        if scope_change is not None:
            details['scope_change_assertion'] = scope_change
        result = commit(state, path, before, document, 'checkpoint_begin', details)
        return dict(result, run=run)


def finish_checkpoint(state, ident, completion=None, failure=None):
    if ((completion is None) == (failure is None) or
            (completion is not None and not isinstance(completion, dict)) or
            (failure is not None and not isinstance(failure, dict))):
        raise ValueError('Provide exactly one completion or failure JSON object')
    with writer_lock(state):
        config, config_raw = profile(state)
        path, before, document = checkpoint_document(state, config)
        run = document['runs'].get(valid_id(ident))
        if not run or run.get('id') != ident or run.get('status') != 'running':
            raise ValueError('Run is missing or already closed; inspect state before any retry')
        key = run['source_key']
        source = document['sources'][key]
        evidence = []
        if failure is not None:
            if failure.get('outcome') not in ('failed', 'partial', 'unauthorized', 'unavailable',
                                              'rate_limited', 'interrupted', 'save_failed'):
                raise ValueError('Unsupported failure outcome')
            text(failure.get('reason'), 'failure.reason (minimal, no raw correspondence)')
            run.update(status=failure['outcome'], failure=failure, completed=now().isoformat())
        else:
            if not checkpoint_profile_matches(run, config, config_raw):
                raise ValueError('Profile changed during search; retain cutoff and reconcile scope')
            if source.get('last_successful_cutoff') != run['previous_successful_cutoff']:
                raise ValueError('Successful cutoff changed during run')
            for field in ('window_start', 'window_end'):
                if completion.get(field) != run[field]:
                    raise ValueError('Completion coverage must match fixed ' + field)
            if timestamp(run['window_end']) > now():
                raise ValueError('Search cutoff is in the future')
            if completion.get('results_durably_saved') is not True:
                raise ValueError('Durable results assertion required; no cutoff advanced')
            pagination = completion.get('pagination')
            if not isinstance(pagination, list):
                raise ValueError('Per-subquery pagination evidence required')
            covered = []
            for page in pagination:
                if (not isinstance(page, dict) or page.get('exhausted') is not True or
                        type(page.get('pages')) is not int or page['pages'] < 1):
                    raise ValueError('All pages must be covered for every declared subquery')
                covered.append(text(page.get('query_id'), 'pagination.query_id'))
            if sorted(covered) != sorted(run['subqueries']):
                raise ValueError('Complete every declared subquery exactly once')
            count = completion.get('result_count')
            if type(count) is not int or count < 0:
                raise ValueError('result_count must be a nonnegative integer')
            paths = completion.get('result_paths')
            if not isinstance(paths, list) or (count > 0 and not paths):
                raise ValueError('Nonzero results need durable result_paths')
            for name in [completion.get('report_path'), *paths]:
                report = inside(state, Path(text(name, 'saved report/result path')))
                if report in (path, state / 'config.json'):
                    raise ValueError('Profile/checkpoint state is not a discovery report')
                if not report.is_file() or report.stat().st_size == 0:
                    raise ValueError('Nonempty saved report/results required; cutoff retained')
                evidence.append(dict(path=str(report), sha256=file_hash(report)))
            run.update(status='complete', completed=now().isoformat(), completion=completion,
                       evidence=evidence)
            source.update(last_successful_cutoff=run['window_end'], last_successful_run_id=ident,
                          coverage_start=run['window_start'], coverage_end=run['window_end'])
            if document.get('note') == 'No successful discovery searches recorded; first-search look-back remains pending.':
                del document['note']
        def still_current():
            if completion is not None:
                current_config, current_raw = profile(state)
                if not checkpoint_profile_matches(run, current_config, current_raw):
                    raise ValueError('Profile changed before checkpoint save')
                for item in evidence:
                    if file_hash(inside(state, Path(item['path']))) != item['sha256']:
                        raise ValueError('Saved evidence changed before checkpoint save')
        result = commit(state, path, before, document, 'checkpoint_finish',
            dict(run_id=ident, outcome=run['status'], coverage_assertions=completion is not None),
            evidence=evidence, precondition=still_current)
        return dict(result, run=run, last_successful_cutoff=source.get('last_successful_cutoff'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('profile-propose')
    p.add_argument('state', type=Path); p.add_argument('patch', type=Path); p.add_argument('provenance', type=Path)
    p.add_argument('--create', action='store_true')
    p = sub.add_parser('profile-apply')
    p.add_argument('state', type=Path); p.add_argument('id'); p.add_argument('--approval', required=True)
    p.add_argument('--approval-reference', required=True)
    p.add_argument('--approval-evidence', type=Path, required=True)
    p = sub.add_parser('checkpoint-begin')
    p.add_argument('state', type=Path); p.add_argument('request', type=Path)
    p.add_argument('--source-approved', action='store_true')
    p.add_argument('--acknowledge-new-scope', action='store_true')
    p.add_argument('--scope-change-reference')
    p = sub.add_parser('checkpoint-sources'); p.add_argument('state', type=Path)
    for name in ('checkpoint-complete', 'checkpoint-fail'):
        p = sub.add_parser(name); p.add_argument('state', type=Path); p.add_argument('id'); p.add_argument('input', type=Path)
    for name in ('status', 'verify'):
        p = sub.add_parser(name); p.add_argument('state', type=Path); p.add_argument('id')
    p = sub.add_parser('check-in-status'); p.add_argument('state', type=Path)
    p = sub.add_parser('check-in-record'); p.add_argument('state', type=Path); p.add_argument('event', type=Path)
    args = parser.parse_args()
    state = plain(args.state)
    if not state.is_dir():
        raise ValueError('Explicit authorized private state directory must already exist')
    if args.command == 'profile-propose':
        result = propose_profile(state, decode(args.patch.read_bytes()), decode(args.provenance.read_bytes()), args.create)
    elif args.command == 'profile-apply':
        result = apply_profile(state, args.id, args.approval, args.approval_reference, args.approval_evidence)
    elif args.command == 'checkpoint-begin':
        result = begin_checkpoint(state, decode(args.request.read_bytes()), args.source_approved,
                                  args.acknowledge_new_scope, args.scope_change_reference)
    elif args.command == 'checkpoint-sources':
        result = checkpoint_sources(state)
    elif args.command == 'checkpoint-complete':
        result = finish_checkpoint(state, args.id, completion=decode(args.input.read_bytes()))
    elif args.command == 'checkpoint-fail':
        result = finish_checkpoint(state, args.id, failure=decode(args.input.read_bytes()))
    elif args.command == 'check-in-status':
        result = check_in_status(state)
    elif args.command == 'check-in-record':
        result = record_check_in(state, decode(args.event.read_bytes()))
    elif args.command == 'status':
        result = operation_status(state, args.id)[2]
    else:
        result = verify_operation(state, args.id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
