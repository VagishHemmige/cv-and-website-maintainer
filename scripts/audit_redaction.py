"""Conservative audit-surface redaction; not de-identification or authentication.

Only use on a separately authorized export copy. Never export reasoning or raw
session logs. Reviewed academic snapshots remain a separate explicit selection.
"""
import copy
import hashlib
import json
import re

MARKER_KEYS = {'redacted', 'reason', 'canonical_sha256', 'canonical_bytes'}
COMMON = ('timestamp', 'source_line', 'type', 'id', 'turn_id',
          'started_at_ms', 'completed_at_ms')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def omitted(value, reason):
    raw = encoded(value)
    return dict(redacted=True, reason=reason,
                canonical_sha256=hashlib.sha256(raw).hexdigest(), canonical_bytes=len(raw))


def is_marker(value):
    return (isinstance(value, dict) and set(value) == MARKER_KEYS
            and value.get('redacted') is True
            and isinstance(value.get('reason'), str) and bool(value['reason'])
            and isinstance(value.get('canonical_sha256'), str)
            and re.fullmatch('[0-9a-f]{64}', value['canonical_sha256']) is not None
            and type(value.get('canonical_bytes')) is int and value['canonical_bytes'] >= 0)


def metadata(value, fields):
    return {key: copy.deepcopy(value[key]) for key in fields if key in value}


def redact_calls(calls):
    result = []
    for call in calls:
        item = metadata(call, ('timestamp', 'source_line', 'id', 'name'))
        item['arguments'] = omitted(call.get('arguments'), 'Raw wrapper/tool arguments omitted')
        result.append(item)
    return result


def redact_events(events, reviewed_query_arguments=None):
    reviewed = reviewed_query_arguments or {}
    used = set()
    result = []
    for event in events:
        item = metadata(event, COMMON)
        kind = event.get('type')
        if kind == 'CommandExecution':
            item.update(metadata(event, ('cwd', 'status', 'exit_code', 'duration')))
            for key in ('command', 'aggregated_output'):
                item[key] = omitted(event.get(key), 'Executable command/output omitted')
        elif kind == 'McpToolCall':
            item.update(metadata(event, ('server', 'tool', 'status', 'duration')))
            item['arguments'] = omitted(event.get('arguments'), 'Raw connector arguments omitted')
            item['result'] = omitted(event.get('result'), 'Raw connector result omitted')
            if event.get('id') in reviewed:
                arguments = event.get('arguments')
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                approved = reviewed[event['id']]
                if (event.get('tool') != 'gmail.search_emails'
                        or not isinstance(approved, dict)
                        or set(approved) != {'query', 'max_results'}
                        or not isinstance(approved['query'], str) or not approved['query'].strip()
                        or type(approved['max_results']) is not int or approved['max_results'] < 1
                        or approved != arguments):
                    raise ValueError('Reviewed query must match the exact search event and allowed fields')
                item['reviewed_query_arguments'] = copy.deepcopy(approved)
                used.add(event['id'])
        elif kind == 'FileChange':
            item.update(metadata(event, ('status',)))
            for key in ('changes', 'stdout', 'stderr'):
                item[key] = omitted(event.get(key), 'Raw file-change body/output omitted')
        elif kind == 'Extension':
            item.update(metadata(event, ('kind',)))
            for key in ('query', 'action', 'results'):
                item[key] = omitted(event.get(key), 'Raw extension body omitted; selected queries retained separately')
        # Unknown event bodies never pass through by default.
        result.append(item)
    if used != set(reviewed):
        raise ValueError('Reviewed query references a missing event')
    return result


def redact_timing(summary):
    result = metadata(summary, ('scope_start', 'scope_end_exclusive', 'source_log_sha256',
        'conversation_messages', 'structured_question_calls', 'observed_escalation_request_wrappers',
        'tool_call_wrappers', 'completed_items', 'command_items'))
    result['limitations'] = [
        'Recorded intervals may include work and waits and may overlap; do not sum blindly.',
        'Question/escalation requests are not physical click counts.',
        'Raw command bodies and outputs are omitted; inspect selected durable evidence separately.']
    result['turns'] = []
    for turn in summary.get('turns', []):
        item = metadata(turn, ('turn_id', 'started_at', 'completed_at', 'duration_ms'))
        item['error'] = omitted(turn['error'], 'Raw turn error omitted') if turn.get('error') else None
        result['turns'].append(item)
    result['completed_item_wall_times'] = []
    for timing in summary.get('completed_item_wall_times', []):
        item = metadata(timing, ('event_id', 'type', 'wall_ms', 'tool'))
        item['command'] = omitted(timing.get('command'), 'Duplicated timing command omitted')
        result['completed_item_wall_times'].append(item)
    return result


def scan_surfaces(calls, events, timing, reviewed_query_arguments=None):
    """Return structural finding labels, never the flagged source values."""
    findings = []
    for index, call in enumerate(calls):
        if set(call) - {'timestamp', 'source_line', 'id', 'name', 'arguments'} or not is_marker(call.get('arguments')):
            findings.append('tool_calls['+str(index)+'].raw_or_unknown_body')
    expected = redact_events(events)
    # Compare the permitted schema, not regenerated marker hashes.
    for index, (event, template) in enumerate(zip(events, expected)):
        allowed = set(template) | ({'reviewed_query_arguments'} if event.get('id') in (reviewed_query_arguments or {}) else set())
        if set(event) - allowed:
            findings.append('timeline['+str(index)+'].unknown_body')
        for key in ('command', 'aggregated_output', 'arguments', 'result', 'changes',
                    'stdout', 'stderr', 'query', 'action', 'results'):
            if key in template and not is_marker(event.get(key)):
                findings.append('timeline['+str(index)+'].'+key)
        approved = (reviewed_query_arguments or {}).get(event.get('id'))
        if event.get('reviewed_query_arguments') != approved or (approved is not None and event.get('tool') != 'gmail.search_emails'):
            findings.append('timeline['+str(index)+'].unreviewed_query')
    if set(reviewed_query_arguments or {}) - {event.get('id') for event in events}:
        findings.append('timeline.missing_reviewed_event')
    allowed_timing = {'scope_start', 'scope_end_exclusive', 'source_log_sha256',
        'conversation_messages', 'structured_question_calls', 'observed_escalation_request_wrappers',
        'tool_call_wrappers', 'completed_items', 'command_items', 'limitations', 'turns',
        'completed_item_wall_times'}
    if set(timing) - allowed_timing:
        findings.append('timing.unknown_body')
    for index, item in enumerate(timing.get('completed_item_wall_times', [])):
        if set(item) - {'event_id', 'type', 'wall_ms', 'tool', 'command'} or not is_marker(item.get('command')):
            findings.append('timing['+str(index)+'].command_or_unknown_body')
    for index, item in enumerate(timing.get('turns', [])):
        if set(item) - {'turn_id', 'started_at', 'completed_at', 'duration_ms', 'error'}:
            findings.append('turns['+str(index)+'].unknown_body')
        if item.get('error') is not None and not is_marker(item['error']):
            findings.append('turns['+str(index)+'].raw_error')
    return findings


def sender_filter_code(text):
    return (re.search(r're\.(?:search|match|fullmatch|compile)\s*\(', text) is not None
            and re.search(r'\bsender\b|\bfrom_addr\b|[\x22\x27](?:from|from_address)[\x22\x27]', text, re.I) is not None)
