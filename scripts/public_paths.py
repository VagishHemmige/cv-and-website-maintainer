"""One conservative public-file boundary for new setup and deployment observations."""
from pathlib import PurePosixPath, PureWindowsPath

PROTECTED_PARTS = frozenset(('cv', 'private', 'raw', '.git', '.codex',
    'state-history', 'profile-proposals', 'initialization-history', '.ssh'))
PROTECTED_NAMES = frozenset(('private.yml', 'config.json', 'handoff.json',
    'initialization.json', 'agents.md', '.renviron', '.rhistory', '.rdata',
    '.netrc', '_netrc', '.git-credentials', 'id_rsa', 'id_dsa', 'id_ecdsa',
    'id_ed25519', 'id_ecdsa_sk', 'id_ed25519_sk'))

def private_path(path):
    if not isinstance(path, str) or not path or '\\' in path or '\x00' in path:
        return True
    p = PurePosixPath(path)
    if p.is_absolute() or PureWindowsPath(path).drive or any(x in ('', '.', '..') for x in path.split('/')):
        return True
    parts = [x.lower() for x in p.parts]
    return (any(x in PROTECTED_PARTS or x in PROTECTED_NAMES or x.startswith('.env') or
                x.endswith(('.pem', '.key', '.pfx')) for x in parts) or
            (parts[-1].endswith('.docx') and path != 'templates/cv-styles.docx'))

