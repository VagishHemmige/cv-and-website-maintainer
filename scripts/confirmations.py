"""Stage and batch-save no-change answers only; no records, preferences or completion."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re

_spec = importlib.util.spec_from_file_location('confirmation_private_state', Path(__file__).with_name('private_state.py'))
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


def validate(config, answer):
    fields = {'id', 'cycle_id', 'category', 'outcome', 'response', 'reference', 'source_hashes'}
    if not isinstance(answer, dict) or set(answer) != fields or answer.get('outcome') != 'no_changes':
        raise ValueError('Only exact no_changes confirmation fields are accepted; changes/deferrals/approvals stay separate')
    helper.valid_id(answer['id'])
    if not isinstance(answer['cycle_id'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', answer['cycle_id']):
        raise ValueError('Stable cycle ID required')
    for field in ('category', 'response', 'reference'):
        helper.text(answer[field], field)
    sources = answer['source_hashes']
    if not isinstance(sources, dict) or not sources:
        raise ValueError('Hashes of the actual displayed source files are required')
    root = helper.plain(config['project_root'])
    for name, digest in sources.items():
        source = helper.plain(name)
        if root not in source.parents or not source.is_file():
            raise ValueError('Confirmation source must be an existing file within the configured project')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Source SHA256 required')
        if helper.file_hash(source) != digest:
            raise ValueError('Displayed source changed; inspect and reconcile before saving confirmation')


def staging_root(config, directory):
    directory = helper.plain(directory)
    helper.private_root(directory, config)
    return directory


def validate_envelope(config, state, envelope):
    if (not isinstance(envelope, dict) or set(envelope) !=
            {'schema_version', 'profile_path', 'config_scope_sha256', 'staged_at', 'answer'}
            or envelope['schema_version'] != 1 or envelope['profile_path'] != str(state / 'config.json')):
        raise ValueError('Malformed staging envelope or different profile; preserve for review')
    if envelope['config_scope_sha256'] != helper.search_scope_hash(config):
        raise ValueError('Profile scope changed; reconcile staged confirmations')
    if helper.timestamp(envelope['staged_at']) > helper.now():
        raise ValueError('Staging time cannot be in the future')
    validate(config, envelope['answer'])


def stage(state, directory, answer):
    state = helper.plain(state)
    config, _ = helper.profile(state)
    directory = staging_root(config, directory)
    validate(config, answer)
    path = helper.plain(directory / ('confirmation-' + answer['id'] + '.json'))
    envelope = dict(schema_version=1, profile_path=str(state / 'config.json'),
                    config_scope_sha256=helper.search_scope_hash(config),
                    staged_at=helper.now().isoformat(), answer=copy.deepcopy(answer))
    try:
        helper.exclusive(path, helper.encoded(envelope))
    except FileExistsError:
        existing = helper.decode(path.read_bytes())
        validate_envelope(config, state, existing)
        if existing['answer'] != answer:
            raise ValueError('Confirmation ID already retains a different answer; never overwrite')
        return dict(status='already_staged', path=str(path), canonical_history_saved=False)
    if helper.decode(path.read_bytes()) != envelope:
        raise ValueError('Staging verification failed; preserve file and inspect before retry')
    return dict(status='staged', path=str(path), canonical_history_saved=False)


def flush(state, directory, cycle_id, expected_revision):
    state = helper.plain(state)
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError('Expected confirmation-history revision required')
    with helper.writer_lock(state):
        config, _ = helper.profile(state)
        directory = staging_root(config, directory)
        target, before, doc = helper.no_change_document(state)
        selected = {}
        staged_hashes = {}
        for path in sorted(directory.glob('confirmation-*.json')):
            path = helper.plain(path)
            raw = path.read_bytes()
            envelope = helper.decode(raw)
            # Preserve unrelated cycles; malformed envelopes never silently disappear.
            if not isinstance(envelope, dict) or not isinstance(envelope.get('answer'), dict):
                raise ValueError('Malformed staged confirmation; preserve for review')
            answer = envelope['answer']
            if answer.get('cycle_id') != cycle_id:
                continue
            ident = helper.valid_id(answer.get('id', ''))
            if path.name != 'confirmation-' + ident + '.json' or ident in selected:
                raise ValueError('Staged confirmation identity mismatch')
            if ident in doc['confirmations']:
                if doc['confirmations'][ident] != envelope:
                    raise ValueError('Saved confirmation ID has different evidence')
                continue  # Idempotent replay remains valid after later source changes.
            validate_envelope(config, state, envelope)
            selected[ident] = envelope
            staged_hashes[str(path)] = helper.sha(raw)
        if not selected:
            return dict(status='no_pending_confirmations', revision=doc['revision'], state_rewritten=False)
        if doc['revision'] != expected_revision:
            raise ValueError('Confirmation history changed; inspect check-in-status revision before flush')
        for ident, envelope in selected.items():
            doc['confirmations'][ident] = envelope
        doc['revision'] += 1
        def still_current():
            current, _ = helper.profile(state)
            for path, digest in staged_hashes.items():
                if helper.file_hash(helper.plain(path)) != digest:
                    raise ValueError('Staged confirmation changed before commit')
            for envelope in selected.values():
                validate_envelope(current, state, envelope)
        target.parent.mkdir(exist_ok=True)
        result = helper.commit(state, target, before, doc, 'no_change_confirmations',
                               dict(cycle_id=cycle_id, confirmation_ids=sorted(selected),
                                    staged_sha256=staged_hashes, actual_user_response_assertion=True),
                               precondition=still_current)
        return dict(result, saved_ids=sorted(selected), revision=doc['revision'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('stage')
    command.add_argument('state', type=Path); command.add_argument('directory', type=Path)
    command.add_argument('answer', type=Path)
    command = sub.add_parser('flush')
    command.add_argument('state', type=Path); command.add_argument('directory', type=Path)
    command.add_argument('--cycle', required=True); command.add_argument('--expected-revision', required=True, type=int)
    args = parser.parse_args()
    if args.command == 'stage':
        result = stage(args.state, args.directory, helper.decode(args.answer.read_bytes()))
    else:
        result = flush(args.state, args.directory, args.cycle, args.expected_revision)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
