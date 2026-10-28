"""Read-only candidate exclusions from approved private preferences; no mail search."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re

_spec = importlib.util.spec_from_file_location('exclusion_private_state', Path(__file__).with_name('private_state.py'))
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


def rules_from_profile(config):
    discovery = config.get('discovery')
    if not isinstance(discovery, dict):
        raise ValueError('Discovery preferences are unresolved or malformed')
    rules = discovery.get('exclusions')
    if rules is None:
        return []
    if not isinstance(rules, list):
        raise ValueError('Discovery exclusions must be a list or null; no rules inferred')
    ids = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {'id', 'destination', 'activity_types', 'reason', 'confirmation_reference'}:
            raise ValueError('Unsupported exclusion fields; reviewed configuration required')
        for field in ('id', 'destination', 'reason', 'confirmation_reference'):
            helper.text(rule[field], 'exclusion.' + field)
        if rule['id'] in ids:
            raise ValueError('Exclusion IDs must be unique')
        ids.add(rule['id'])
        types = rule['activity_types']
        if (not isinstance(types, list) or not types or
                any(not isinstance(t, str) or not re.fullmatch('[a-z][a-z0-9_]*', t) for t in types)
                or len(set(types)) != len(types)):
            raise ValueError('Exclusions require unique explicit activity type IDs')
    return rules


def evaluate(config, candidates):
    rules = rules_from_profile(config)
    if not isinstance(candidates, list):
        raise ValueError('Candidates must be a list of minimal private summaries')
    result = dict(eligible=[], excluded=[], needs_classification=[],
                  rule_counts={r['id']: 0 for r in rules},
                  counts_are='unique candidates; per-rule match counts may overlap',
                  classification_limit='Typed classifications and confirmation references are operator assertions, not independent authentication')
    seen = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError('Candidate must be an object')
        ident = helper.text(candidate.get('id'), 'candidate.id')
        helper.text(candidate.get('destination'), 'candidate.destination')
        if ident in seen:
            raise ValueError('Duplicate candidate IDs; deduplicate before exclusions')
        seen.add(ident)
        applicable = [r for r in rules if r['destination'] == candidate['destination']]
        if not applicable:
            result['eligible'].append(copy.deepcopy(candidate))
            continue
        classification = candidate.get('activity_classification')
        if classification is None:
            result['needs_classification'].append(copy.deepcopy(candidate))
            continue
        if (not isinstance(classification, dict) or set(classification) != {'type', 'certainty', 'reference'}
                or not isinstance(classification['type'], str)
                or not re.fullmatch('[a-z][a-z0-9_]*', classification['type'])
                or classification['certainty'] not in ('supported', 'uncertain')):
            raise ValueError('Activity classification requires type, certainty and reference')
        if classification['certainty'] == 'uncertain':
            result['needs_classification'].append(copy.deepcopy(candidate))
            continue
        helper.text(classification['reference'], 'Actual activity classification evidence reference')
        matched = [r for r in applicable if classification['type'] in r['activity_types']]
        if matched:
            result['excluded'].append(dict(id=ident, matched_rule_ids=[r['id'] for r in matched]))
            for rule in matched:
                result['rule_counts'][rule['id']] += 1
        else:
            result['eligible'].append(copy.deepcopy(candidate))
    result['counts'] = {name: len(result[name]) for name in ('eligible', 'excluded', 'needs_classification')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    parser.add_argument('candidates', type=Path)
    args = parser.parse_args()
    config, _ = helper.profile(args.state)
    path = helper.inside(helper.plain(args.state), args.candidates)
    candidates = helper.decode(path.read_bytes())
    print(json.dumps(evaluate(config, candidates), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
