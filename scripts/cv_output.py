"""Read-only local CV selection and metadata. Never certify contents as current."""
import argparse
import datetime as dt
import fnmatch
import hashlib
import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location('cv_private_state', Path(__file__).with_name('private_state.py'))
state_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(state_helper)


def resolve(check_in, last_save_at=None):
    if not isinstance(check_in, dict):
        raise ValueError('Check-in preferences must be an object')
    save = state_helper.timestamp(last_save_at) if last_save_at is not None else None
    if save is not None and save > state_helper.now():
        raise ValueError('Referenced verified save cannot be in the future')
    result = dict(kind='cv', status='not_configured', freshness='unverified', candidates=[],
                  content_verified=False, last_save_at=last_save_at)
    locator = check_in.get('cv_locator')
    try:
        if locator is not None:
            if not isinstance(locator, dict) or set(locator) != {'directory', 'filename_pattern'}:
                raise ValueError('CV locator requires directory and filename_pattern only')
            directory = state_helper.plain(state_helper.text(locator['directory'], 'CV directory'))
            pattern = state_helper.text(locator['filename_pattern'], 'CV filename pattern')
            if any(part in pattern for part in ('/', '\\', '..', '**')) or pattern in ('.', '*'):
                raise ValueError('Use a filename-only CV pattern without traversal or recursive wildcards')
            if Path(pattern).suffix.lower() not in ('.docx', '.pdf'):
                raise ValueError('CV pattern must end in .docx or .pdf')
            if not directory.exists():
                return dict(result, status='missing')
            if not directory.is_dir():
                raise ValueError('CV directory must be a directory')
            paths = [p for p in directory.iterdir() if fnmatch.fnmatchcase(p.name, pattern)
                     and not p.name.startswith('~$')]
            result['selection_basis'] = 'latest modification time within approved filename pattern'
        else:
            link = check_in.get('cv_link')
            if not link:
                return result
            if not isinstance(link, str):
                raise ValueError('CV link must be text')
            if link.startswith(('https://', 'http://')):
                return dict(result, status='remote_unverified', configured_link=link)
            path = state_helper.plain(link)
            if path.suffix.lower() not in ('.docx', '.pdf'):
                raise ValueError('Configured CV must be a .docx or .pdf output')
            paths = [path] if path.exists() else []
            result['selection_basis'] = 'configured fixed path; no inferred filename pattern'
        for path in paths:
            path = state_helper.plain(path)
            if not path.is_file():
                continue
            stat = path.stat()
            result['candidates'].append(dict(path=str(path), size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                modified_at=dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).isoformat()))
        result['candidates'].sort(key=lambda c: (-c['mtime_ns'], c['path']))
        if not result['candidates']:
            return dict(result, status='missing')
        if len(result['candidates']) > 1 and result['candidates'][0]['mtime_ns'] == result['candidates'][1]['mtime_ns']:
            return dict(result, status='ambiguous', reason='Newest candidates have identical modification times; ask which output to use')
        chosen = dict(result['candidates'][0])
        path = state_helper.plain(chosen['path'])
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        after = path.stat()
        if after.st_mtime_ns != chosen['mtime_ns'] or after.st_size != chosen['size_bytes']:
            return dict(result, status='changed_during_observation')
        chosen['sha256'] = digest.hexdigest()
        result.update(status='found', selected=chosen)
        modified = state_helper.timestamp(chosen['modified_at'])
        if modified > state_helper.now():
            result['freshness'] = 'future_file_timestamp_unverified'
        elif save is not None:
            result['freshness'] = ('stale_by_timestamp' if modified < save else
                                   'modified_at_or_after_save_contents_unverified')
        return result
    except OSError as error:
        return dict(result, status='inaccessible', reason=type(error).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    parser.add_argument('--last-save-at', help='Timestamp of an independently verified save, not an inferred file date')
    args = parser.parse_args()
    config, _ = state_helper.profile(args.state)
    review = config.get('review', {})
    check_in = review.get('check_in', {}) if isinstance(review, dict) else {}
    print(json.dumps(resolve(check_in, args.last_save_at), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
