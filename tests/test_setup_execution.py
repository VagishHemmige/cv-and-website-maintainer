"""Approved setup on disposable projects; all approval/review evidence is SYNTHETIC."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from approval_fixture import approval_file

spec=importlib.util.spec_from_file_location('execution_test_target',Path(__file__).resolve().parents[1]/'scripts/setup_execution.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


class SetupExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'));self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.state=self.base/'private';self.state.mkdir()
        h.init.start(self.state,True,'SYNTHETIC storage choice')
        self.source=self.state/'reviewed-source';self.source.mkdir();(self.source/'index.txt').write_text('SYNTHETIC public content')
        self.project=self.base/'new-project';self.git=os.environ.get('TEST_GIT') or shutil.which('git')
        self.spec=dict(source=str(self.source),project=str(self.project),steps=[],git=None)
        # Synthetic identity is explicit for planning too; never depend on host Git config.
        config=self.base/'preflight-gitconfig';config.write_text('')
        identity_patch=patch.dict(os.environ,dict(GIT_AUTHOR_NAME='Synthetic Tester',GIT_AUTHOR_EMAIL='test@example.invalid',
            GIT_COMMITTER_NAME='Synthetic Tester',GIT_COMMITTER_EMAIL='test@example.invalid',
            GIT_CONFIG_GLOBAL=str(config),GIT_CONFIG_NOSYSTEM='1'))
        identity_patch.start();self.addCleanup(identity_patch.stop)
    def plan(self):return h.plan(self.state,self.spec)
    def evidence(self,plan,kind='setup'):
        return approval_file(self.state,kind,plan['id'],plan['sha256'],plan['destination'])
    def execute(self,plan):return h.execute(self.state,plan['id'],self.evidence(plan))
    def configure_git(self,publication='hold_for_review'):
        if not self.git:self.skipTest('Git unavailable')
        self.spec['git']=dict(executable=self.git,branch='main',remote='https://github.com/example/review-fixture.git',commit_roots=['index.txt'],publication_mode=publication)
    def identity(self):
        empty=self.base/'empty-gitconfig';empty.write_text('')
        return patch.dict(os.environ,dict(GIT_AUTHOR_NAME='Synthetic Tester',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Synthetic Tester',GIT_COMMITTER_EMAIL='test@example.invalid',GIT_CONFIG_GLOBAL=str(empty),GIT_CONFIG_NOSYSTEM='1'))
    def verification(self,plan,result):
        report=dict(plan_id=plan['id'],commit=result['commit'],public_files=result['public_files'],reference='SYNTHETIC preview and repository review',factual_review=True,privacy_review=True,visual_review=True,link_review=True,repository_identity_and_visibility_verified=True)
        path=self.state/'verification.json';path.write_text(json.dumps(report));return path

    def test_plan_does_not_create_destination(self):
        plan=self.plan();self.assertEqual(plan['status'],'awaiting_exact_setup_approval');self.assertFalse(self.project.exists())
    def test_unapproved_execution_cannot_create_project(self):
        plan=self.plan()
        with self.assertRaises(ValueError):h.execute(self.state,plan['id'],None)
        self.assertFalse(self.project.exists())
    def test_copy_exact_reviewed_source_after_approval(self):
        plan=self.plan();result=self.execute(plan)
        self.assertEqual((self.project/'index.txt').read_text(),'SYNTHETIC public content');self.assertFalse(result['pushed'])
    def test_changed_source_invalidates_setup_approval(self):
        plan=self.plan();(self.source/'index.txt').write_text('Changed')
        with self.assertRaisesRegex(ValueError,'source changed'):self.execute(plan)
        self.assertFalse(self.project.exists())
    def test_existing_destination_never_overwritten(self):
        plan=self.plan();self.project.mkdir();(self.project/'keep.txt').write_text('Keep')
        with self.assertRaisesRegex(ValueError,'must not exist'):self.execute(plan)
        self.assertEqual((self.project/'keep.txt').read_text(),'Keep')
    def test_no_blind_reexecution(self):
        plan=self.plan();self.execute(plan)
        with self.assertRaisesRegex(ValueError,'already attempted'):self.execute(plan)
    def test_private_source_and_credential_paths_refused(self):
        for name in ('cv/private.yml','private/contact.txt','.env','secret.key','config.json'):
            with self.subTest(name=name):self.assertTrue(h.excluded(name))
        (self.source/'private.yml').write_text('SYNTHETIC private')
        with self.assertRaisesRegex(ValueError,'private/unsupported'):self.plan()
    def test_public_directory_with_private_nested_file_refused(self):
        self.project.mkdir();(self.project/'docs').mkdir();(self.project/'docs/private.yml').write_text('SYNTHETIC')
        with self.assertRaisesRegex(ValueError,'Private/unexpected'):h.public_files(self.project,['docs'])
    def test_exact_local_command_and_expected_output(self):
        self.spec['steps']=[dict(name='configure',argv=[sys.executable,'-c','from pathlib import Path; Path("output.txt").write_text("SYNTHETIC")'],expected_files=['output.txt'])]
        result=self.execute(self.plan());self.assertTrue(result['local_commands_verified']);self.assertEqual((self.project/'output.txt').read_text(),'SYNTHETIC')
    def test_failed_command_preserves_partial_project_and_logs(self):
        self.spec['steps']=[dict(name='configure',argv=[sys.executable,'-c','raise SystemExit(3)'],expected_files=['output.txt'])]
        plan=self.plan()
        with self.assertRaisesRegex(ValueError,'stage failed'):self.execute(plan)
        folder=self.state/'setup-plans'/plan['id'];self.assertTrue((folder/'failed.json').is_file());self.assertTrue(self.project.exists());self.assertFalse((folder/'completed.json').exists())
    def test_missing_expected_output_is_not_success(self):
        self.spec['steps']=[dict(name='configure',argv=[sys.executable,'-c','pass'],expected_files=['missing.txt'])]
        with self.assertRaisesRegex(ValueError,'missing/empty'):self.execute(self.plan())
    def test_command_requires_argv_not_shell_string(self):
        self.spec['steps']=[dict(name='configure',argv='do something',expected_files=['output.txt'])]
        with self.assertRaisesRegex(ValueError,'argument list'):self.plan()
    def test_private_state_cannot_be_project_destination(self):
        self.spec['project']=str(self.state/'project')
        with self.assertRaisesRegex(ValueError,'separate'):self.plan()
    def test_git_real_local_commit_uses_only_public_paths(self):
        self.configure_git();plan=self.plan()
        with self.identity():result=self.execute(plan)
        self.assertIsNotNone(result['commit']);self.assertEqual(set(result['public_files']),{'index.txt'});self.assertFalse(result['pushed'])
        files=subprocess.check_output([self.git,'ls-tree','-r','--name-only','HEAD'],cwd=self.project,text=True).strip().splitlines()
        self.assertEqual(files,['index.txt'])
    def test_publish_needs_actual_verification_report(self):
        self.configure_git();plan=self.plan()
        with self.identity():result=self.execute(plan)
        path=self.verification(plan,result);report=json.loads(path.read_text());report['visual_review']=False;path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'verification is required'):h.publish(self.state,plan['id'],path)
    def test_hold_for_review_requires_publication_approval(self):
        self.configure_git();plan=self.plan()
        with self.identity():result=self.execute(plan)
        report=self.verification(plan,result)
        with self.assertRaisesRegex(ValueError,'evidence file required'):h.publish(self.state,plan['id'],report)
        self.assertFalse((self.state/'setup-plans'/plan['id']/'push-started.json').exists())
    def test_publication_request_binds_exact_commit_and_remote(self):
        self.configure_git();plan=self.plan()
        with self.identity():result=self.execute(plan)
        request=h.publication_request(self.state,plan['id'])
        self.assertEqual(request['request']['commit'],result['commit']);self.assertEqual(request['request']['remote'],self.spec['git']['remote'])
    def test_standing_scope_allows_verified_push_without_second_human_approval(self):
        self.configure_git('after_verified_preview');plan=self.plan()
        with self.identity():result=self.execute(plan)
        report=self.verification(plan,result);actual=h.command;seen=[]
        def command(folder,label,argv,cwd):
            if label=='git-push':seen.append(argv);return 'SYNTHETIC mocked remote push'
            return actual(folder,label,argv,cwd)
        with patch.object(h,'command',side_effect=command):out=h.publish(self.state,plan['id'],report)
        self.assertEqual(out['status'],'push_command_succeeded');self.assertFalse(out['deployment_verified']);self.assertNotIn('--force',seen[0])
        with self.assertRaisesRegex(ValueError,'already attempted'):h.publish(self.state,plan['id'],report)
    def test_changed_public_bytes_block_push(self):
        self.configure_git('after_verified_preview');plan=self.plan()
        with self.identity():result=self.execute(plan)
        report=self.verification(plan,result);(self.project/'index.txt').write_text('Changed')
        with self.assertRaisesRegex(ValueError,'state changed'):h.publish(self.state,plan['id'],report)
    def test_new_approval_kinds_do_not_cross_authorize(self):
        plan=self.plan();evidence=self.evidence(plan,'publication')
        with self.assertRaisesRegex(ValueError,'does not match'):h.execute(self.state,plan['id'],evidence)
    def test_final_publication_approval_allows_only_reviewed_commit(self):
        self.configure_git();plan=self.plan()
        with self.identity():result=self.execute(plan)
        report=self.verification(plan,result);request=h.publication_request(self.state,plan['id']);evidence=self.evidence(request,'publication')
        actual=h.command
        def command(folder,label,argv,cwd):
            if label=='git-push':return 'SYNTHETIC mocked remote push'
            return actual(folder,label,argv,cwd)
        with patch.object(h,'command',side_effect=command):self.assertEqual(h.publish(self.state,plan['id'],report,evidence)['status'],'push_command_succeeded')
    def test_private_file_in_approved_root_stops_before_git_commit(self):
        self.configure_git();self.spec['git']['commit_roots']=['docs']
        self.spec['steps']=[dict(name='render_website',argv=[sys.executable,'-c','from pathlib import Path; Path("docs").mkdir(); Path("docs/private.yml").write_text("SYNTHETIC")'],expected_files=['docs/private.yml'])]
        plan=self.plan()
        with self.identity(),self.assertRaisesRegex(ValueError,'Private/unexpected'):self.execute(plan)
        self.assertFalse((self.project/'.git').exists())
    def test_git_environment_redirect_is_removed_before_command(self):
        folder=self.state/'probe';folder.mkdir()
        with patch.dict(os.environ,{'GIT_DIR':'SYNTHETIC redirect','GIT_WORK_TREE':'SYNTHETIC redirect'}),patch.object(h.subprocess,'run',return_value=type('R',(),{'stdout':b'','stderr':b'','returncode':0})()) as run:
            h.command(folder,'environment',[sys.executable,'-c','pass'],self.base)
        self.assertNotIn('GIT_DIR',run.call_args.kwargs['env']);self.assertNotIn('GIT_WORK_TREE',run.call_args.kwargs['env'])
    @unittest.skipUnless(os.environ.get('TEST_QUARTO') and os.environ.get('TEST_RSCRIPT'),'Set TEST_QUARTO and TEST_RSCRIPT for real starter execution')
    def test_real_r_quarto_new_project_cv_site_and_public_git_commit(self):
        staged=h.init.stage_starter(self.state,'SYNTHETIC stage request')
        self.source=Path(staged['project_source_root']);self.spec['source']=str(self.source)
        self.spec['steps']=[
            dict(name='generate_cv',argv=[os.environ['TEST_RSCRIPT'],'-e','options(academic_records.cv_filename="test-output.docx"); source("R/cv.R", encoding="UTF-8")'],expected_files=['cv/test-output.docx']),
            dict(name='render_website',argv=[os.environ['TEST_QUARTO'],'render'],expected_files=['docs/index.html','docs/abstracts.html','docs/mentoring.html'])]
        self.configure_git();self.spec['git']['commit_roots']=[*sorted(p.relative_to(self.source).as_posix() for p in self.source.rglob('*') if p.is_file()),'docs']
        plan=self.plan()
        environment={'R_LIBS_USER':os.environ.get('TEST_R_LIBRARY',''),'QUARTO_R':str(Path(os.environ['TEST_RSCRIPT']).parent)}
        with self.identity(),patch.dict(os.environ,environment):result=self.execute(plan)
        self.assertTrue((self.project/'cv/test-output.docx').is_file());self.assertEqual(len(list((self.project/'docs').glob('*.html'))),9)
        self.assertIsNotNone(result['commit']);self.assertFalse(result['pushed']);self.assertFalse(any(n.startswith('cv/') for n in result['public_files']))
        self.assertNotIn('operation.json',result['public_files']);self.assertNotIn('completed.json',result['public_files'])
        self.assertTrue((Path(staged['metadata_folder'])/'completed.json').is_file())


if __name__=='__main__':unittest.main()
