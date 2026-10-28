"""Local readiness observations only: no installation, project execution or network."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import setup_execution as setup

LINKS = {
    'r': 'https://cran.r-project.org/',
    'quarto': 'https://quarto.org/docs/get-started/',
    'git': 'https://docs.github.com/en/get-started/git-basics/set-up-git',
    'python': 'https://pypdf.readthedocs.io/en/stable/user/installation.html',
}
PACKAGES = ('yaml', 'officer', 'RefManageR', 'dplyr', 'lubridate', 'purrr',
            'tidyverse', 'knitr', 'rmarkdown')
VERSION = re.compile(r'(?<![A-Za-z0-9])\d+[.]\d+(?:[.]\d+)*(?:[-+][A-Za-z0-9.]+)?')

def row(component, status, detail, path=None, version=None, link=None):
    return dict(component=component, status=status, detail=detail,
                path=path, version=version, guidance=link)

def environment():
    env = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(key, None)
    env.update(GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1')
    return env

def run(argv, env):
    try:
        result = subprocess.run(argv, cwd=Path(__file__).resolve().parent,
                                env=env, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None, 'Probe timed out; availability is unresolved.'
    except OSError:
        return None, 'Probe could not launch; check path and host permission.'
    if result.returncode:
        return None, 'Probe failed; inspect the selected installation privately.'
    return (result.stdout or result.stderr).decode('utf-8', errors='replace'), None

def selected(explicit, name):
    # An explicit saved path never silently falls back to another installation.
    value = explicit if explicit is not None else shutil.which(name)
    if value is None and name == 'quarto' and os.name == 'nt':
        for root in dict.fromkeys(filter(None, (os.environ.get('ProgramFiles'), 'C:/Program Files'))):
            candidate = Path(root)/'RStudio/resources/app/bin/quarto/bin/quarto.exe'
            if candidate.is_file():
                value = str(candidate)
                break
    return value

def tool(component, path, args, env, link):
    if path is None:
        return row(component, 'missing', 'No candidate found in the selected discovery scope; check saved/host runtimes.', link=link), None
    try:
        exe = str(setup.executable(path))
    except ValueError:
        return row(component, 'blocked', 'Selected executable is inaccessible, invalid or not executable.', path=str(path), link=link), None
    out, error = run([exe, *args], env)
    match = VERSION.search(out or '')
    if error or not match:
        return row(component, 'blocked', error or 'Version response was not recognized.', path=str(path), link=link), None
    return row(component, 'ready', 'Selected executable launched; this is not an output-generation test.',
               path=exe, version=match[0], link=link), exe

def report(goals=('records',), python=None, rscript=None, r_library=None,
           quarto=None, git=None, packages=None, legacy_ppt=False):
    goals = set(goals)
    if not goals or not goals <= {'records', 'cv', 'site', 'pdf', 'git'}:
        raise ValueError('Choose records, cv, site, pdf and/or git.')
    if packages is not None and any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9.]*', n) for n in packages):
        raise ValueError('Use inspected R package names, not expressions.')
    if legacy_ppt and 'pdf' not in goals:
        raise ValueError('Legacy PPT requires the pdf goal.')
    env = environment()
    rows = []
    item, py = tool('Python', selected(python or sys.executable, 'python'), ['--version'], env, LINKS['python'])
    rows.append(item)
    if 'pdf' in goals and py:
        names = ['pypdf'] + (['olefile'] if legacy_ppt else [])
        code = """import importlib, importlib.metadata, json
result={}
for name in NAMES:
 try:
  importlib.import_module(name)
  result[name]={'status':'ready','version':importlib.metadata.version(name)}
 except Exception:
  result[name]={'status':'blocked','version':None}
print(json.dumps(result))
""".replace('NAMES', repr(names))
        out, error = run([py, '-I', '-B', '-c', code], env)
        try:
            data = json.loads(out) if error is None else {}
            if not isinstance(data, dict):
                data = {}
        except (ValueError, TypeError):
            data = {}
        for name in names:
            value = data.get(name, {})
            if not isinstance(value, dict):
                value = {}
            ready = value.get('status') == 'ready' and isinstance(value.get('version'), str) and VERSION.fullmatch(value['version'])
            rows.append(row(name, 'ready' if ready else 'blocked',
                'Module imports in selected Python.' if ready else 'Module missing, failed to load or probe unresolved; review this interpreter.',
                path=py, version=value.get('version') if ready else None, link=LINKS['python']))
    elif 'pdf' in goals:
        rows.append(row('PDF modules', 'not checked', 'Resolve Python first.', link=LINKS['python']))
    else:
        rows.append(row('PDF modules', 'not needed', 'PDF processing was not selected.'))

    if goals & {'records', 'cv', 'site'}:
        item, rex = tool('R', selected(rscript, 'Rscript'), ['--version'], env, LINKS['r'])
        rows.append(item)
        required = sorted(set(packages if packages is not None else
                              PACKAGES if goals & {'cv', 'site'} else ['yaml']))
        # CV needs these even when additional consumer dependencies are supplied.
        if 'cv' in goals:
            required = sorted(set(required) | {'officer', 'yaml', 'RefManageR'})
        if 'records' in goals:
            required = sorted(set(required) | {'yaml'})
        if rex:
            renv = env.copy()
            if r_library is not None:
                renv['ACADEMIC_READINESS_LIBRARY'] = str(r_library)
            else:
                renv.pop('ACADEMIC_READINESS_LIBRARY', None)
            code = """lib <- Sys.getenv("ACADEMIC_READINESS_LIBRARY")
if (nzchar(lib)) {
 if (!dir.exists(lib)) quit(status=2)
 .libPaths(c(lib, .libPaths()))
}
cat("AR_READY_LIBS", paste(.libPaths(), collapse="|"), "\\n", sep="\\t")
for (p in PACKAGES) {
 ok <- tryCatch(requireNamespace(p, quietly=TRUE), error=function(e) FALSE)
 ver <- if (ok) as.character(utils::packageVersion(p)) else "-"
 cap <- if (ok && p == "officer") "run_tab" %in% getNamespaceExports(p) else TRUE
 cat("AR_READY_PACKAGE", p, if(ok && cap) "ready" else "blocked", ver, "\\n", sep="\\t")
}
""".replace('PACKAGES', 'c(' + ','.join(json.dumps(n) for n in required) + ')' if required else 'character()')
            # Windows Rscript -e must receive a single expression line.
            code = code.replace('{\n', '{').replace('\n}', '}').replace('\n', ';')
            code = code.replace('"', "'")
            out, error = run([rex, '--vanilla', '-e', code], renv)
            parsed = {}
            libraries = []
            for line in (out or '').splitlines():
                fields = line.strip().split('\t')
                if len(fields) >= 2 and fields[0] == 'AR_READY_LIBS':
                    libraries = fields[1].split('|')
                if len(fields) >= 4 and fields[0] == 'AR_READY_PACKAGE':
                    parsed[fields[1]] = fields[2:4]
            rows.append(row('R libraries', 'ready' if libraries and not error else 'blocked',
                            'Libraries inspected: ' + '; '.join(libraries) if libraries and not error else 'Selected library/probe unavailable.',
                            path=str(r_library) if r_library is not None else None, link=LINKS['r']))
            for name in required:
                value = parsed.get(name, [])
                ready = not error and len(value) == 2 and value[0] == 'ready' and VERSION.fullmatch(value[1])
                rows.append(row('R: '+name, 'ready' if ready else 'blocked',
                    'Namespace loads; officer also requires run_tab.' if ready else 'Missing/load failure, incompatible capability or unresolved probe; review selected R library.',
                    version=value[1] if ready else None, path=rex, link=LINKS['r']))
        else:
            rows.append(row('R packages', 'not checked', 'Resolve selected R first.', link=LINKS['r']))
    else:
        rows.append(row('R', 'not needed', 'R work was not selected.'))
    if 'site' in goals:
        item, _ = tool('Quarto', selected(quarto, 'quarto'), ['--version'], env, LINKS['quarto'])
        rows.append(item)
    else:
        rows.append(row('Quarto', 'not needed', 'Website generation was not selected.'))
    if 'git' in goals:
        item, gex = tool('Git', selected(git, 'git'), ['--version'], env, LINKS['git'])
        rows.append(item)
        if gex:
            try:
                setup.git_preflight({'executable':gex}, Path(__file__).resolve().parent)
                rows.append(row('Git identity/signing', 'ready', 'Identity usable; signing disabled/unset. No identity values displayed.', link=LINKS['git']))
            except ValueError as error:
                # Only classified messages; never print Git output or identity.
                detail = 'Signing requires a reviewed manual workflow.' if 'signing' in str(error) else 'Identity/configuration probe blocked; review Git setup.'
                rows.append(row('Git identity/signing', 'blocked', detail, link=LINKS['git']))
        else:
            rows.append(row('Git identity/signing', 'not checked', 'Resolve Git first.', link=LINKS['git']))
    else:
        rows.append(row('Git', 'not needed', 'Git publication was not selected.'))
    rows.extend([row('Editor', 'not checked', 'Optional: use your chosen editor or authorized agent execution.'),
                 row('Zotero/connectors', 'not checked', 'Check selected integrations separately; installation does not prove access.'),
                 row('Remote access/Pages', 'not checked', 'No network requests made; reachability alone cannot prove write permission or deployment.')])
    return dict(rows=rows, goals=sorted(goals), network_checked=False, changed_settings=False,
                scope='Local observations only; no project scripts, rendering, installation or Git writes. Namespace loading may initialize trusted installed packages.')

def table(result):
    def cell(value):
        return str(value or '').replace('|', '/').replace('\n', ' ').replace('\r', ' ')
    lines = ['| Component | Status | Version | Next step / observation |',
             '| --- | --- | --- | --- |']
    for item in result['rows']:
        lines.append('| ' + ' | '.join(cell(item[k]) for k in ('component', 'status', 'version', 'detail')) + ' |')
        if item.get('guidance') and item['status'] in ('missing', 'blocked'):
            lines.append('| Guidance | | | '+item['guidance']+' |')
    return '\n'.join(lines)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--goal', action='append', choices=['records','cv','site','pdf','git'])
    for name in ('python','rscript','r-library','quarto','git'):
        p.add_argument('--'+name)
    p.add_argument('--package', action='append')
    p.add_argument('--legacy-ppt', action='store_true')
    p.add_argument('--format', choices=['json','table'], default='table')
    args = p.parse_args()
    result = report(args.goal or ['records'], args.python, args.rscript, args.r_library,
                    args.quarto, args.git, args.package, args.legacy_ppt)
    print(json.dumps(result, indent=2) if args.format == 'json' else table(result))

if __name__ == '__main__':
    main()
