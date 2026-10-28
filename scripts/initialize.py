"""Private, resumable initialization staging. No installs, record saves or publishing."""
import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import uuid
import zipfile
from xml.etree import ElementTree as ET

QUESTIONS = (
    ('outputs', 'Would you like a CV, a website, or both?', ('cv', 'website', 'both')),
    ('starting_point', 'Do you already have a website or a local records project?', ('fresh', 'existing_website', 'existing_local_project')),
    ('website_cv', 'Would you like a public CV PDF available on your website?', ('yes', 'no', 'defer')),
    ('cv_format', 'Would you like your private CV as Word only, or Word and PDF?', ('docx', 'docx_pdf', 'defer')),
    ('cv_source', 'Which current CV should be the initial source? You can skip this for now.', None),
    ('project_path', 'Which local project folder should be used or created? You can defer this.', None),
    ('assistance', 'Would you prefer guidance, prepared changes, or approved execution?', ('guidance', 'prepared_changes', 'approved_execution')),
    ('github_account', 'If GitHub is relevant, do you have an account or want help setting one up?', ('have_account', 'need_help', 'not_needed', 'defer')),
    ('integrations', 'Which optional integrations would you like to consider? You can choose none.', None),
)


def applicable_questions(answers):
    """Skip irrelevant output choices without inventing or deleting saved answers."""
    for item in QUESTIONS:
        key = item[0]
        if key == 'website_cv' and answers.get('outputs') not in ('website', 'both'):
            continue
        if key == 'cv_format' and answers.get('outputs') not in ('cv', 'both'):
            continue
        yield item


def cv_output_choices(answers):
    """Preferences only; never enable conversion, public files or publication."""
    goals = answers.get('outputs')
    private_format = answers.get('cv_format', 'pending') if goals in ('cv', 'both') else 'not_requested'
    public_cv = answers.get('website_cv', 'pending') if goals in ('website', 'both') else 'not_requested'
    return dict(private_format=private_format, website_cv=public_cv,
                pdf_generation_requested=private_format == 'docx_pdf' or public_cv == 'yes',
                implementation='separate reviewed source adaptation required; bundled starter is Word-only',
                public_use_approved=False, publication_approved=False)


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def encode(value): return (json.dumps(value, indent=2, ensure_ascii=False)+'\n').encode('utf-8')
def decode(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise ValueError('Duplicate JSON key')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Invalid JSON number')))


def plain(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts: raise ValueError('Explicit absolute path required')
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and part.resolve() != part):
            raise ValueError('Redirected path refused for protected source/project/private state; choose a direct authorized path. Executable links use the separate setup executable resolver.')
    return path


def private(state, project=None):
    state = plain(state)
    if not state.is_dir(): raise ValueError('Choose an existing authorized private storage directory first')
    if state == Path(state.anchor): raise ValueError('Filesystem root is not private initialization storage')
    if any((part/'.git').exists() for part in (state, *state.parents)):
        raise ValueError('Initialization state must be outside a Git repository')
    if project:
        project = plain(project)
        if state == project or project in state.parents or state in project.parents:
            raise ValueError('Private initialization storage and project must be separate')
    return state


def exclusive(path, raw):
    plain(path)
    with path.open('xb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())


@contextlib.contextmanager
def lock(state):
    state = private(state);path = state/'.initialization-writer.lock'
    try:
        exclusive(path, encode({'token':uuid.uuid4().hex,'created':now()}))
    except FileExistsError:
        raise FileExistsError('Initialization writer lock already exists at ' + str(path) +
                              '; an operation may be active or interrupted. Preserve the lock and history; '
                              'inspect the actual operation before reviewed recovery. Do not delete the lock or retry blindly.') from None
    try: yield
    finally: path.unlink()


def load(state):
    private(state); value = decode(plain(state/'initialization.json').read_bytes())
    if value.get('schema_version') != 1 or not isinstance(value.get('answers'),dict):
        raise ValueError('Unsupported initialization state; preserve it for reviewed recovery')
    project=value['answers'].get('project_path')
    if project: private(state,project)
    return value


def save(state,value,before=None):
    target=state/'initialization.json'
    if before is not None:
        if target.read_bytes()!=before: raise ValueError('Initialization state changed; reload before proceeding')
        folder=state/'initialization-history';plain(folder);folder.mkdir(exist_ok=True)
        exclusive(folder/(uuid.uuid4().hex+'.json'),before)
    elif target.exists(): raise ValueError('Initialization already exists; resume it')
    raw=encode(value);temp=state/('.initialization-'+uuid.uuid4().hex+'.tmp')
    exclusive(temp,raw)
    os.replace(temp,target)
    if target.read_bytes()!=raw: raise ValueError('Initialization save verification failed')


def status(state):
    value=load(state)
    pending=next((dict(id=key,question=question,choices=choices) for key,question,choices in applicable_questions(value['answers']) if key not in value['answers']),None)
    staging=[]
    folder=plain(state/'initialization-staging')
    if folder.exists():
        for operation in sorted(folder.iterdir()):
            plain(operation)
            if not operation.is_dir(): continue
            complete=plain(operation/'completed.json')
            staging.append(dict(folder=str(operation),status='staged' if complete.is_file() else 'interrupted_or_in_progress',
                                result=decode(complete.read_bytes()).get('result') if complete.is_file() else None))
    return dict(state=value,next_question=pending,questionnaire_complete=pending is None,
                cv_output_choices=cv_output_choices(value['answers']),
                profile_created=(state/'config.json').is_file(),
                staged_operations=staging,
                note='Questionnaire completion is not import, tool readiness, project creation or scheduling success.')


def start(state, confirmed, reference):
    if not confirmed or not reference.strip(): raise ValueError('Actual private-storage choice/reference required')
    with lock(state):
        if (state/'config.json').exists(): raise ValueError('Existing profile found; use configure-academic-records, do not restart initialization')
        save(state,dict(schema_version=1,id=uuid.uuid4().hex,created=now(),answers={},history=[],
                        storage_reference=reference,readiness={'questionnaire':'in_progress','import':'pending','project':'pending'}))
    return status(state)


def answer(state,incoming):
    if not isinstance(incoming,dict) or set(incoming)!={'key','value','response','reference'} or not all(isinstance(incoming.get(k),str) and incoming[k].strip() for k in ('key','response','reference')):
        raise ValueError('Record one actual answer with its response and reference')
    key=incoming['key']; value=incoming['value'];questions={k:c for k,_,c in QUESTIONS}
    if key not in questions: raise ValueError('Unsupported initialization question')
    choices=questions[key]
    if choices and value not in choices: raise ValueError('Unsupported answer choice')
    if key in ('cv_source','project_path') and value is not None:
        if not isinstance(value,str):raise ValueError('Path answers must be absolute text or explicitly deferred null')
        path=plain(value)
        if key=='cv_source' and not path.is_file(): raise ValueError('Selected CV source is unavailable')
        if key=='project_path': private(state,path)
        value=str(path)
    if key=='integrations' and (not isinstance(value,list) or any(v not in ('zotero','email','calendar','github','editor_extensions') for v in value) or len(value)!=len(set(value))):
        raise ValueError('Use supported optional integrations or an empty list')
    with lock(state):
        raw=(state/'initialization.json').read_bytes();record=load(state)
        if (state/'config.json').exists(): raise ValueError('Profile now exists; resume canonical configuration rather than changing bootstrap answers')
        record['answers'][key]=value;record['history'].append(dict(incoming,recorded_at=now()))
        record['updated']=now();save(state,record,raw)
    return status(state)


def transaction(state,label,writer):
    folder=state/'initialization-staging';plain(folder);folder.mkdir(exist_ok=True)
    target=folder/(label+'-'+uuid.uuid4().hex);target.mkdir()
    exclusive(target/'operation.json',encode({'status':'started','created':now(),'label':label}))
    result=writer(target)
    exclusive(target/'completed.json',encode({'status':'staged','created':now(),'result':result}))
    return result


def extract(state, source, approved, screening, reference):
    if not approved or screening!='not_flagged' or not reference.strip(): raise ValueError('Screen source first and obtain actual private processing approval; flagged sources stay blocked')
    source=plain(source)
    if not source.is_file() or source.suffix.lower() not in ('.docx','.pdf','.txt'):
        raise ValueError('Supported CV sources are DOCX, text PDF and UTF-8 TXT')
    with lock(state):
        record=load(state)
        if record['answers'].get('cv_source')!=str(source): raise ValueError('Confirm this CV as the selected source before extraction')
        raw=source.read_bytes();digest=sha(raw);segments=[];limits=[]
        if len(raw)>32*1024*1024: raise ValueError('CV exceeds the 32 MiB extraction limit')
        if source.suffix.lower()=='.docx':
            with zipfile.ZipFile(source) as z:
                if sum(i.file_size for i in z.infolist())>64*1024*1024: raise ValueError('Expanded DOCX exceeds extraction limit')
                for name in ['word/document.xml',*sorted(n for n in z.namelist() if n.startswith(('word/header','word/footer')) and n.endswith('.xml'))]:
                    root=ET.fromstring(z.read(name)); ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    if root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'):
                        limits.append('Drawing/image content is not OCRed')
                    for i,p in enumerate(root.findall('.//w:p',ns),1):
                        text=''.join(t.text or '' for t in p.findall('.//w:t',ns)).strip()
                        if text: segments.append({'location':name+':paragraph-'+str(i),'text':text})
                if any(n in z.namelist() for n in ('word/footnotes.xml','word/endnotes.xml','word/comments.xml')):
                    limits.append('Footnotes/endnotes/comments require separate inspection; not included in extracted text')
            limits.append('Paragraph/table text extraction does not establish visual reading order or entry completeness')
        elif source.suffix.lower()=='.pdf':
            try:
                from pypdf import PdfReader
            except ImportError:
                raise ValueError('PDF extraction requires a working pypdf installation in the selected Python interpreter. '
                                 'Verify the configured runtime/library, request permission for installation or repair, '
                                 'or provide a readable DOCX/TXT source. No packages were installed.') from None
            reader=PdfReader(source)
            if reader.is_encrypted: raise ValueError('Encrypted PDF requires a separately reviewed source')
            for i,page in enumerate(reader.pages,1):
                text=page.extract_text() or ''
                if not text.strip(): limits.append('Page '+str(i)+' has no extractable text; OCR/manual review required')
                for line,text in enumerate(text.splitlines(),1):
                    if text.strip():segments.append({'location':'page-'+str(i)+':line-'+str(line),'text':text.strip()})
            limits.append('PDF text order/layout is unverified; no OCR or visual completeness claimed')
        else:
            for i,text in enumerate(raw.decode('utf-8').splitlines(),1):
                if text.strip():segments.append({'location':'line-'+str(i),'text':text.strip()})
        if not segments: raise ValueError('No extractable CV text; obtain a readable source or manual transcription')
        if sha(source.read_bytes())!=digest: raise ValueError('Source changed during extraction')
        for i,s in enumerate(segments,1):s['id']='S'+str(i).zfill(5)
        def write(folder):
            result=dict(source_sha256=digest,source_name=source.name,segments=segments,limitations=limits,
                        processing_reference=reference,public_use_approved=False)
            exclusive(folder/'extracted.json',encode(result))
            return dict(folder=str(folder),source_sha256=digest,segment_count=len(segments),limitations=limits,
                        next='Review text and construct candidate/coverage ledger privately; nothing imported')
        return transaction(state,'cv',write)



def output_coverage_report(candidates, requested):
    """Validate private operator assessments; do not infer consumers or render success."""
    if requested not in (None, 'cv', 'website', 'both'):
        raise ValueError('Unsupported output goal')
    active=('cv','website') if requested in (None,'both') else (requested,)
    rows=[]
    for candidate in candidates:
        supplied=candidate.get('output_coverage',{})
        if not isinstance(supplied,dict) or set(supplied)-{'cv','website'}:
            raise ValueError('Output coverage needs cv/website assessments')
        outputs={}
        for output in ('cv','website'):
            assessment=supplied.get(output)
            if assessment is not None:
                if not isinstance(assessment,dict) or set(assessment)!={'status','reason','reference'}:
                    raise ValueError('Output assessment needs status, reason and reference')
                if assessment['status'] not in ('included','excluded','unsupported','pending'):
                    raise ValueError('Unsupported output assessment status')
                if not all(isinstance(assessment[k],str) and assessment[k].strip() for k in ('reason','reference')):
                    raise ValueError('Output assessment needs actual consumer/review references')
            if output not in active:
                outputs[output]=dict(status='not_requested',reason='Outside selected output goals',reference=None)
            elif assessment is None:
                outputs[output]=dict(status='pending',reason='Actual consumer coverage not assessed',reference=None)
            else:
                outputs[output]=dict(assessment)
        statuses=[outputs[o]['status'] for o in active]
        if requested is None or 'pending' in statuses:label='Pending'
        else:
            included=[o for o in active if outputs[o]['status']=='included']
            label='Both' if len(included)==2 else ('CV only' if included==['cv'] else ('Website only' if included==['website'] else 'Neither'))
        rows.append(dict(candidate_id=candidate['id'],target=candidate['target'],outputs=outputs,display=label))
    return dict(requested_outputs=requested,rows=rows,
                basis='operator_consumer_assessments_not_render_verification',
                user_review='pending; omissions need explicit acceptance or a separately scoped consumer change')


def stage_ledger(state,extracted_path,ledger):
    with lock(state):
        load(state);path=plain(extracted_path)
        if state not in path.parents: raise ValueError('Extraction must be in the private initialization state')
        source=decode(path.read_bytes());ids={s['id'] for s in source['segments']}
        if not isinstance(ledger,dict) or ledger.get('source_sha256')!=source['source_sha256']: raise ValueError('Ledger refers to a different source')
        coverage=ledger.get('coverage');candidates=ledger.get('candidates')
        if not isinstance(coverage,list) or not isinstance(candidates,list): raise ValueError('Ledger needs coverage and candidate lists')
        if any(not isinstance(x,dict) for x in coverage+candidates):raise ValueError('Coverage and candidates must contain objects')
        if len(coverage)!=len(ids) or {x.get('source_id') for x in coverage}!=ids: raise ValueError('Every extracted segment must be accounted for once')
        candidate_ids=[x.get('id') for x in candidates]
        if any(not isinstance(x,str) or not x for x in candidate_ids) or len(set(candidate_ids))!=len(candidate_ids): raise ValueError('Candidates need unique IDs')
        targets={'education.yml','training.yml','appointments.yml','certifications.yml','memberships.yml','honors.yml','service.yml','grants.yml','talks.yml','abstracts.yml','teaching.yml','mentoring.yml','projects.yml','media.yml','zotero'}
        for c in candidates:
            if c.get('target') not in targets or not isinstance(c.get('record'),dict) or not c.get('source_ids') or not set(c['source_ids']).issubset(ids): raise ValueError('Candidate needs a supported destination, fields and source references')
        for row in coverage:
            if row.get('disposition') not in ('candidate','context','excluded','unresolved') or not isinstance(row.get('reason'),str) or not row['reason'].strip(): raise ValueError('Coverage needs a disposition and explanation')
            links=row.get('candidate_ids',[])
            if not isinstance(links,list) or not set(links).issubset(candidate_ids) or (row['disposition']=='candidate' and not links): raise ValueError('Candidate coverage needs matching candidate IDs')
            if any(row['source_id'] not in next(c['source_ids'] for c in candidates if c['id']==link) for link in links): raise ValueError('Coverage and candidate provenance disagree')
        for c in candidates:
            if any(not any(row['source_id']==s and c['id'] in row.get('candidate_ids',[]) for row in coverage) for s in c['source_ids']):raise ValueError('Every candidate source needs a reciprocal coverage link')
        report=output_coverage_report(candidates,load(state)['answers'].get('outputs'))
        def write(folder):
            exclusive(folder/'ledger.json',encode(ledger))
            exclusive(folder/'output-coverage.json',encode(report))
            return dict(folder=str(folder),candidate_count=len(candidates),segments_accounted_for=len(ids),
                        output_coverage_path=str(folder/'output-coverage.json'),output_review_status='pending',
                        semantic_verification='pending assistant and human review; structural coverage is not proof of factual completeness',
                        imported=False)
        return transaction(state,'ledger',write)


def stage_starter(state,reference):
    if not reference.strip(): raise ValueError('Actual staging request reference required')
    with lock(state):
        bootstrap=load(state);archive=Path(__file__).parents[1]/'assets/starter.zip'
        def write(folder):
            with zipfile.ZipFile(archive) as z:
                if sum(m.file_size for m in z.infolist())>64*1024*1024:raise ValueError('Starter exceeds staging limit')
                for member in z.infolist():
                    name=Path(member.filename)
                    if name.is_absolute() or name.drive or '..' in name.parts or (member.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe starter archive path')
                    destination=folder/name;plain(destination)
                    if member.is_dir():destination.mkdir(parents=True,exist_ok=True)
                    else:
                        destination.parent.mkdir(parents=True,exist_ok=True);exclusive(destination,z.read(member))
            project_source_root=plain(folder/'starter')
            if not all((project_source_root/name).is_file() for name in ('_quarto.yml','R/cv.R')):
                raise ValueError('Staged starter lacks its expected project source root; preserve staging for inspection')
            return dict(folder=str(folder),metadata_folder=str(folder),project_source_root=str(project_source_root),
                        archive_sha256=sha(archive.read_bytes()),request_reference=reference,
                        cv_output_choices=cv_output_choices(bootstrap['answers']),
                        project_created=False,next='Review files under project_source_root only; retain metadata_folder privately and obtain exact setup approval before project creation')
        return transaction(state,'starter',write)


def probes():
    found={key:shutil.which(key) for key in ('Rscript','quarto','git','rstudio','code')}
    if os.name=='nt':
        for base in dict.fromkeys(filter(None,[os.environ.get('ProgramFiles'),'C:/Program Files'])):
            path=Path(base)/'RStudio/resources/app/bin/quarto/bin/quarto.exe'
            if not found['quarto'] and path.is_file():found['quarto']=str(path)
    return dict(executables=found,python_modules={name:importlib.util.find_spec(name) is not None for name in ('pypdf',)},
                status='paths observed only; versions, R packages and launch permissions still require read-only probes',
                github_account='ask only when GitHub is relevant; executable presence is not account/authentication evidence',installed_nothing=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('start');c.add_argument('state',type=Path);c.add_argument('--private-storage-confirmed',action='store_true');c.add_argument('--reference',required=True)
    for name in ('status','probe'):
        c=sub.add_parser(name)
        if name=='status':c.add_argument('state',type=Path)
    c=sub.add_parser('answer');c.add_argument('state',type=Path);c.add_argument('input',type=Path)
    c=sub.add_parser('extract');c.add_argument('state',type=Path);c.add_argument('source',type=Path);c.add_argument('--private-processing-approved',action='store_true');c.add_argument('--source-screening',choices=('not_flagged','flagged'),required=True);c.add_argument('--reference',required=True)
    c=sub.add_parser('ledger');c.add_argument('state',type=Path);c.add_argument('extracted',type=Path);c.add_argument('input',type=Path)
    c=sub.add_parser('stage-starter');c.add_argument('state',type=Path);c.add_argument('--reference',required=True)
    a=p.parse_args()
    if a.cmd=='start':result=start(a.state,a.private_storage_confirmed,a.reference)
    elif a.cmd=='status':result=status(a.state)
    elif a.cmd=='answer':result=answer(a.state,decode(a.input.read_bytes()))
    elif a.cmd=='extract':result=extract(a.state,a.source,a.private_processing_approved,a.source_screening,a.reference)
    elif a.cmd=='ledger':result=stage_ledger(a.state,a.extracted,decode(a.input.read_bytes()))
    elif a.cmd=='stage-starter':result=stage_starter(a.state,a.reference)
    else:result=probes()
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try: main()
    except (ValueError,OSError) as error: raise SystemExit(str(error))
