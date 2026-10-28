"""Stage/review new PDFs, then save approved bytes without replacing resources.

Requires pypdf. Local PowerPoint (including Store installations) or LibreOffice converts .ppt/.pptx.
Approval arguments assert prior human approval; they are not authentication.
"""
import argparse
import zipfile
import xml.etree.ElementTree as ET
import posixpath
import struct
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import uuid
import importlib.util

_approval_spec = importlib.util.spec_from_file_location('academic_approval_evidence',
    Path(__file__).with_name('approval_evidence.py'))
approvals = importlib.util.module_from_spec(_approval_spec)
_approval_spec.loader.exec_module(approvals)
_state_spec = importlib.util.spec_from_file_location('attachment_private_state',
    Path(__file__).with_name('private_state.py'))
private_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(private_state)



def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as out:
        json.dump(value, out, indent=2)


def settings(state):
    config_path = state / 'config.json'
    raw = config_path.read_bytes()
    config = json.loads(raw.decode('utf-8'))
    raw_root = config.get('project_root')
    if not isinstance(raw_root, str) or not Path(raw_root).is_absolute():
        raise ValueError('Explicit absolute project_root required')
    root = Path(raw_root).resolve(strict=True)
    if state == root or root in state.parents:
        raise ValueError('Private staging must be outside the project')
    if config.get('approval_policy') != 'per_change':
        raise ValueError('per_change approval required')
    options = config.get('attachments', {})
    dirs = options.get('approved_pdf_dirs')
    if not isinstance(dirs, list) or not dirs or any(not isinstance(d, str) for d in dirs):
        raise ValueError('Explicit attachments.approved_pdf_dirs required')
    return root, options, hashlib.sha256(raw).hexdigest()


def save_scope(root, options):
    """Version 1: canonical resolved root, per-change policy, all attachment settings.

    Whole-profile hashes remain evidence for conservative legacy compatibility.
    This digest detects changes; it is not approval authentication.
    """
    snapshot = dict(project_root=str(root), approval_policy='per_change', attachments=options)
    raw = json.dumps(snapshot, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def require_save_scope(item, root, options, config_hash):
    if 'save_scope_version' in item or 'save_scope_sha256' in item:
        if type(item.get('save_scope_version')) is not int or item['save_scope_version'] != 1:
            raise ValueError('Unsupported attachment save-scope version; reviewed reconciliation required')
        if item.get('save_scope_sha256') != save_scope(root, options):
            raise ValueError('Attachment settings changed; reconcile scope and obtain renewed review before saving')
    elif config_hash != item['config_sha256']:
        raise ValueError('Legacy staged attachment profile changed; relevant prior settings cannot '
                         'be established. Reviewed reconciliation required; no automatic approval migration')


def destination(root, options, relative):
    p = PurePosixPath(relative)
    if ('\\' in relative or ':' in relative or p.is_absolute() or
            '..' in p.parts or str(p) != relative or p.suffix.lower() != '.pdf'):
        raise ValueError('Use a normalized project-relative PDF path')
    if p.parts[0] not in ('abstracts', 'teaching', 'presentations'):
        raise ValueError('Outside supported resource roots')
    if str(p.parent) not in options['approved_pdf_dirs']:
        raise ValueError('PDF directory is not explicitly approved')
    # Refuse symlink/junction routes, not just escapes outside the project.
    parent = root
    for part in p.parts[:-1]:
        parent = parent / part
        if not parent.is_dir() or parent.is_symlink() or parent.resolve() != parent:
            raise ValueError('Missing or redirected destination directory')
    target = parent / p.name
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError('Redirected destination')
    return target


def pdf_pages(path):
    from pypdf import PdfReader
    with path.open('rb') as f:
        if f.read(5) != b'%PDF-':
            raise ValueError('Not a PDF')
    reader = PdfReader(str(path), strict=True)
    if reader.is_encrypted or len(reader.pages) == 0:
        raise ValueError('Encrypted or empty PDF requires review')
    return len(reader.pages)


def windows_host():
    return os.name == 'nt'


def powerpoint_shell(preferred=None):
    if not windows_host():
        return None
    shell = preferred or shutil.which('pwsh') or shutil.which('powershell')
    if shell:
        try:
            probe = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command',
                "if ($null -eq [type]::GetTypeFromProgID('PowerPoint.Application')) { exit 1 }"],
                capture_output=True, text=True, timeout=20)
        except PermissionError as error:
            raise ValueError('PowerPoint registration probe blocked by executable access; converter availability is unresolved') from error
        except subprocess.TimeoutExpired as error:
            raise ValueError('PowerPoint registration probe timed out; converter availability is unresolved') from error
        except OSError as error:
            raise ValueError('PowerPoint registration probe could not launch the selected shell; check its saved path and host access') from error
        if probe.returncode == 0:
            return shell
        if probe.returncode != 1:
            raise ValueError('PowerPoint registration probe failed (exit ' + str(probe.returncode) + '); converter availability is unresolved')
    return None


def libreoffice_executable(preferred=None):
    if preferred:
        path = Path(preferred)
        if not path.is_absolute() or not path.is_file():
            raise ValueError('Configured LibreOffice executable is unavailable; check its saved absolute path and host access')
        return str(path)
    found = shutil.which('soffice')
    if found:
        return found
    if windows_host():
        roots = [os.environ.get('ProgramW6432'), os.environ.get('ProgramFiles'),
                 os.environ.get('ProgramFiles(x86)'), 'C:/Program Files', 'C:/Program Files (x86)']
        checked = set()
        for root in roots:
            if not root:
                continue
            path = Path(root) / 'LibreOffice' / 'program' / 'soffice.exe'
            if path in checked:
                continue
            checked.add(path)
            if path.is_file():
                return str(path)
    return None


def resumable_attempt(folder, item, target):
    attempt = json.loads((folder / 'save-attempt.json').read_text(encoding='utf-8'))
    if (not isinstance(attempt, dict) or attempt.get('approval_assertion') != item['id'] or
            attempt.get('destination') != str(target) or attempt.get('pdf_sha256') != item['pdf_sha256'] or
            attempt.get('privacy_review_assertion') is not True or attempt.get('public_use_assertion') is not True):
        raise ValueError('Saved attachment attempt does not match reviewed bytes, destination and public/privacy approval')
    expected = approvals.target('attachment', item['id'], item['pdf_sha256'], target)
    approvals.verify(folder, attempt.get('approval_evidence'), expected)
    return attempt


def status(folder, item, target):
    staged = folder / 'material.pdf'
    if not staged.is_file() or digest(staged) != item['pdf_sha256']:
        return 'staged_changed'
    if target.exists():
        return 'saved_bytes_verified' if digest(target) == item['pdf_sha256'] else 'destination_conflict'
    if (folder / 'saved.json').exists():
        return 'missing_after_save'
    if (folder / 'save-attempt.json').exists():
        try:
            resumable_attempt(folder, item, target)
        except (ValueError, OSError, KeyError, TypeError):
            return 'save_attempt_invalid'
        return 'save_interrupted_before_copy'
    return 'awaiting_approval'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    stage = sub.add_parser('stage')
    stage.add_argument('state', type=Path)
    stage.add_argument('source', type=Path)
    stage.add_argument('relative_pdf')
    stage.add_argument('--source-screening',
                       choices=('not_screened', 'not_flagged', 'flagged'),
                       default='not_screened',
                       help='Operator initial-screen assertion; not full privacy clearance')
    stage.add_argument('--private-copy-approved', action='store_true',
                       help='Assert explicit approval to privately copy/convert PowerPoint before final visual review')
    for name in ('save', 'status'):
        command = sub.add_parser(name)
        command.add_argument('state', type=Path)
        command.add_argument('id')
        if name == 'save':
            command.add_argument('--resume', action='store_true',
                                 help='Resume an inspected attempt with no destination; original exact evidence required')
            command.add_argument('--approval', required=True)
            command.add_argument('--approval-evidence', type=Path, required=True)
            command.add_argument('--privacy-reviewed', action='store_true', required=True,
                                 help='Assert actual completed privacy review with no unresolved patient identifiers')
            command.add_argument('--public-approved', action='store_true', required=True,
                                 help='Assert explicit approval of the reviewed PDF for public website use')
    args = parser.parse_args()
    state = args.state.resolve(strict=True)
    root, options, config_hash = settings(state)
    if args.command == 'stage':
        target = destination(root, options, args.relative_pdf)
        if target.exists():
            raise ValueError('Destination already exists; review reuse or select a new filename')
        source = args.source.resolve(strict=True)
        ext = source.suffix.lower()
        if ext not in ('.pdf', '.ppt', '.pptx'):
            raise ValueError('Only PDF/PPT/PPTX supported')
        stage_attachment(args, state, root, options, config_hash, source, ext)
        return
    save_or_status(args, state, root, options, config_hash)




def powerpoint_format(path, ext):
    """Bounded format recognition, not complete Office validation or privacy clearance."""
    try:
        if ext == '.ppt':
            with path.open('rb') as stream:
                if stream.read(8) != bytes.fromhex('d0cf11e0a1b11ae1'):
                    raise ValueError('PPT is not a compound PowerPoint file')
            try:
                import olefile
            except ImportError:
                raise ValueError('Legacy PPT validation requires olefile; request a locally exported PDF/PPTX or authorize installation. No converter was probed.') from None
            with olefile.OleFileIO(str(path), raise_defects=olefile.DEFECT_INCORRECT) as ole:
                if ole.exists('EncryptedPackage') or ole.exists('EncryptionInfo'):
                    raise ValueError('Encrypted PowerPoint is unsupported')
                if not all(ole.exists(n) for n in ('PowerPoint Document', 'Current User')):
                    raise ValueError('PPT lacks PowerPoint streams')
                current=ole.openstream('Current User').read(32)
                if len(current)<28 or struct.unpack_from('<H',current,2)[0]!=4086:
                    raise ValueError('Invalid PPT Current User record')
                if struct.unpack_from('<I',current,12)[0]!=0xE391C05F:
                    raise ValueError('Encrypted or invalid PPT header token')
                offset=struct.unpack_from('<I',current,16)[0]
                document=ole.openstream('PowerPoint Document')
                if offset+8>ole.get_size('PowerPoint Document'):
                    raise ValueError('Invalid PPT edit offset')
                document.seek(offset);header=document.read(8)
                if len(header)!=8 or struct.unpack_from('<H',header,2)[0]!=4085:
                    raise ValueError('Invalid PPT UserEdit record')
                size=struct.unpack_from('<I',header,4)[0]
                if size not in (28,32) or offset+8+size>ole.get_size('PowerPoint Document'):
                    raise ValueError('Truncated PPT UserEdit record')
            return
        with zipfile.ZipFile(path) as package:
            entries=package.infolist();names=[e.filename for e in entries]
            if len(entries)>10000 or len(names)!=len(set(names)):
                raise ValueError('Duplicate or excessive PPTX package entries')
            if any(e.flag_bits & 1 or e.file_size>256*1024*1024 for e in entries) or sum(e.file_size for e in entries)>1024*1024*1024:
                raise ValueError('Encrypted or oversized PPTX package')
            if any('\\' in n or n.startswith('/') or '..' in n.split('/') for n in names):
                raise ValueError('Unsafe PPTX package paths')
            def xml(name):
                info=package.getinfo(name)
                if info.file_size>8*1024*1024:
                    raise ValueError('Oversized PPTX XML part')
                raw=package.read(name)
                # Reject DTD/entity syntax, including UTF-16/32 encodings, before parsing.
                probe=raw.replace(bytes([0]),b'').upper()
                if b'<!DOCTYPE' in probe or b'<!ENTITY' in probe:
                    raise ValueError('PPTX XML declarations are unsupported')
                return ET.fromstring(raw)
            types=xml('[Content_Types].xml')
            ct='http://schemas.openxmlformats.org/package/2006/content-types'
            relns='http://schemas.openxmlformats.org/package/2006/relationships'
            if types.tag!='{'+ct+'}Types':raise ValueError('Invalid PPTX content types')
            relationships=xml('_rels/.rels')
            if relationships.tag!='{'+relns+'}Relationships':raise ValueError('Invalid PPTX relationships')
            offices=('http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument',
                     'http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument')
            links=[r for r in relationships if r.tag=='{'+relns+'}Relationship' and r.get('Type') in offices]
            if len(links)!=1 or links[0].get('TargetMode','Internal')!='Internal':raise ValueError('Missing internal PPTX presentation relationship')
            target=links[0].get('Target','').lstrip('/')
            if not target or '\\' in target or '..' in target.split('/') or ':' in target:raise ValueError('Unsafe PPTX presentation target')
            target=posixpath.normpath(target)
            content='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'
            matches=[r for r in types if r.tag=='{'+ct+'}Override' and r.get('PartName')=='/'+target]
            if len(matches)!=1 or matches[0].get('ContentType')!=content:raise ValueError('Not a PPTX presentation content type')
            presentation=xml(target)
            if presentation.tag not in ('{http://schemas.openxmlformats.org/presentationml/2006/main}presentation',
                                         '{http://purl.oclc.org/ooxml/presentationml/main}presentation'):
                raise ValueError('Invalid PPTX presentation root')
            namespace=presentation.tag.split('}')[0]+'}'
            slides=presentation.findall(namespace+'sldIdLst/'+namespace+'sldId')
            if slides:
                relpath=posixpath.join(posixpath.dirname(target),'_rels',posixpath.basename(target)+'.rels')
                rels=xml(relpath)
                if rels.tag!='{'+relns+'}Relationships':raise ValueError('Invalid presentation relationships')
                mapping={r.get('Id'):r for r in rels}
                if len(mapping)!=len(rels):raise ValueError('Duplicate presentation relationship IDs')
                for slide in slides:
                    ids=[v for k,v in slide.attrib.items() if k in (
                        '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id',
                        '{http://purl.oclc.org/ooxml/officeDocument/relationships}id')]
                    if len(ids)!=1 or ids[0] not in mapping:raise ValueError('Missing slide relationship')
                    rel=mapping[ids[0]]
                    if rel.tag!='{'+relns+'}Relationship' or rel.get('Type') not in tuple(t.rsplit('/',1)[0]+'/slide' for t in offices) or rel.get('TargetMode','Internal')!='Internal':
                        raise ValueError('Invalid slide relationship')
                    part=rel.get('Target','')
                    if not part or '\\' in part or ':' in part:raise ValueError('Invalid slide target')
                    part=posixpath.normpath(part.lstrip('/') if part.startswith('/') else posixpath.join(posixpath.dirname(target),part))
                    if part.startswith('../'):raise ValueError('Slide target escapes package')
                    if xml(part).tag!=namespace+'sld':raise ValueError('Invalid slide XML root')
            # Read all entries in bounded chunks to verify CRC/truncation without extracting.
            for entry in entries:
                with package.open(entry) as stream:
                    while stream.read(1024*1024):pass
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('PowerPoint input is malformed or unreadable ('+type(exc).__name__+'); request a repaired deck or locally exported PDF') from None


def stage_attachment(args, state, root, options, config_hash, source, ext):
    # Reject declared identifiers before any copy, folder creation or converter probe.
    # These are human/operator assertions, never automated PHI detection.
    if args.source_screening == 'flagged':
        raise ValueError('Source is flagged; no private copy or conversion permitted. '
                         'Request a de-identified replacement.')
    if args.source_screening != 'not_flagged':
        kind = 'PowerPoint' if ext in ('.ppt', '.pptx') else 'PDF'
        raise ValueError(kind + ' requires an initial not-flagged source-screen assertion; '
                         'this is not full visual/privacy clearance')
    if ext in ('.ppt', '.pptx'):
        if not args.private_copy_approved:
            raise ValueError('PowerPoint conversion creates private copies before final visual '
                             'review; obtain explicit private-copy approval or request a '
                             'user-exported de-identified PDF')
        validated_hash = digest(source)
        powerpoint_format(source, ext)
        if digest(source) != validated_hash:
            raise ValueError('Source changed during PowerPoint format validation')
    ident = uuid.uuid4().hex
    folder = state / 'attachments' / ident
    folder.mkdir(parents=True, exist_ok=False)
    phase = 'private_preparation_receipt'
    try:
        write_json(folder / 'staging.json', dict(
            status='private_preparation_pending',
            review_status='pending_visual_privacy_review',
            source_screening_assertion=args.source_screening,
            private_copy_approval_assertion=args.private_copy_approved))
        original = folder / ('original' + ext)
        phase = 'source_copy'
        before = digest(source)
        if ext in ('.ppt', '.pptx') and before != validated_hash:
            raise ValueError('Source changed after PowerPoint format validation')
        shutil.copyfile(source, original)
        if digest(original) != before or digest(source) != before:
            raise ValueError('Source changed while staging')
        pdf = folder / 'material.pdf'
        method = 'original PDF'
        if ext == '.pdf':
            shutil.copyfile(original, pdf)
        else:
            phase = 'converter_discovery'
            config = json.loads((state / 'config.json').read_text(encoding='utf-8'))
            shell = powerpoint_shell(config.get('runtime', {}).get('powershell'))
            executable = libreoffice_executable(options.get('soffice')) if not shell else None
            if not shell and not executable:
                raise ValueError('No local PowerPoint or LibreOffice converter found in checked locations; availability outside those locations is unresolved; preserve pending request and obtain PDF')
            if shell:
                phase = 'powerpoint_conversion'
                result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-File',
                    str(Path(__file__).with_name('convert_powerpoint.ps1')),
                    '-Source', str(original), '-Destination', str(pdf)],
                    capture_output=True, text=True, timeout=180)
                if result.returncode != 0 or not pdf.is_file():
                    raise ValueError('Local PowerPoint export failed; no public file saved')
                method = 'local PowerPoint export; visual/privacy review required'
            else:
                phase = 'libreoffice_conversion'
                convert_libreoffice(executable, original, pdf)
                method = 'local LibreOffice export; visual/privacy review required'
        phase = 'pdf_validation'
        pages = pdf_pages(pdf)
        item = dict(id=ident, project_root=str(root), relative_pdf=args.relative_pdf,
                    source_name=source.name, source_sha256=before,
                    pdf_sha256=digest(pdf), pages=pages, method=method,
                    config_sha256=config_hash,
                    save_scope_version=1, save_scope_sha256=save_scope(root, options),
                    review_status='pending_visual_privacy_review',
                    source_screening_assertion=args.source_screening,
                    private_copy_approval_assertion=args.private_copy_approved)
        phase = 'manifest_write'
        write_json(folder / 'manifest.json', item)
        print(json.dumps(dict(item, status='awaiting_approval', staged_pdf=str(pdf)), indent=2))

    except Exception as error:
        try:
            write_json(folder / 'staging-failed.json', dict(
                status='preparation_failed', error_category=type(error).__name__,
                failure_phase=phase,
                review_status='pending_visual_privacy_review',
                private_files_may_remain=True))
        except OSError:
            pass  # Still surface the location when receipt creation also fails.
        raise ValueError('Attachment preparation failed during ' + phase +
                         '; private files may remain at ' +
                         str(folder) + '. Public saving/linking is paused. Inspect the '
                         'folder and obtain authorization before any cleanup.') from error


def convert_libreoffice(executable, original, pdf):
    with tempfile.TemporaryDirectory(prefix='academic-convert-', dir=pdf.parent) as tmp:
        temp = Path(tmp)
        result = subprocess.run([str(executable), '-env:UserInstallation=' + (temp / 'profile').as_uri(),
            '--headless', '--convert-to', 'pdf', '--outdir', str(temp), str(original)],
            capture_output=True, text=True, timeout=180)
        converted = temp / 'original.pdf'
        if result.returncode != 0 or not converted.is_file():
            raise ValueError('Local conversion failed; no public file saved')
        shutil.copyfile(converted, pdf)


def save_or_status(args, state, root, options, config_hash):
    if args.command == 'status':
        return save_or_status_locked(args, state, root, options, config_hash)
    with private_state.writer_lock(state):
        root, options, config_hash = settings(state)
        return save_or_status_locked(args, state, root, options, config_hash)


def save_or_status_locked(args, state, root, options, config_hash):
    if len(args.id) != 32 or any(c not in '0123456789abcdef' for c in args.id):
        raise ValueError('Invalid attachment ID')
    folder = state / 'attachments' / args.id
    item = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if item['id'] != args.id or item['project_root'] != str(root):
        raise ValueError('Attachment identity mismatch')
    target = destination(root, options, item['relative_pdf'])
    outcome = status(folder, item, target)
    if args.command == 'status':
        receipt = folder / 'saved.json'
        if not receipt.exists():
            receipt = folder / 'save-attempt.json'
        receipt_invalid = False
        try:
            reference = json.loads(receipt.read_text(encoding='utf-8')).get('approval_evidence') if receipt.exists() else None
        except (ValueError, OSError, AttributeError):
            reference = None
            receipt_invalid = True
        expected = approvals.target('attachment', item['id'], item['pdf_sha256'], target)
        resume_available = outcome == 'save_interrupted_before_copy'
        if resume_available:
            try:
                require_save_scope(item, root, options, config_hash)
            except ValueError:
                resume_available = False
        print(json.dumps(dict(status=outcome, resume_available=resume_available,
            destination=str(target), yaml_link='verify separately',
            save_receipt_present=(folder / 'saved.json').is_file(),
            approval_evidence_status='missing_or_changed' if receipt_invalid else approvals.status(folder, reference, expected))))
        return
    if args.approval != args.id:
        raise ValueError('Approval must name this exact reviewed attachment')
    require_save_scope(item, root, options, config_hash)
    allowed = 'save_interrupted_before_copy' if args.resume else 'awaiting_approval'
    if outcome != allowed:
        raise ValueError('Reconcile attachment status before save: ' + outcome +
                         '; use --resume only for an inspected interrupted attempt with no destination')
    original_attempt = resumable_attempt(folder, item, target) if args.resume else None
    pdf = folder / 'material.pdf'
    pdf_pages(pdf)
    # Recheck current scope/route and bytes after PDF parsing, before public creation.
    root, options, config_hash = settings(state)
    if item['project_root'] != str(root):
        raise ValueError('Attachment project identity changed before save')
    target = destination(root, options, item['relative_pdf'])
    require_save_scope(item, root, options, config_hash)
    if status(folder, item, target) != allowed:
        raise ValueError('Attachment bytes or destination changed before save; reconcile before retry')
    expected = approvals.target('attachment', item['id'], item['pdf_sha256'], target)
    raw = approvals.read(state, args.approval_evidence, expected)
    reference = approvals.persist(folder, raw, expected)
    if args.resume:
        current_attempt = resumable_attempt(folder, item, target)
        if current_attempt != original_attempt or current_attempt['approval_evidence'] != reference:
            raise ValueError('Saved attachment attempt changed; reconcile without overwriting evidence')
    else:
        write_json(folder / 'save-attempt.json', dict(approval_assertion=args.approval,
            approval_evidence=reference, destination=str(target), pdf_sha256=item['pdf_sha256'],
            privacy_review_assertion=args.privacy_reviewed, public_use_assertion=args.public_approved))
    approvals.verify(folder, reference, expected)
    # Exclusive creation preserves existing files even if another writer races us.
    with target.open('xb') as out, pdf.open('rb') as src:
        shutil.copyfileobj(src, out)
        out.flush()
        os.fsync(out.fileno())
    if digest(target) != item['pdf_sha256']:
        raise ValueError('Saved file mismatch; inspect status, never retry blindly')
    approvals.verify(folder, reference, expected)
    write_json(folder / 'saved.json', dict(approval_assertion=args.approval,
               approval_evidence=reference,
               privacy_review_assertion=args.privacy_reviewed,
               public_use_assertion=args.public_approved,
               destination=str(target), sha256=digest(target)))
    print(json.dumps(dict(status='saved_bytes_verified', destination=str(target), yaml_link='pending separate approved YAML apply')))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, ImportError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))

