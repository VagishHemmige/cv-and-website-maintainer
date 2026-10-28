"""Private approval audit evidence. Structure/hash checks are not authentication."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re

FILENAME = 'approval-evidence.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Approval evidence needs nonblank ' + label)
    return value


def timestamp(value):
    parsed = dt.datetime.fromisoformat(text(value, 'timestamp').replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Approval evidence timestamps need explicit timezones')
    return parsed


def private_path(state, path):
    state, path = Path(state), Path(path)
    if not state.is_absolute() or not path.is_absolute() or '..' in path.parts:
        raise ValueError('Approval evidence needs an absolute private path')
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and part.resolve() != part):
            raise ValueError('Redirected approval evidence path refused')
    if state not in path.parents:
        raise ValueError('Approval evidence must be inside the private state directory')
    return path


def target(kind, ident, sha256, destination):
    return dict(kind=kind, id=ident, sha256=sha256, destination=str(destination))


def parse(raw, expected):
    if len(raw) > 65536:
        raise ValueError('Approval evidence exceeds 64 KiB; retain only minimal approval context')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate approval evidence JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-finite approval evidence number')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 1:
        raise ValueError('Unsupported approval evidence schema')
    if value.get('decision') != 'approved':
        raise ValueError('Approval evidence must record an approved decision')
    for name in ('response', 'channel', 'message_reference', 'proposal_reference'):
        text(value.get(name), name)
    captured = timestamp(value.get('recorded_at'))
    approved = value.get('approved_at')
    if approved is None:
        if value.get('timestamp_source') != 'message_time_unavailable':
            raise ValueError('Unknown approval time must be labelled message_time_unavailable')
    else:
        if value.get('timestamp_source') not in ('host_message_timestamp', 'user_supplied_timestamp'):
            raise ValueError('Known approval time needs its actual timestamp source')
        if timestamp(approved) > captured:
            raise ValueError('Approval time cannot be later than evidence recording time')
    items = value.get('approvals')
    if not isinstance(items, list) or not items:
        raise ValueError('Approval evidence must identify exact approved items')
    seen = set()
    matched = False
    for item in items:
        if not isinstance(item, dict) or item.get('kind') not in ('yaml', 'attachment', 'profile', 'setup', 'publication'):
            raise ValueError('Invalid approval evidence item kind')
        ident = text(item.get('id'), 'item ID')
        if not re.fullmatch('[0-9a-f]{32}', ident) or not re.fullmatch('[0-9a-f]{64}', text(item.get('sha256'), 'item SHA256')):
            raise ValueError('Approval evidence needs exact item ID and SHA256')
        key = (item['kind'], ident)
        if key in seen:
            raise ValueError('Duplicate or contradictory approval evidence item')
        seen.add(key)
        destination = Path(text(item.get('destination'), 'destination'))
        if not destination.is_absolute() or '..' in destination.parts:
            raise ValueError('Approval destination must be absolute without traversal')
        if item['kind'] == 'attachment' and item.get('public_use_approved') is not True:
            raise ValueError('Attachment evidence must explicitly cover public use')
        if (all(item.get(name) == expected[name] for name in ('kind', 'id', 'sha256')) and
                destination.resolve() == Path(expected['destination']).resolve()):
            matched = True
    if not matched:
        raise ValueError('Approval evidence does not match this exact item, bytes and destination')
    return value


def read(state, path, expected):
    if path is None:
        raise ValueError('Approval evidence file required before saving')
    path = private_path(state, path)
    if not path.is_file() or path.stat().st_size > 65536:
        raise ValueError('Missing or oversized approval evidence file')
    raw = path.read_bytes()
    parse(raw, expected)
    return raw


def persist(folder, raw, expected):
    parse(raw, expected)
    path = Path(folder) / FILENAME
    # Refuse redirected destinations even when bytes would be identical.
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and part.resolve() != part):
            raise ValueError('Redirected approval audit destination refused')
    try:
        with path.open('xb') as out:
            out.write(raw); out.flush(); os.fsync(out.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError('Existing approval evidence differs; never overwrite approval history')
    if path.read_bytes() != raw:
        raise ValueError('Stored approval evidence verification failed')
    return dict(path=FILENAME, sha256=digest(raw), schema_version=1)


def verify(folder, reference, expected):
    if (not isinstance(reference, dict) or reference.get('path') != FILENAME or
            type(reference.get('schema_version')) is not int or reference['schema_version'] != 1):
        raise ValueError('Missing linked approval evidence; reviewed reconciliation required')
    path = Path(folder) / FILENAME
    raw = read(Path(folder), path, expected)
    if digest(raw) != reference.get('sha256'):
        raise ValueError('Stored approval evidence hash changed; reconcile before verification')
    return reference


def status(folder, reference, expected):
    if reference is None:
        return 'not_recorded'
    try:
        verify(folder, reference, expected)
    except (ValueError, OSError, KeyError, TypeError):
        return 'missing_or_changed'
    return 'recorded'
