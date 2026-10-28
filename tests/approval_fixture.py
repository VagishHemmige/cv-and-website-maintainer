"""Synthetic approval inputs. Never use these fixtures to authorize real data."""
import json
from pathlib import Path


def approval_file(state, kind, ident, sha256, destination):
    item = dict(kind=kind, id=ident, sha256=sha256, destination=str(destination))
    if kind == 'attachment':
        item['public_use_approved'] = True
    value = dict(schema_version=1, decision='approved', response='SYNTHETIC FIXTURE APPROVAL ONLY',
        approved_at=None, recorded_at='2026-10-17T12:00:00+00:00',
        timestamp_source='message_time_unavailable', channel='unit-test',
        message_reference='synthetic-fixture-response', proposal_reference='synthetic-fixture-proposal',
        approvals=[item])
    path = Path(state) / ('fixture-approval-' + kind + '-' + ident + '.json')
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    return path
