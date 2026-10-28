"""Private proposal staging. Commands never infer human approval from silence.

propose STATE DATA FILE CANDIDATE RSCRIPT [--r-library PATH]
apply STATE PROPOSAL_ID --approval PROPOSAL_ID RSCRIPT [--r-library PATH]
list STATE
remember STATE INPUT_JSON
event STATE PENDING_ID EVENT_JSON
status STATE PROPOSAL_ID
verify STATE PROPOSAL_ID RSCRIPT [--r-library PATH]
inspect DATA

The host/skill must obtain actual human approval before calling apply. A CLI
argument is an operator assertion, not authentication or an access-control boundary.
"""
import argparse
from collections import Counter
import re
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import importlib.util

_approval_spec = importlib.util.spec_from_file_location('academic_approval_evidence',
    Path(__file__).with_name('approval_evidence.py'))
approvals = importlib.util.module_from_spec(_approval_spec)
_approval_spec.loader.exec_module(approvals)

_state_spec = importlib.util.spec_from_file_location('academic_pending_state',
    Path(__file__).with_name('private_state.py'))
pending_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(pending_state)

REQUIRED_FILES = tuple(n + '.yml' for n in (
    'abstracts', 'appointments', 'certifications', 'education', 'grants',
    'honors', 'memberships', 'mentoring', 'projects', 'service', 'talks',
    'teaching', 'training'))
FILES = REQUIRED_FILES + ('media.yml',)


def source_files(root):
    return REQUIRED_FILES + (('media.yml',) if (root / 'media.yml').exists() else ())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)


def validate(root, rscript, library, bibliography=None):
    env = os.environ.copy()
    if library:
        env['R_LIBS_USER'] = library
    command = [rscript, str(Path(__file__).with_name('validate.R')), str(root)]
    # Never let live validation discover a default absent from reviewed staging.
    command.append(str(root / bibliography) if bibliography else '--no-bibliography')
    result = subprocess.run(command,
                            capture_output=True, text=True, env=env)
    if 'AR_VALIDATION_V1' not in result.stdout.splitlines():
        raise ValueError('Validation failed: complete diagnostic report unavailable.\n' + result.stdout + result.stderr)
    diagnostics = validation_errors(result.stdout)
    if result.returncode not in (0, 1) or (result.returncode == 1 and not diagnostics):
        raise ValueError('Validation failed.\n' + validation_display(result.stdout) + result.stderr)
    if any(error['severity'] == 'fatal' for error in diagnostics):
        raise ValueError('Validation failed: parser/structure failure.\n' + validation_display(result.stdout))
    if result.returncode == 0 and diagnostics:
        raise ValueError('Validation failed: inconsistent diagnostic exit status')
    return result.stdout


def validation_errors(output):
    lines = output.splitlines()
    machine = [line for line in lines if line.startswith('AR_')]
    if not machine:
        if any(line.strip().startswith('ERROR:') for line in lines):
            raise ValueError('Validation failed: unstructured errors cannot be compared safely')
        return []
    if machine[0] != 'AR_VALIDATION_V1' or not machine[-1].startswith('AR_VALIDATION_END\t'):
        raise ValueError('Validation failed: incomplete diagnostic report')
    try:
        count = int(machine[-1].split('\t')[1])
        errors = []
        for line in machine[1:-1]:
            tag, severity, message_hex, context = line.split('\t')
            if tag != 'AR_ERROR' or severity not in ('record', 'fatal') or not context:
                raise ValueError()
            message = bytes.fromhex(message_hex).decode('utf-8')
            if not message:
                raise ValueError()
            # Only the validator's leading display row is positional. Keep the file,
            # diagnostic detail and full serialized affected record in the identity.
            stable_message = message
            if severity == 'record':
                tables = '|'.join(re.escape(Path(name).stem) for name in FILES)
                stable_message = re.sub(r'^(' + tables + r')\[[1-9][0-9]*\](?= )',
                                        r'\1[*]', message, count=1)
            identity = hashlib.sha256((severity + '\0' + stable_message + '\0' + context).encode('utf-8')).hexdigest()
            errors.append(dict(identity=identity, severity=severity, message=message))
        if count != len(errors):
            raise ValueError()
        human_errors = {line.strip()[6:].strip() for line in lines if line.strip().startswith('ERROR:')}
        if human_errors != {error['message'].strip() for error in errors}:
            raise ValueError()
        return errors
    except (ValueError, IndexError, UnicodeError) as error:
        raise ValueError('Validation failed: malformed diagnostic report') from error


def validation_display(output):
    return '\n'.join(line for line in output.splitlines() if not line.startswith('AR_')) + '\n'


def compare_validation_errors(baseline, current, exact=False):
    previous = validation_errors(baseline)
    actual = validation_errors(current)
    if any(e['severity'] == 'fatal' for e in previous + actual):
        raise ValueError('Validation failed: parser/structure errors block proposals')
    before = Counter(e['identity'] for e in previous)
    after = Counter(e['identity'] for e in actual)
    if any(count > before[identity] for identity, count in after.items()) or (exact and after != before):
        raise ValueError('Validation failed: ' + ('reviewed errors changed; renewed review required' if exact else 'new or changed errors; proposal blocked') +
                         '\n' + validation_display(current))
    retained = after.copy()
    resolved = []
    for error in previous:
        if retained[error['identity']]:
            retained[error['identity']] -= 1
        else:
            resolved.append(error['message'])
    return dict(remaining_errors=[e['message'] for e in actual], resolved_errors=resolved)


def check_paths(state, root, project_root):
    if root != project_root and project_root not in root.parents:
        raise ValueError('data_root must be inside configured project_root')
    if state == project_root or project_root in state.parents:
        raise ValueError('Private state must be outside configured project_root')
    for name in source_files(root):
        path = root / name
        if not path.is_file() or path.is_symlink() or path.resolve().parent != root:
            raise ValueError('Missing or redirected source: ' + name)


def profile(state, root=None):
    config = json.loads((state / 'config.json').read_text(encoding='utf-8'))
    for key in ('data_root', 'project_root'):
        if not isinstance(config.get(key), str) or not Path(config[key]).is_absolute():
            raise ValueError(key + ' must be an explicit absolute path in the profile')
    configured = Path(config['data_root']).resolve()
    project_root = Path(config['project_root']).resolve(strict=True)
    check_paths(state, configured, project_root)
    if root is not None and root != configured:
        raise ValueError('Requested data root differs from the saved profile')
    approved = config.get('approved_files')
    if (not isinstance(approved, list) or not approved or
            any(name not in FILES for name in approved) or len(set(approved)) != len(approved)):
        raise ValueError('Profile needs an explicit approved_files subset of the supported adapter')
    if config.get('approval_policy') != 'per_change':
        raise ValueError('This updater supports only confirmed per_change approval')
    bibliography = config.get('bibliography_file')
    if bibliography and (not isinstance(bibliography, str) or
            Path(bibliography).name != bibliography or '/' in bibliography or '\\' in bibliography):
        raise ValueError('bibliography_file must name a file in the configured data folder')
    if bibliography and (not (configured / bibliography).is_file() or
                         (configured / bibliography).resolve().parent != configured):
        raise ValueError('Configured bibliography is missing or redirected; resolve before validation')
    return config, configured



def atomic_write(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.academic-records-',
                                         suffix='.tmp', delete=False) as out:
            temporary = Path(out.name)
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def valid_id(value):
    if len(value) != 32 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Invalid record ID')
    return value


def read_proposal(state, ident):
    folder = state / 'proposals' / valid_id(ident)
    item = json.loads((folder / 'proposal.json').read_text(encoding='utf-8'))
    if item['id'] != ident or item['file'] not in FILES:
        raise ValueError('Invalid proposal metadata')
    receipt = folder / 'applied.json'
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        if 'validated_bibliography_sha256' in saved:
            item['bibliography_sha256'] = saved['validated_bibliography_sha256']
    return folder, item


def snapshot_changes(root, item, bibliography, check_bibliography=True):
    """Compare current sources with this proposal's approved post-save snapshot."""
    changed = []
    if set(item['before']) != set(source_files(root)):
        changed.append('<source-file-layout>')
    for name, previous in item['before'].items():
        path = root / name
        expected = item['candidate_sha256'] if name == item['file'] else previous
        if (not path.is_file() or path.is_symlink() or
                path.resolve().parent != root or digest(path) != expected):
            changed.append(name)
    if bibliography != item.get('bibliography_file'):
        changed.append('<bibliography-configuration>')
    if bibliography and check_bibliography:
        path = root / bibliography
        if (not path.is_file() or path.is_symlink() or
                path.resolve().parent != root or
                digest(path) != item.get('bibliography_sha256')):
            changed.append(bibliography)
    return changed


def require_snapshot(root, item, bibliography, check_bibliography=True):
    changed = snapshot_changes(root, item, bibliography, check_bibliography)
    if changed:
        raise ValueError('Snapshot changed; no completion receipt written: ' + ', '.join(changed))


def validation_warnings(output):
    return sorted(set(line.strip() for line in output.splitlines()
                      if line.strip().startswith('WARNING:')))


def validate_current_bibliography(root, item, rscript, library, candidate_root=None):
    """Validate a stable bibliography generation, retaining the exact approved YAML.

    Candidate validation uses a disposable copy, never changes approved staging.
    Three attempts bound concurrent auto-export retries; errors on a stable source
    and changed warnings require review, not silent acceptance.
    """
    bibliography = item.get('bibliography_file')
    bib = root / bibliography if bibliography else None
    for _ in range(3):
        before = digest(bib) if bib else None
        try:
            if candidate_root is None:
                checked = validate(root, rscript, library, bibliography)
            else:
                with tempfile.TemporaryDirectory(prefix='bibliography-check-',
                                                 dir=candidate_root.parent) as tmp:
                    scratch = Path(tmp)
                    for name in item['before']:
                        shutil.copyfile(candidate_root / name, scratch / name)
                    if bib:
                        shutil.copyfile(bib, scratch / bibliography)
                        if digest(scratch / bibliography) != before:
                            continue
                    checked = validate(scratch, rscript, library, bibliography)
        except ValueError:
            if bib and digest(bib) != before:
                continue
            raise
        if bib and digest(bib) != before:
            continue
        compare_validation_errors(item['proposed_validation'], checked, exact=True)
        expected = validation_warnings(item['proposed_validation'])
        actual = validation_warnings(checked)
        if actual != expected:
            raise ValueError('Validation warnings changed; renewed review and approval required. '
                             'Previously reviewed: ' + json.dumps(expected) +
                             '; current: ' + json.dumps(actual))
        return checked, before
    raise ValueError('Snapshot changed: bibliography kept changing during validation; '
                     'no stable validation result available')


def current_scope(state, item):
    config, root = profile(state, Path(item['root']).resolve())
    if item['file'] not in config['approved_files']:
        raise ValueError('Proposal target is not approved in the current profile')
    if config.get('bibliography_file') != item.get('bibliography_file'):
        raise ValueError('Bibliography configuration changed; reconcile before verification')
    return config, root


def approval_target(item):
    return approvals.target('yaml', item['id'], item['candidate_sha256'], Path(item['root']) / item['file'])


def approval_reference(folder):
    receipt = folder / 'applied.json'
    if receipt.is_file():
        return json.loads(receipt.read_text(encoding='utf-8')).get('approval_evidence')
    attempts = sorted((folder / 'attempts').glob('*.json'))
    if attempts:
        return json.loads(attempts[-1].read_text(encoding='utf-8')).get('approval_evidence')
    return None



def confirmed_target_write(attempt, item):
    return (attempt.get('write_evidence_version') == 1 and
            attempt.get('target_write_confirmed') is True and
            attempt.get('target_written_sha256') == item['candidate_sha256'])


def write_attribution(folder, item):
    attempts = [json.loads(path.read_text(encoding='utf-8'))
                for path in sorted((folder / 'attempts').glob('*.json'))]
    failed = any(a.get('status') == 'failed_before_write' and
                 not confirmed_target_write(a, item) for a in attempts)
    receipt = folder / 'applied.json'
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        if saved.get('recovered') and failed:
            return 'contradictory_recovery_history'
        if saved.get('recovered') and not any(confirmed_target_write(a, item) for a in attempts):
            return 'legacy_recovery_unattributed'
        return 'verified_receipt'
    if failed:
        return 'known_failed_before_write'
    if any(confirmed_target_write(a, item) for a in attempts):
        return 'confirmed_target_write'
    return 'unconfirmed'



def proposal_details(state, ident, config=None):
    folder, item = read_proposal(state, ident)
    root = Path(item['root']).resolve()
    bibliography = config.get('bibliography_file') if config is not None else item.get('bibliography_file')
    changed = snapshot_changes(root, item, bibliography)
    return dict(id=ident, status=proposal_status(state, ident),
                approval_evidence_status=approvals.status(folder, approval_reference(folder), approval_target(item)),
                historical_save_verified=((folder / 'applied.json').is_file() and
                                          write_attribution(folder, item) == 'verified_receipt'),
                write_attribution=write_attribution(folder, item),
                current_snapshot_matches=not changed, changed_files=changed,
                target_currently_approved=(item['file'] in config['approved_files']) if config is not None else None)


def proposal_status(state, ident):
    folder, item = read_proposal(state, ident)
    target = Path(item['root']).resolve() / item['file']
    attempts = sorted((folder / 'attempts').glob('*.json'))
    receipt = folder / 'applied.json'
    attribution = write_attribution(folder, item)
    if attribution == 'contradictory_recovery_history':
        return 'conflict'
    if attribution == 'legacy_recovery_unattributed':
        return 'legacy_recovery_unattributed'
    if attribution == 'known_failed_before_write':
        return 'failed_before_write'
    current = digest(target) if target.is_file() else None
    if current == item['candidate_sha256']:
        return 'verified_saved' if receipt.exists() else 'saved_unverified'
    if receipt.exists():
        # A receipt verifies a historical save, not every subsequent edit.
        return 'changed_after_save'
    if current == item['before'][item['file']]:
        if attempts:
            return 'conflict' if attribution == 'confirmed_target_write' else 'failed_before_write'
        if set(item['before']) != set(source_files(Path(item['root']))):
            return 'stale'
        for name, previous in item['before'].items():
            path = Path(item['root']) / name
            if not path.is_file() or digest(path) != previous:
                return 'stale'
        return 'awaiting_approval'
    return 'conflict'


def revisit_condition(value):
    date, trigger = value.get('revisit_on'), value.get('revisit_trigger')
    if (date is None) == (trigger is None):
        raise ValueError('Deferred item needs exactly one revisit_on or revisit_trigger')
    if date is not None:
        if not isinstance(date, str):
            raise ValueError('revisit_on must be an ISO timestamp with timezone')
        parsed = datetime.datetime.fromisoformat(date.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('revisit_on needs an explicit timezone, not a guessed date boundary')
    elif not isinstance(trigger, str) or not trigger.strip() or trigger != trigger.strip():
        raise ValueError('revisit_trigger must be a nonblank exact named condition')


def revisit_context(triggers, reference):
    if not isinstance(triggers, (list, tuple, set)):
        raise ValueError('Named triggers must be a collection of exact condition names')
    if triggers and (not isinstance(reference, str) or not reference.strip()):
        raise ValueError('Named triggers require an actual condition/source reference')
    if any(not isinstance(t, str) or not t.strip() for t in triggers):
        raise ValueError('Invalid named trigger')
    return triggers


def pending_readiness(item, triggers=()):
    if not isinstance(triggers, (list, tuple, set)):
        raise ValueError('Named triggers must be a collection of exact condition names')
    item['questions_to_ask'] = []
    if item['status'] != 'deferred':
        item['revisit_status'] = 'not_deferred'
        if item['status'] in ('needs_information', 'needs_review'):
            item['questions_to_ask'] = item.get('questions', [])
        return item
    revisit_condition(item)
    if not isinstance(item.get('deferral_id'), str) or len(item['deferral_id']) != 32:
        raise ValueError('Deferred history lacks a structured deferral ID; reviewed migration required')
    if item.get('revisit_offered_at'):
        item['revisit_status'] = 'already_offered'
        return item
    if item.get('revisit_on') is not None:
        cutoff = datetime.datetime.fromisoformat(item['revisit_on'].replace('Z', '+00:00'))
        due = datetime.datetime.fromisoformat(now()) >= cutoff
        item['revisit_status'] = 'eligible' if due else 'waiting_for_date'
    else:
        due = item['revisit_trigger'] in triggers
        item['revisit_status'] = 'eligible' if due else 'waiting_for_trigger'
    if due:
        item['questions_to_ask'] = item.get('questions', [])
    return item


def read_pending(state, ident, triggers=()):
    path = state / 'pending' / (valid_id(ident) + '.json')
    item = json.loads(path.read_text(encoding='utf-8'))
    if item['id'] != ident:
        raise ValueError('Pending ID mismatch')
    for path in sorted((state / 'events' / ident).glob('*.json')):
        event = json.loads(path.read_text(encoding='utf-8'))
        if event.get('event_type') == 'revisit_offered':
            if (item['status'] != 'deferred' or event.get('deferral_id') != item.get('deferral_id') or
                    item.get('revisit_offered_at')):
                item.setdefault('ignored_revisit_events', []).append(path.name)
                continue
            for key in ('revisit_offered_at', 'revisit_offered_cycle_id', 'revisit_offered_reference'):
                item[key] = event[key]
            item['updated'] = event['created']
            continue
        if (item['status'] in ('applied', 'rejected', 'superseded') and
                event['status'] != item['status']):
            item.setdefault('ignored_reopen_events', []).append(path.name)
            continue
        item['status'] = event['status']
        item['updated'] = event['created']
        if 'facts' in event:
            item['facts'] = {**item['facts'], **event['facts']}
        for key in ('missing_fields', 'questions', 'proposal_id', 'note', 'revisit_on',
                    'revisit_trigger', 'deferral_id', 'deferral_reference', 'revisit_offered_at',
                    'revisit_offered_cycle_id', 'revisit_offered_reference', 'resume_reference'):
            if key in event:
                item[key] = event[key]
    if item.get('proposal_id'):
        actual = proposal_status(state, item['proposal_id'])
        item['proposal_status'] = actual
        details = proposal_details(state, item['proposal_id'])
        if item['status'] not in ('applied', 'rejected', 'superseded'):
            if details['historical_save_verified']:
                item['status'] = 'applied'
            elif actual == 'saved_unverified' and item['status'] != 'deferred':
                item['status'] = 'saved_unverified'
            elif actual in ('failed_before_write', 'conflict', 'stale', 'legacy_recovery_unattributed') and item['status'] != 'deferred':
                item['status'] = 'needs_review'
        if actual == 'legacy_recovery_unattributed':
            item['historical_reconciliation_required'] = True
        item['historical_save_verified'] = details['historical_save_verified']
        item['current_snapshot_matches'] = details['current_snapshot_matches']
        item['changed_files'] = details['changed_files']
        item['approval_evidence_status'] = details['approval_evidence_status']
    return pending_readiness(item, triggers)


def event_pending(state, ident, incoming):
    with pending_state.writer_lock(state):
        return event_pending_locked(state, ident, incoming)


def event_pending_locked(state, ident, incoming):
    current = read_pending(state, ident)
    allowed = {'needs_information', 'awaiting_approval', 'rejected', 'superseded', 'applied', 'deferred'}
    if not isinstance(incoming, dict) or incoming.get('status') not in allowed:
        raise ValueError('Event needs a supported status')
    if current['status'] in ('rejected', 'superseded', 'applied') and incoming['status'] != current['status']:
        raise ValueError('Terminal item cannot be reopened; create a new linked candidate')
    event = {key: incoming[key] for key in
             ('status', 'facts', 'missing_fields', 'questions', 'proposal_id', 'note',
              'revisit_on', 'revisit_trigger', 'deferral_reference', 'resume_reference') if key in incoming}
    if event['status'] == 'deferred':
        revisit_condition(event)
        if not isinstance(event.get('deferral_reference'), str) or not event['deferral_reference'].strip():
            raise ValueError('Deferral needs a reference to the actual user deferral/rescheduling decision')
        event.update(revisit_on=event.get('revisit_on'), revisit_trigger=event.get('revisit_trigger'),
                     deferral_id=uuid.uuid4().hex, revisit_offered_at=None,
                     revisit_offered_cycle_id=None, revisit_offered_reference=None)
    elif any(key in event for key in ('revisit_on', 'revisit_trigger', 'deferral_reference')):
        raise ValueError('Revisit conditions belong only to a deferred event')
    if current['status'] == 'deferred' and event['status'] in ('needs_information', 'awaiting_approval'):
        if not isinstance(event.get('resume_reference'), str) or not event['resume_reference'].strip():
            raise ValueError('Resuming deferred questions requires an actual user-response/request reference')
    if 'facts' in event and not isinstance(event['facts'], dict):
        raise ValueError('Event facts must be an object')
    for key in ('missing_fields', 'questions'):
        if key in event and not isinstance(event[key], list):
            raise ValueError('Event questions/missing_fields must be lists')
    proposed_id = event.get('proposal_id', current.get('proposal_id'))
    if proposed_id:
        read_proposal(state, proposed_id)
        event['proposal_id'] = proposed_id
    if event['status'] == 'awaiting_approval':
        if not proposed_id:
            raise ValueError('Complete pending item must link an actual proposal')
        if event.get('missing_fields', current['missing_fields']) or event.get('questions', current['questions']):
            raise ValueError('Resolve missing fields/questions before awaiting approval')
    if event['status'] == 'applied':
        if not proposed_id or proposal_status(state, proposed_id) not in ('verified_saved', 'changed_after_save'):
            raise ValueError('Cannot mark applied without a verified proposal receipt')
    append_pending_event(state, ident, event)
    return read_pending(state, ident)


def append_pending_event(state, ident, event):
    event.update(id=uuid.uuid4().hex, pending_id=valid_id(ident), created=now())
    directory = pending_state.inside(state, state / 'events' / ident)
    directory.mkdir(parents=True, exist_ok=True)
    # Time-ordered filenames allow deterministic replay without rewriting history.
    filename = now().replace(':', '').replace('.', '') + '-' + event['id'] + '.json'
    write_json(directory / filename, event)


def offer_revisit(state, ident, cycle_id, offer_reference, triggers=(), trigger_reference=None):
    revisit_context(triggers, trigger_reference)
    for value in (cycle_id, offer_reference):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Revisit offer needs cycle ID and reference to the actual offered question')
    with pending_state.writer_lock(state):
        item = read_pending(state, ident, triggers)
        if item['status'] != 'deferred' or item['revisit_status'] != 'eligible':
            raise ValueError('Deferred item is not eligible or revisit was already offered')
        event = dict(status='deferred', event_type='revisit_offered', deferral_id=item['deferral_id'],
            revisit_offered_at=now(), revisit_offered_cycle_id=cycle_id,
            revisit_offered_reference=offer_reference, matched_trigger_reference=trigger_reference)
        append_pending_event(state, ident, event)
        return read_pending(state, ident, triggers)


def verify_saved(state, ident, rscript, library):
    folder, item = read_proposal(state, ident)
    config, root = current_scope(state, item)
    outcome = proposal_status(state, ident)
    if outcome == 'verified_saved':
        reference = approval_reference(folder)
        if reference is not None:
            approvals.verify(folder, reference, approval_target(item))
        require_snapshot(root, item, config.get('bibliography_file'))
        return dict(proposal_details(state, ident, config), record_rewritten=False,
                    validation_run=False)
    if outcome != 'saved_unverified':
        raise ValueError('Verification requires saved_unverified; current status=' + outcome)
    attempts = [json.loads(path.read_text(encoding='utf-8'))
                for path in (folder / 'attempts').glob('*.json')]
    if not attempts or not all(attempt.get('approval_assertion') == ident for attempt in attempts):
        raise ValueError('Missing approved apply attempt; reconcile manually')
    if not all(confirmed_target_write(attempt, item) for attempt in attempts):
        raise ValueError('No confirmed target write for this proposal; matching bytes alone cannot establish attribution. Reconcile manually without creating a recovery receipt.')
    reference = attempts[0].get('approval_evidence')
    if any(attempt.get('approval_evidence') != reference for attempt in attempts):
        raise ValueError('Inconsistent approval evidence across attempts; reconcile manually')
    approvals.verify(folder, reference, approval_target(item))
    backup = folder / 'backup' / item['file']
    if not backup.is_file() or digest(backup) != item['before'][item['file']]:
        raise ValueError('Original verified backup unavailable; reconcile manually')
    bibliography = config.get('bibliography_file')
    if bibliography != item.get('bibliography_file'):
        raise ValueError('Bibliography configuration changed; reconcile before verification')
    require_snapshot(root, item, bibliography, check_bibliography=False)
    checked, validated_bib = validate_current_bibliography(root, item, rscript, library)
    config, root = current_scope(state, item)
    require_snapshot(root, item, config.get('bibliography_file'), check_bibliography=False)
    approvals.verify(folder, reference, approval_target(item))
    write_json(folder / 'applied.json', dict(approval_assertion=ident,
        approval_evidence=reference,
        verified=now(), recovered=True, record_rewritten=False,
        backup=str(backup.parent), validation=checked,
        validated_bibliography_sha256=validated_bib))
    return {'id': ident, 'status': 'verified_saved', 'record_rewritten': False,
            'backup': str(backup.parent)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('propose')
    for name in ('state', 'data', 'file', 'candidate', 'rscript'):
        p.add_argument(name)
    p.add_argument('--r-library')
    p = sub.add_parser('apply')
    p.add_argument('state'); p.add_argument('id')
    p.add_argument('--approval', required=True)
    p.add_argument('--approval-evidence', required=True, type=Path)
    p.add_argument('rscript'); p.add_argument('--r-library')
    p = sub.add_parser('list'); p.add_argument('state')
    p.add_argument('--trigger', action='append', default=[]); p.add_argument('--trigger-reference')
    p = sub.add_parser('offer-revisit'); p.add_argument('state'); p.add_argument('id')
    p.add_argument('--cycle-id', required=True); p.add_argument('--offer-reference', required=True)
    p.add_argument('--trigger', action='append', default=[]); p.add_argument('--trigger-reference')
    p = sub.add_parser('remember'); p.add_argument('state'); p.add_argument('input')
    p = sub.add_parser('event'); p.add_argument('state'); p.add_argument('id'); p.add_argument('input')
    p = sub.add_parser('status'); p.add_argument('state'); p.add_argument('id')
    p = sub.add_parser('inspect'); p.add_argument('data')
    p = sub.add_parser('verify'); p.add_argument('state'); p.add_argument('id'); p.add_argument('rscript')
    p.add_argument('--r-library')
    args = parser.parse_args()
    if args.command == 'inspect':
        root = Path(args.data).resolve()
        missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
        print(json.dumps({'adapter': 'academic-yaml-13', 'data_root': str(root),
                          'supported_file_layout': not missing, 'missing_files': missing,
                          'optional_files_present': [n for n in FILES if n not in REQUIRED_FILES and (root / n).is_file()],
                          'next_step': 'Inspect consumers and validate existing records before proposals' if not missing
                          else 'Unsupported layout: report required adapter/consumer work; do not create empty files'}, indent=2))
        return
    state = Path(args.state).resolve()
    if args.command == 'verify':
        print(json.dumps(verify_saved(state, args.id, args.rscript, args.r_library)))
        return
    if args.command == 'event':
        profile(state)
        incoming = json.loads(Path(args.input).read_text(encoding='utf-8'))
        print(json.dumps(event_pending(state, args.id, incoming), ensure_ascii=False, indent=2))
        return
    if args.command == 'offer-revisit':
        profile(state)
        print(json.dumps(offer_revisit(state, args.id, args.cycle_id, args.offer_reference,
            args.trigger, args.trigger_reference), ensure_ascii=False, indent=2))
        return
    if args.command == 'status':
        config, _ = profile(state)
        print(json.dumps(proposal_details(state, args.id, config)))
        return
    if args.command == 'remember':
        item = json.loads(Path(args.input).read_text(encoding='utf-8'))
        config, root = profile(state)
        required = {'kind', 'facts', 'missing_fields', 'questions', 'sources'}
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError('Pending item needs kind, facts, missing_fields, questions, sources')
        if not isinstance(item['facts'], dict) or any(not isinstance(item[k], list)
                for k in ('missing_fields', 'questions', 'sources')):
            raise ValueError('Invalid pending item fields')
        if not item['missing_fields'] or not item['questions']:
            raise ValueError('Incomplete candidates need missing fields and focused questions')
        item = {k: item[k] for k in required}
        item.update(id=uuid.uuid4().hex, status='needs_information',
                    created=datetime.datetime.now(datetime.timezone.utc).isoformat())
        pending = state / 'pending'
        pending.mkdir(parents=True, exist_ok=True)
        write_json(pending / (item['id'] + '.json'), item)
        print(json.dumps(item, ensure_ascii=False, indent=2))
        return
    if args.command == 'list':
        config, _ = profile(state)
        triggers = revisit_context(args.trigger, args.trigger_reference)
        for file in sorted(state.glob('pending/*.json')):
            item = read_pending(state, file.stem, triggers)
            print(item['id'], item['kind'], item['status'], json.dumps(item['questions_to_ask']),
                  json.dumps({key:item.get(key) for key in ('revisit_status', 'revisit_on', 'revisit_trigger',
                    'revisit_offered_at', 'revisit_offered_cycle_id', 'proposal_status')}))
        for file in sorted(state.glob('proposals/*/proposal.json')):
            item = json.loads(file.read_text(encoding='utf-8'))
            details = proposal_details(state, item['id'], config)
            print(item['id'], item['file'], details['status'],
                  json.dumps({key: details[key] for key in
                    ('historical_save_verified', 'current_snapshot_matches', 'changed_files', 'target_currently_approved', 'approval_evidence_status')}))
        return
    if args.command == 'propose':
        root = Path(args.data).resolve()
        config, root = profile(state, root)
        if args.file not in config['approved_files']:
            raise ValueError('File is outside the approved allowlist')
        if args.file not in source_files(root):
            raise ValueError('New optional files require an approved schema/consumer migration before routine proposals')
        candidate = Path(args.candidate).read_bytes()
        candidate.decode('utf-8')
        if candidate == (root / args.file).read_bytes():
            raise ValueError('No change to propose')
        before = {n: digest(root / n) for n in source_files(root)}
        ident = uuid.uuid4().hex
        folder = state / 'proposals' / ident
        staged = folder / 'staged'
        staged.mkdir(parents=True, exist_ok=False)
        for name in before:
            shutil.copy2(root / name, staged / name)
            if digest(staged / name) != before[name]:
                raise ValueError('Source changed during staging')
        bibliography = config.get('bibliography_file')
        bib = root / bibliography if bibliography else None
        if bib and bib.is_file():
            shutil.copy2(bib, staged / bib.name)
        baseline = validate(staged, args.rscript, args.r_library, bibliography)
        (staged / args.file).write_bytes(candidate)
        checked = validate(staged, args.rscript, args.r_library, bibliography)
        error_review = compare_validation_errors(baseline, checked)
        diff = ''.join(difflib.unified_diff(
            (root / args.file).read_bytes().decode('utf-8').splitlines(True),
            candidate.decode('utf-8').splitlines(True),
            fromfile=args.file + ' (current)', tofile=args.file + ' (proposed)'))
        (folder / 'diff.txt').write_bytes(diff.encode('utf-8'))
        item = dict(id=ident, root=str(root), file=args.file, before=before,
                    candidate_sha256=digest(staged / args.file),
                    created=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    baseline_validation=baseline, proposed_validation=checked, error_review=error_review,
                    bibliography_file=bibliography,
                    bibliography_sha256=digest(bib) if bib and bib.is_file() else None)
        write_json(folder / 'proposal.json', item)
        print(json.dumps({'id': ident, 'status': 'awaiting approval', 'diff': diff,
                          'baseline_validation': validation_display(baseline),
                          'proposed_validation': validation_display(checked), 'error_review': error_review}, indent=2))
        return
    # Actual human approval must be obtained by the host before this assertion.
    valid_id(args.id)
    if args.approval != args.id:
        raise ValueError('Approval must identify this exact proposal')
    folder, item = read_proposal(state, args.id)
    outcome = proposal_status(state, args.id)
    if outcome == 'failed_before_write':
        raise ValueError('Apply refused; failed_before_write: this proposal cannot be reapplied. '
                         'Inspect status, backup and failure cause; preserve all attempt evidence. '
                         'Create a fresh proposal from current sources and obtain new exact approval, '
                         'even for an identical diff. Do not reuse the old approval.')
    if outcome != 'awaiting_approval':
        raise ValueError('Apply refused; reconcile existing outcome with status first: ' + outcome)
    root = Path(item['root']).resolve()
    config, root = profile(state, root)
    if item['file'] not in config['approved_files']:
        raise ValueError('Proposal target is not approved in the current profile')
    if set(item['before']) != set(source_files(root)):
        raise ValueError('Incomplete baseline')
    bibliography = config.get('bibliography_file')
    if bibliography != item.get('bibliography_file'):
        raise ValueError('Bibliography configuration changed; create a fresh proposal')
    bib = root / bibliography if bibliography else None
    for name in item['before']:
        if digest(root / name) != item['before'][name]:
            raise ValueError('Source changed; create a fresh proposal: ' + name)
    staged = folder / 'staged'
    for name in item['before']:
        expected = item['candidate_sha256'] if name == item['file'] else item['before'][name]
        if digest(staged / name) != expected:
            raise ValueError('Staged proposal changed; approval is invalid')
    if bibliography and item.get('bibliography_sha256') != digest(staged / bibliography):
        raise ValueError('Staged bibliography changed')
    staged_validation = validate(staged, args.rscript, args.r_library, bibliography)
    compare_validation_errors(item['proposed_validation'], staged_validation, exact=True)
    require_snapshot(staged.resolve(), item, bibliography)
    validate_current_bibliography(root, item, args.rscript, args.r_library,
                                  candidate_root=staged)
    approval_raw = approvals.read(state, args.approval_evidence, approval_target(item))
    reference = approvals.persist(folder, approval_raw, approval_target(item))
    attempts = folder / 'attempts'
    attempts.mkdir(exist_ok=True)
    attempt_path = attempts / (uuid.uuid4().hex + '.json')
    attempt = dict(approval_assertion=args.approval, approval_evidence=reference, started=now(), status='applying',
                   write_evidence_version=1, target_write_confirmed=False)
    write_json(attempt_path, attempt)
    backup = folder / 'backup'
    target = root / item['file']
    write_started = False
    try:
        backup.mkdir(exist_ok=False)
        shutil.copy2(target, backup / item['file'])
        if digest(backup / item['file']) != item['before'][item['file']]:
            raise ValueError('Backup hash mismatch')
        for name in item['before']:
            if digest(root / name) != item['before'][name]:
                raise ValueError('Source changed before write: ' + name)
        approvals.verify(folder, reference, approval_target(item))
        candidate_bytes = (staged / item['file']).read_bytes()
        write_started = True
        atomic_write(target, candidate_bytes)
        if digest(target) != item['candidate_sha256']:
            raise ValueError('Write hash mismatch')
        attempt.update(target_write_confirmed=True, target_written_sha256=item['candidate_sha256'])
        atomic_write(attempt_path, json.dumps(attempt, indent=2).encode('utf-8'))
        result, validated_bib = validate_current_bibliography(root, item, args.rscript,
                                                           args.r_library)
        config, root = current_scope(state, item)
        require_snapshot(root, item, config.get('bibliography_file'), check_bibliography=False)
        approvals.verify(folder, reference, approval_target(item))
        write_json(folder / 'applied.json', dict(approval_assertion=args.approval,
            approval_evidence=reference,
            applied=now(), backup=str(backup), validation=result,
            validated_bibliography_sha256=validated_bib))
        attempt.update(status='verified_saved', completed=now(), backup=str(backup))
        atomic_write(attempt_path, json.dumps(attempt, indent=2).encode('utf-8'))
        print(json.dumps({'status': 'verified_saved', 'file': item['file'], 'backup': str(backup)}))
    except Exception as error:
        outcome = proposal_status(state, args.id) if write_started else 'failed_before_write'
        attempt.update(status=outcome, completed=now(), error=str(error), backup=str(backup))
        try:
            atomic_write(attempt_path, json.dumps(attempt, indent=2).encode('utf-8'))
        except OSError:
            pass  # Durable apply-start marker plus target hashes still permit status recovery.
        raise ValueError('Apply interrupted; outcome=' + outcome +
                         '; inspect status and backup; do not reapply this proposal. '
                         + ('For failed_before_write, resolve the cause, create a fresh proposal '
                            'and obtain new exact approval, even for an identical diff. '
                            if outcome == 'failed_before_write' else
                            'For saved_unverified, review verification recovery without rewriting; '
                            'other outcomes require reviewed reconciliation. ') + str(error)) from error


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
