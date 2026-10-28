"""Reviewed new-project setup execution; existing projects use their established workflow."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import uuid


def sibling(name):
    spec=importlib.util.spec_from_file_location('setup_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


init=sibling('initialize');approvals=sibling('approval_evidence')


public_paths=sibling('public_paths')

def excluded(relative):
    return public_paths.private_path(relative)


def manifest(folder):
    folder=init.plain(folder)
    if not folder.is_dir():raise ValueError('Reviewed source folder unavailable')
    result={}
    for path in sorted(folder.rglob('*')):
        init.plain(path)
        if path.is_file():result[path.relative_to(folder).as_posix()]=init.sha(path.read_bytes())
    return result



def executable(path):
    """Executable aliases are resolved separately from protected data/state paths."""
    requested=Path(path)
    if not requested.is_absolute() or '..' in requested.parts:
        raise ValueError('Executable needs an explicit absolute path')
    try:
        resolved=requested.resolve(strict=True)
    except (OSError,RuntimeError):
        raise ValueError('Executable link is missing, inaccessible or cyclic; choose a working installed executable') from None
    if not resolved.is_file() or requested.suffix.lower() in ('.cmd','.bat') or resolved.suffix.lower() in ('.cmd','.bat'):
        raise ValueError('Use a verified executable, not a shell wrapper or directory')
    if os.name!='nt' and not os.access(resolved,os.X_OK):
        raise ValueError('Resolved executable is not executable; review the installation')
    return resolved


def executable_snapshot(path):
    resolved=executable(path)
    stat=resolved.stat()
    return dict(requested=str(path),resolved=str(resolved),sha256=init.sha(resolved.read_bytes()),
                owner=getattr(stat,'st_uid',None),mode=stat.st_mode)


def bind_executables(spec):
    normalized=copy.deepcopy(spec);bindings=[]
    if not isinstance(normalized,dict):return normalized,bindings
    steps=normalized.get('steps')
    if isinstance(steps,list):
        for step in steps:
            if isinstance(step,dict) and isinstance(step.get('argv'),list) and step['argv'] and isinstance(step['argv'][0],str):
                snapshot=executable_snapshot(step['argv'][0]);bindings.append(snapshot)
                step['argv'][0]=snapshot['resolved']
    git=normalized.get('git')
    if isinstance(git,dict) and isinstance(git.get('executable'),str):
        snapshot=executable_snapshot(git['executable']);bindings.append(snapshot);git['executable']=snapshot['resolved']
    return normalized,bindings


def verify_executables(item):
    spec=item['specification']
    paths=[step['argv'][0] for step in spec['steps']]
    if spec['git']:paths.append(spec['git']['executable'])
    bindings=item.get('executables')
    if bindings is None:
        if paths:raise ValueError('Legacy setup plan lacks executable identity; prepare and approve a fresh plan without modifying the old plan')
        return
    if not isinstance(bindings,list) or [b.get('resolved') for b in bindings]!=paths:
        raise ValueError('Setup executable bindings do not match reviewed commands')
    for snapshot in bindings:
        if executable_snapshot(snapshot['requested'])!=snapshot:
            raise ValueError('Reviewed executable target, bytes, ownership or mode changed; prepare and approve a fresh plan')


def reviewed_command(folder,label,argv,cwd,item):
    verify_executables(item)
    if not any(b['resolved']==argv[0] for b in item.get('executables',[])):
        raise ValueError('Command executable is outside the reviewed setup plan')
    return command(folder,label,argv,cwd)


def git_preflight(git, state):
    """Read-only checks; no repository, config writes, credentials or signing invocation."""
    import re
    environment = os.environ.copy()
    for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR',
                'GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        environment.pop(key, None)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    def probe(arguments):
        try:
            return subprocess.run([git['executable'], *arguments], cwd=state, env=environment,
                                  capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError('Git preflight could not run; resolve Git before creating the project') from error
    for identity in ('GIT_AUTHOR_IDENT', 'GIT_COMMITTER_IDENT'):
        result = probe(['-c', 'user.useConfigOnly=true', 'var', identity])
        value = result.stdout.decode('utf-8', errors='replace').strip()
        parsed = re.fullmatch(r'(.+) <([^<>]+)> -?\d+ [+-]\d{4}', value)
        if result.returncode or parsed is None or not parsed[1].strip() or not parsed[2].strip():
            raise ValueError('Git name/email is missing or unusable; configure author and committer identity with the user before creating the project. No Git settings were changed.')
    result = probe(['config', '--bool', '--get', 'commit.gpgsign'])
    if result.returncode not in (0, 1):
        raise ValueError('Git commit-signing configuration could not be read; resolve it before creating the project')
    if result.returncode == 0:
        value = result.stdout.strip().lower()
        if value not in (b'true', b'false'):
            raise ValueError('Git commit-signing configuration is unresolved')
        if value == b'true':
            raise ValueError('Git commit signing is enabled but noninteractive signing has not been verified. Resolve the signing workflow or use reviewed manual Git setup before creating the project; signing was not disabled.')
    return {'identity': 'usable', 'commit_signing': 'disabled_or_unset'}



def valid(spec,state):
    if not isinstance(spec,dict) or set(spec)!={'source','project','steps','git'}:raise ValueError('Setup specification needs source/project/steps/git')
    source=init.plain(spec['source']);project=init.plain(spec['project']);init.private(state,project)
    if source==project or source in project.parents or project in source.parents:raise ValueError('Source and destination must be separate')
    if project.exists() or not project.parent.is_dir():raise ValueError('New destination must not exist and its parent must exist')
    files=manifest(source)
    if not files or any(excluded(n) for n in files):raise ValueError('Source includes private/unsupported paths or is empty; prepare a reviewed public-source subset')
    if not isinstance(spec['steps'],list):raise ValueError('Steps must be an explicit list')
    for step in spec['steps']:
        if not isinstance(step,dict) or set(step)!={'name','argv','expected_files'}:raise ValueError('Each step needs name/argv/expected_files')
        if step['name'] not in ('configure','generate_cv','render_website','verify_outputs'):raise ValueError('Unsupported local stage; installations/account changes use separately approved host tools')
        argv=step['argv']
        if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x or '\x00' in x for x in argv):raise ValueError('Use an exact nonempty argument list, never a shell string')
        executable(argv[0])
        if not isinstance(step['expected_files'],list) or not step['expected_files']:raise ValueError('Each local stage needs expected output files')
        for name in step['expected_files']:
            path=Path(name)
            if path.is_absolute() or path.drive or '..' in path.parts:raise ValueError('Expected outputs must be project-relative')
    git=spec['git']
    if git is not None:
        import re
        if not isinstance(git,dict) or set(git)!={'executable','branch','remote','commit_roots','publication_mode'}:raise ValueError('Git plan needs executable/branch/remote/commit_roots/publication_mode')
        executable(git['executable'])
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*',git['branch']) or '..' in git['branch'] or git['branch'].endswith(('.','/')):raise ValueError('Invalid branch')
        if git['remote'] is not None and not re.fullmatch(r'https://github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:[.]git)?',git['remote']):raise ValueError('Use an explicitly reviewed HTTPS GitHub repository, without credentials')
        if git['publication_mode'] not in ('hold_for_review','after_verified_preview'):raise ValueError('Choose final-review or explicitly authorized preview-based publication')
        if not isinstance(git['commit_roots'],list) or not git['commit_roots'] or any(excluded(n) for n in git['commit_roots']):raise ValueError('Commit roots must be explicit public paths; never blanket stage')
        git_preflight(git, state)
    return files


def plan(state,spec):
    with init.lock(state):
        init.load(state);spec,bindings=bind_executables(spec);files=valid(spec,state);ident=uuid.uuid4().hex
        document=dict(id=ident,created=init.now(),specification=spec,source_files=files,executables=bindings,
                      scope='Create new project from exact reviewed source, run exact local commands, optionally create local Git commit. No implicit installation, repository creation or push.')
        folder=state/'setup-plans'/ident;init.plain(folder);folder.mkdir(parents=True)
        raw=init.encode(document);init.exclusive(folder/'plan.json',raw)
        return dict(id=ident,sha256=init.sha(raw),destination=spec['project'],files=files,steps=spec['steps'],git=spec['git'],executables=bindings,status='awaiting_exact_setup_approval')


def read_plan(state,ident):
    if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Invalid setup plan ID')
    folder=init.plain(state/'setup-plans'/ident);raw=(folder/'plan.json').read_bytes();document=init.decode(raw)
    if document['id']!=ident:raise ValueError('Plan identity changed')
    return folder,document,raw


def command(folder,label,argv,cwd):
    # Logs remain private; a failure is reported without echoing source/private content.
    environment=os.environ.copy()
    for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        environment.pop(key,None)
    environment['GIT_TERMINAL_PROMPT']='0'
    result=subprocess.run(argv,cwd=cwd,env=environment,capture_output=True,timeout=600)
    init.exclusive(folder/(label+'.stdout'),result.stdout);init.exclusive(folder/(label+'.stderr'),result.stderr)
    if result.returncode:raise ValueError('Setup stage failed: '+label+'; inspect private logs and actual partial state')
    return result.stdout.decode('utf-8',errors='replace').strip()


def public_files(project,roots):
    found={}
    for relative in roots:
        if excluded(relative):raise ValueError('Private commit root refused')
        path=init.plain(project/relative)
        if not path.exists():raise ValueError('Expected public commit root missing: '+relative)
        entries=path.rglob('*') if path.is_dir() else [path]
        for file in entries:
            init.plain(file)
            if not file.is_file():continue
            name=file.relative_to(project).as_posix()
            if excluded(name):raise ValueError('Private/unexpected file inside public commit root: '+name)
            found[name]=init.sha(file.read_bytes())
    if not found:raise ValueError('No public files to commit')
    return found


def execute(state,ident,evidence):
    with init.lock(state):
        init.load(state);folder,item,raw=read_plan(state,ident)
        def run(folder,label,argv,cwd):return reviewed_command(folder,label,argv,cwd,item)
        if (folder/'started.json').exists():raise ValueError('Execution already attempted; inspect actual state, do not rerun blindly')
        verify_executables(item)
        spec=item['specification'];files=valid(spec,state)
        if files!=item['source_files']:raise ValueError('Reviewed source changed; prepare and approve a fresh plan')
        expected=approvals.target('setup',ident,init.sha(raw),spec['project'])
        approval=approvals.read(state,evidence,expected);reference=approvals.persist(folder,approval,expected)
        init.exclusive(folder/'started.json',init.encode(dict(created=init.now(),approval_evidence=reference)))
        project=Path(spec['project'])
        try:
            project.mkdir()
            for name,digest in files.items():
                source=init.plain(Path(spec['source'])/name)
                data=source.read_bytes()
                if init.sha(data)!=digest:raise ValueError('Source changed during copy')
                target=project/name;target.parent.mkdir(parents=True,exist_ok=True);init.exclusive(target,data)
            for index,step in enumerate(spec['steps']):
                run(folder,'step-'+str(index),step['argv'],project)
                for name in step['expected_files']:
                    output=init.plain(project/name)
                    if not output.is_file() or output.stat().st_size==0:raise ValueError('Expected output missing/empty: '+name)
                init.exclusive(folder/('step-'+str(index)+'.json'),init.encode(dict(name=step['name'],status='command_and_expected_files_verified',visual_review=False)))
            git=spec['git'];commit=None;public={}
            if git:
                exe=git['executable'];public=public_files(project,git['commit_roots'])
                run(folder,'git-init',[exe,'init','-b',git['branch']],project)
                # A new repository may still resolve an external worktree via environment.
                top=run(folder,'git-root',[exe,'rev-parse','--show-toplevel'],project)
                if Path(top).resolve()!=project.resolve():raise ValueError('Git context escaped selected project')
                hooks=project/'.git/hooks'
                if hooks.exists() and any(f.is_file() and not f.name.endswith('.sample') for f in hooks.iterdir()):raise ValueError('Unexpected enabled Git hooks require review; do not bypass them')
                ordered=sorted(public)
                for index in range(0,len(ordered),64):run(folder,'git-add-'+str(index),[exe,'add','--',*ordered[index:index+64]],project)
                staged=run(folder,'git-staged',[exe,'diff','--cached','--name-only','-z'],project).split('\x00')
                if set(filter(None,staged))!=set(public):raise ValueError('Unexpected staged files; stop before commit')
                if public_files(project,git['commit_roots'])!=public:raise ValueError('Public files changed during staging')
                run(folder,'git-commit',[exe,'commit','-m','Initialize reviewed academic records project'],project)
                commit=run(folder,'git-head',[exe,'rev-parse','HEAD'],project)
                object_format=run(folder,'git-object-format',[exe,'rev-parse','--show-object-format'],project)
                if object_format not in ('sha1','sha256'):raise ValueError('Unsupported Git object format')
                tree=run(folder,'git-tree',[exe,'ls-tree','-rz','HEAD'],project)
                actual={}
                for entry in filter(None,tree.split('\x00')):
                    metadata,name=entry.split('\t',1);mode,kind,oid=metadata.split(' ')
                    if kind!='blob' or mode not in ('100644','100755'):raise ValueError('Unexpected Git tree entry')
                    actual[name]=oid
                expected_tree={}
                for name in public:
                    data=(project/name).read_bytes();expected_tree[name]=hashlib.new(object_format,b'blob '+str(len(data)).encode()+b'\x00'+data).hexdigest()
                if actual!=expected_tree:raise ValueError('Committed bytes differ from reviewed public files; inspect filters or extra entries')
                if git['remote']:run(folder,'git-remote',[exe,'remote','add','origin',git['remote']],project)
            result=dict(id=ident,project=str(project),created=init.now(),local_commands_verified=True,
                        visual_review=False,commit=commit,public_files=public,pushed=False,
                        next='Review/verify generated outputs and public content; publication remains gated')
            init.exclusive(folder/'completed.json',init.encode(result));return result
        except Exception as error:
            init.exclusive(folder/'failed.json',init.encode(dict(created=init.now(),status='failed_or_uncertain',project_exists=project.exists(),error_type=type(error).__name__,note='Preserve partial files/logs. No rollback, cleanup or retry is automatic.')))
            raise


def publish(state,ident,report_path,evidence=None):
    with init.lock(state):
        init.load(state);folder,item,raw=read_plan(state,ident);spec=item['specification'];git=spec['git']
        verify_executables(item)
        def run(folder,label,argv,cwd):return reviewed_command(folder,label,argv,cwd,item)
        if not git or not git['remote']:raise ValueError('No approved GitHub push destination')
        if (folder/'push-started.json').exists():raise ValueError('Push already attempted; inspect remote state before any retry')
        completed=init.decode((folder/'completed.json').read_bytes());project=init.plain(spec['project'])
        report_path=init.plain(report_path)
        if state not in report_path.parents:raise ValueError('Keep verification report in private setup state')
        report=init.decode(report_path.read_bytes())
        if report.get('plan_id')!=ident or report.get('commit')!=completed['commit'] or report.get('public_files')!=completed['public_files']:raise ValueError('Verification report does not match committed public bytes')
        if not isinstance(report.get('reference'),str) or not report['reference'].strip() or any(report.get(k) is not True for k in ('factual_review','privacy_review','visual_review','link_review','repository_identity_and_visibility_verified')):raise ValueError('Actual preview/privacy/factual/link/repository verification is required; flags alone are not proof')
        exe=git['executable']
        head=run(folder,'publish-head-'+uuid.uuid4().hex,[exe,'rev-parse','HEAD'],project)
        branch=run(folder,'publish-branch-'+uuid.uuid4().hex,[exe,'branch','--show-current'],project)
        remote=run(folder,'publish-remote-'+uuid.uuid4().hex,[exe,'remote','get-url','origin'],project)
        if head!=completed['commit'] or branch!=git['branch'] or remote!=git['remote'] or public_files(project,git['commit_roots'])!=completed['public_files']:raise ValueError('Git/public state changed since verification')
        if git['publication_mode']=='hold_for_review':
            target=approvals.target('publication',ident,init.sha(init.encode(dict(commit=head,remote=remote,branch=branch,public_files=completed['public_files']))),remote_destination(state,ident))
            # Destination is the private publication request, whose contents bind the remote.
            publication_raw=approvals.read(state,evidence,target)
            publication_folder=init.plain(folder/'publication');publication_folder.mkdir(exist_ok=True)
            approvals.persist(publication_folder,publication_raw,target)
        else:
            started=init.decode((folder/'started.json').read_bytes())
            approvals.verify(folder,started['approval_evidence'],approvals.target('setup',ident,init.sha(raw),spec['project']))
        init.exclusive(folder/'push-started.json',init.encode(dict(created=init.now(),commit=head,remote=remote,verification_sha256=init.sha(report_path.read_bytes()))))
        run(folder,'git-push',[exe,'push','--porcelain','origin','HEAD:refs/heads/'+git['branch']],project)
        result=dict(status='push_command_succeeded',commit=head,remote=remote,deployment_verified=False)
        init.exclusive(folder/'pushed.json',init.encode(result));return result


def remote_destination(state,ident):return state/'setup-plans'/ident/'publication-request.json'


def publication_request(state,ident):
    folder,item,_=read_plan(state,ident);done=init.decode((folder/'completed.json').read_bytes());git=item['specification']['git']
    payload=dict(commit=done['commit'],remote=git['remote'],branch=git['branch'],public_files=done['public_files'])
    path=init.plain(remote_destination(state,ident));raw=init.encode(payload)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Publication request changed; preserve history and reconcile')
    else:init.exclusive(path,raw)
    return dict(id=ident,sha256=init.sha(init.encode(payload)),destination=str(remote_destination(state,ident)),request=payload)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('plan');a.add_argument('state',type=Path);a.add_argument('specification',type=Path)
    a=sub.add_parser('execute');a.add_argument('state',type=Path);a.add_argument('id');a.add_argument('--approval-evidence',type=Path,required=True)
    a=sub.add_parser('publish');a.add_argument('state',type=Path);a.add_argument('id');a.add_argument('verification',type=Path);a.add_argument('--approval-evidence',type=Path)
    a=sub.add_parser('publication-request');a.add_argument('state',type=Path);a.add_argument('id')
    a=p.parse_args()
    if a.command=='plan':result=plan(a.state,init.decode(a.specification.read_bytes()))
    elif a.command=='execute':result=execute(a.state,a.id,a.approval_evidence)
    elif a.command=='publication-request':result=publication_request(a.state,a.id)
    else:result=publish(a.state,a.id,a.verification,a.approval_evidence)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try: main()
    except (OSError,ValueError,subprocess.SubprocessError) as error:raise SystemExit(str(error))
