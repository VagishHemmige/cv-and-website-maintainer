"""Read-only filtering by approved account-scoped exact sender/domain rules."""
import argparse
from email.headerregistry import HeaderRegistry
import importlib.util
import json
from pathlib import Path
import re

_spec = importlib.util.spec_from_file_location('sender_private_state', Path(__file__).with_name('private_state.py'))
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


def domain(value):
    if not isinstance(value, str) or not value or value != value.strip() or value.endswith('.'):
        raise ValueError('Use an exact DNS domain without whitespace or a trailing dot')
    try:
        normalized = value.encode('idna').decode('ascii').lower()
    except UnicodeError as error:
        raise ValueError('Invalid sender domain') from error
    labels = normalized.split('.')
    if (len(labels) < 2 or len(normalized) > 253 or
            any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)):
        raise ValueError('Use an exact DNS domain; wildcards and regular expressions are unsupported')
    return normalized


def mailbox(value):
    """Conservative parsing; ambiguous/unsupported headers never cause exclusion."""
    if not isinstance(value, str) or not value.strip() or any(c in value for c in ('\r', '\n', '\x00')):
        return None
    try:
        header = HeaderRegistry()('From', value)
        if header.defects or len(header.addresses) != 1 or any(g.display_name is not None for g in header.groups):
            return None
        address = header.addresses[0]
        local = address.username
        if (not local or not re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+", local)
                or local.startswith('.') or local.endswith('.') or '..' in local):
            return None
        host = domain(address.domain)
        return local + '@' + host, host
    except (ValueError, IndexError, TypeError):
        return None


def approved_rules(config, account):
    helper.text(account, 'Actual authorized account identity')
    discovery = config.get('discovery')
    if not isinstance(discovery, dict):
        raise ValueError('Discovery preferences are unresolved or malformed')
    rules = discovery.get('sender_exclusions')
    if rules is None:
        return []
    if not isinstance(rules, list):
        raise ValueError('Sender exclusions must be a list or null; no filters inferred')
    active, ids = [], set()
    fields = {'id', 'account', 'kind', 'value', 'include_subdomains', 'reason', 'confirmation_reference'}
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != fields:
            raise ValueError('Unsupported sender rule fields; exact reviewed configuration required')
        for field in ('id', 'account', 'value', 'reason', 'confirmation_reference'):
            helper.text(rule[field], 'sender exclusion.' + field)
        if rule['id'] in ids:
            raise ValueError('Sender rule IDs must be unique')
        ids.add(rule['id'])
        if type(rule['include_subdomains']) is not bool:
            raise ValueError('Explicit include_subdomains boolean required')
        if rule['kind'] == 'address':
            parsed = mailbox(rule['value'])
            if (parsed is None or rule['include_subdomains'] or
                    any(c.isspace() or c in '<>()"' for c in rule['value'])):
                raise ValueError('Address rule needs one bare address; no substring/display-name matching')
            normalized = parsed[0]
        elif rule['kind'] == 'domain':
            normalized = domain(rule['value'])
        else:
            raise ValueError('Sender rule kind must be address or domain')
        if rule['account'] == account:
            active.append(dict(rule, normalized_value=normalized))
    return active


def evaluate(config, account, messages):
    rules = approved_rules(config, account)
    if not isinstance(messages, list):
        raise ValueError('Messages must be a deduplicated minimal list')
    result = dict(retained_ids=[], excluded=[], sender_review_ids=[],
                  rule_counts={r['id']:0 for r in rules},
                  count_scope='Unique returned message IDs; rule counts can overlap, sender_review_ids are retained')
    seen = set()
    for message in messages:
        if not isinstance(message, dict) or set(message) != {'id', 'from'}:
            raise ValueError('Input accepts only id and from, never raw bodies or arbitrary filter code')
        ident = helper.text(message['id'], 'message.id')
        if ident in seen:
            raise ValueError('Duplicate message IDs; deduplicate before sender filtering')
        seen.add(ident)
        if not rules:
            result['retained_ids'].append(ident)
            continue
        parsed = mailbox(message['from'])
        if parsed is None:
            result['retained_ids'].append(ident)
            result['sender_review_ids'].append(ident)
            continue
        address, host = parsed
        matches = [r for r in rules if
                   (r['kind'] == 'address' and address == r['normalized_value']) or
                   (r['kind'] == 'domain' and (host == r['normalized_value'] or
                    (r['include_subdomains'] and host.endswith('.' + r['normalized_value']))))]
        if not matches:
            result['retained_ids'].append(ident)
            continue
        result['excluded'].append(dict(id=ident, matched_rule_ids=[r['id'] for r in matches]))
        for rule in matches:
            result['rule_counts'][rule['id']] += 1
    result['counts'] = dict(returned=len(messages), retained=len(result['retained_ids']),
                           excluded=len(result['excluded']), sender_review=len(result['sender_review_ids']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path); parser.add_argument('messages', type=Path)
    parser.add_argument('--account', required=True)
    args = parser.parse_args()
    config, _ = helper.profile(args.state)
    path = helper.inside(helper.plain(args.state), args.messages)
    print(json.dumps(evaluate(config, args.account, helper.decode(path.read_bytes())), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
