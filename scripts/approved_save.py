"""Capture exact human approval context and delegate one YAML save.

The input is an operator assertion, not human authentication. It must describe
the actual response to the displayed exact proposal. No targets are inferred.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import uuid

_spec = importlib.util.spec_from_file_location('approved_save_proposals',
    Path(__file__).with_name('proposals.py'))
records = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(records)
state_helper = records.pending_state


def capture(state, ident, context):
    state = state_helper.plain(state)
    records.profile(state)
    records.valid_id(ident)
    folder, item = records.read_proposal(state, ident)
    outcome = records.proposal_status(state, ident)
    if outcome != 'awaiting_approval':
        raise ValueError('Save refused; inspect existing status before reconciliation: ' + outcome)
    context = records.approvals.private_path(state, context)
    if not context.is_file() or context.stat().st_size > 65536:
        raise ValueError('Missing or oversized approval context')
    value = state_helper.decode(context.read_bytes())
    fields = {'schema_version', 'decision', 'response', 'channel', 'message_reference',
              'proposal_reference', 'approved_at', 'timestamp_source', 'approvals'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('Approval context requires exact evidence fields except recorded_at')
    # Never derive the approved hash/destination from newly observed bytes.
    value['recorded_at'] = records.now()
    raw = state_helper.encoded(value)
    expected = records.approval_target(item)
    records.approvals.parse(raw, expected)
    directory = state_helper.plain(state / 'approval-inputs')
    directory.mkdir(exist_ok=True)
    path = directory / (uuid.uuid4().hex + '.json')
    state_helper.exclusive(path, raw)
    if records.approvals.read(state, path, expected) != raw:
        raise ValueError('Approval capture verification failed; preserve evidence for review')
    return path


def apply(state, ident, context, rscript, library=None):
    state = state_helper.plain(state)
    evidence = capture(state, ident, context)
    # This line remains available even if the process is subsequently interrupted.
    print(json.dumps(dict(event='approval_captured', id=ident,
                          approval_evidence=str(evidence), save_verified=False)), flush=True)
    command = [sys.executable, '-B', str(Path(__file__).with_name('proposals.py')),
               'apply', str(state), ident, '--approval', ident,
               '--approval-evidence', str(evidence), str(rscript)]
    if library:
        command.extend(['--r-library', str(library)])
    completed = subprocess.run(command, capture_output=True, text=True)
    try:
        config, _ = records.profile(state)
        current = records.proposal_details(state, ident, config)
    except (ValueError, OSError, KeyError, TypeError) as error:
        current = dict(status='unknown', status_error=str(error))
    result = dict(id=ident, approval_evidence=str(evidence),
                  helper_returncode=completed.returncode, current=current)
    if completed.returncode:
        result.update(error=completed.stderr.strip() or 'Save helper failed without diagnostics',
                      next_step='Inspect status and retained evidence; do not blindly retry or roll back')
    elif current['status'] != 'verified_saved':
        result['next_step'] = 'Helper returned; current status still requires inspection'
    return completed.returncode or (0 if current['status'] == 'verified_saved' else 1), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    parser.add_argument('id')
    parser.add_argument('context', type=Path)
    parser.add_argument('rscript')
    parser.add_argument('--r-library')
    args = parser.parse_args()
    code, result = apply(args.state, args.id, args.context, args.rscript, args.r_library)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
