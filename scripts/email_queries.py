"""Prepare Gmail discovery definitions; no connector, profile or checkpoint writes."""
import argparse
import hashlib
import json
from pathlib import Path

CATALOGUE = Path(__file__).resolve().parents[1] / 'references' / 'email-queries.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def prepare(identity, categories, catalogue=None):
    """Explicit categories are operator assertions of saved scope, not permission."""
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError('An explicitly approved account identity is required')
    if (not isinstance(categories, list) or not categories or
            any(not isinstance(c, str) for c in categories) or len(set(categories)) != len(categories)):
        raise ValueError('Select unique, nonempty approved category IDs')
    catalogue = catalogue if catalogue is not None else json.loads(CATALOGUE.read_text(encoding='utf-8'))
    if catalogue.get('schema_version') != 1 or catalogue.get('provider') != 'gmail':
        raise ValueError('Unsupported email catalogue schema/provider')
    version = catalogue.get('version')
    if not isinstance(version, str) or not version.strip():
        raise ValueError('Catalogue version is required')
    definitions = catalogue.get('categories')
    if not isinstance(definitions, dict) or any(c not in definitions for c in categories):
        raise ValueError('Unknown category; use catalogue IDs, not an inferred scope')
    selected = []
    for category in sorted(categories):
        definition = definitions[category]
        query = definition.get('query')
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Each selected category needs a nonempty query')
        selected.append({'id': category, 'query': query})
    # Dates/tokens/agent prose do not participate. Exact selected queries do.
    scope = {'catalogue_version': version, 'queries': selected}
    fingerprint = hashlib.sha256(canonical(scope).encode('utf-8')).hexdigest()
    return {
        'source': {'provider': 'gmail', 'identity': identity,
                   'scope_version': 'email-catalogue-' + version + '-' + fingerprint,
                   'query': canonical(scope)},
        'subqueries': [q['id'] for q in selected],
        'queries': selected,
        'unselected_categories': sorted(set(definitions) - set(categories)),
        'coverage_limit': 'Keyword searches in the selected account only; not all mail, accounts or activities. Invitations and decisions are candidates, not proof of completion.'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', required=True)
    parser.add_argument('--categories', nargs='+', required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.identity, args.categories)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
