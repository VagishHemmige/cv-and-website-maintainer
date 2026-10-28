"""B6: setup and deployment protect the same actual paths before publication."""
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_setup_execution as setup
import test_personal_site as site

class PublicPathTests(unittest.TestCase):
    def test_private_and_unsafe_paths_block_in_both_workflows(self):
        paths=['AGENTS.md','data/agents.MD','docs/.codex/settings.json',
               '.codex/cache/file.txt','cv/private.yml','docs/raw/upload.pdf',
               'docs/state-history/op.json','docs/config.json/nested.txt',
               '.env.local','docs/.environment','docs/secret.KEY',
               'docs/templates/cv-styles.docx','Templates/cv-styles.docx',
               '../file','/absolute','C:/private.txt','docs\\private.yml',
               'docs//file','./data/file']
        p=site.m.plan('example','main')
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(setup.h.excluded(path))
                self.assertTrue(site.m.private_path(path))
                self.assertIn('public_files',site.m.check(p,{'public_files':[path]})['blockers'])

    def test_ordinary_public_sources_assets_and_exact_style_template_remain_allowed(self):
        for path in ['index.qmd','data/grants.yml','docs/index.html','docs/.nojekyll',
                     'docs/site_libs/a.css','templates/cv-styles.docx','.github/workflows/render.yml']:
            with self.subTest(path=path):
                self.assertFalse(setup.h.excluded(path))
                self.assertFalse(site.m.private_path(path))

class SetupBoundaryTests(unittest.TestCase):
    setUp=setup.SetupExecutionTests.setUp
    plan=setup.SetupExecutionTests.plan
    evidence=setup.SetupExecutionTests.evidence
    execute=setup.SetupExecutionTests.execute
    configure_git=setup.SetupExecutionTests.configure_git

    def test_agent_instructions_in_source_refused_before_destination_creation(self):
        path=self.source/'data/AGENTS.md';path.parent.mkdir();path.write_text('SYNTHETIC private instructions')
        with self.assertRaisesRegex(ValueError,'private/unsupported'):
            self.plan()
        self.assertFalse(self.project.exists())

    def test_generated_agent_instructions_refused_before_git_repository_mutation(self):
        self.configure_git()
        docs=self.source/'docs';docs.mkdir();(docs/'index.html').write_text('SYNTHETIC public')
        self.spec['git']['commit_roots']=['docs']
        self.spec['steps']=[dict(name='configure',argv=[sys.executable,'-c',
            'from pathlib import Path; Path("docs/AGENTS.md").write_text("SYNTHETIC private")'],
            expected_files=['docs/index.html'])]
        plan=self.plan();real=setup.h.command;git_calls=[]
        def observed(folder,label,argv,cwd):
            if label.startswith('git-'):git_calls.append(label)
            return real(folder,label,argv,cwd)
        with patch.object(setup.h,'command',side_effect=observed):
            with self.assertRaisesRegex(ValueError,'Private/unexpected'):
                self.execute(plan)
        self.assertEqual(git_calls,[])
        self.assertFalse((self.project/'.git').exists())
        self.assertEqual((self.project/'docs/AGENTS.md').read_text(),'SYNTHETIC private')

if __name__=='__main__':unittest.main()


# N1: synthetic filenames only; no real credentials or user project access.
SENSITIVE_NAMES = ['.Renviron', '.Rhistory', '.RData', '.netrc', '_netrc',
    '.git-credentials', 'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    'id_ecdsa_sk', 'id_ed25519_sk', '.ssh/custom-key']

class CredentialBoundaryTests(unittest.TestCase):
    def test_sensitive_names_blocked_at_all_depths_by_both_workflows(self):
        plan=site.m.plan('example','main')
        for name in SENSITIVE_NAMES:
            for path in [name, 'docs/'+name, 'docs/'+name.upper()]:
                with self.subTest(path=path):
                    self.assertTrue(setup.h.excluded(path))
                    self.assertTrue(site.m.private_path(path))
                    self.assertIn('public_files',site.m.check(plan,{'public_files':[path]})['blockers'])

    def test_starter_gitignore_blocks_real_git_staging_candidates(self):
        git=os.environ.get('TEST_GIT') or __import__('shutil').which('git')
        if not git:self.skipTest('Git unavailable')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as tmp:
            root=Path(tmp)
            with zipfile.ZipFile(Path(__file__).resolve().parents[1]/'assets/starter.zip') as z:
                (root/'.gitignore').write_bytes(z.read('starter/.gitignore'))
            subprocess.run([git,'init',str(root)],check=True,capture_output=True)
            for name in SENSITIVE_NAMES:
                for path in [name,'docs/'+name]:
                    with self.subTest(path=path):
                        f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('SYNTHETIC')
                        result=subprocess.run([git,'-C',str(root),'check-ignore','--',path],capture_output=True)
                        self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([git,'-C',str(root),'check-ignore','--','index.qmd'],capture_output=True)
            self.assertEqual(result.returncode,1)
