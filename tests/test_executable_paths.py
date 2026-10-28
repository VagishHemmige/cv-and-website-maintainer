"""Executable aliases use real filesystem redirects; protected data rules stay strict."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_setup_execution as fixture

h=fixture.h

class ExecutablePathTests(unittest.TestCase):
    setUp=fixture.SetupExecutionTests.setUp
    plan=fixture.SetupExecutionTests.plan
    evidence=fixture.SetupExecutionTests.evidence
    execute=fixture.SetupExecutionTests.execute
    configure_git=fixture.SetupExecutionTests.configure_git
    verification=fixture.SetupExecutionTests.verification

    def alias(self,target=None):
        target=Path(target or sys.executable).resolve(strict=True)
        alias=self.base/'runtime-alias'
        if os.name=='nt':
            # Directory junctions require no symlink privilege and exercise real resolution.
            result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(alias),str(target.parent)],capture_output=True)
            if result.returncode:raise RuntimeError('Synthetic junction creation failed')
        else:alias.symlink_to(target.parent,target_is_directory=True)
        self.addCleanup(lambda: os.rmdir(alias) if os.name=='nt' and alias.exists() else alias.unlink(missing_ok=True))
        return alias/target.name

    def step(self,exe=None,code='from pathlib import Path; Path("output.txt").write_text("SYNTHETIC")'):
        self.spec['steps']=[dict(name='configure',argv=[str(exe or sys.executable),'-c',code],expected_files=['output.txt'])]

    def item(self,plan):return h.read_plan(self.state,plan['id'])[1]

    def test_real_alias_is_resolved_recorded_and_executed(self):
        alias=self.alias();self.step(alias);original=copy.deepcopy(self.spec)
        plan=self.plan();binding=plan['executables'][0]
        self.assertEqual(self.spec,original)
        self.assertEqual(binding['requested'],str(alias));self.assertEqual(binding['resolved'],str(Path(sys.executable).resolve()))
        self.assertEqual(plan['steps'][0]['argv'][0],binding['resolved']);self.assertEqual(len(binding['sha256']),64)
        result=self.execute(plan);self.assertTrue(result['local_commands_verified'])
        self.assertEqual((self.project/'output.txt').read_text(),'SYNTHETIC')

    def test_changed_binary_blocks_before_project_creation(self):
        target=self.base/'disposable.exe';shutil.copyfile(sys.executable,target)
        if os.name!='nt':target.chmod(0o700)
        self.step(target);plan=self.plan();target.write_bytes(b'changed executable')
        with self.assertRaisesRegex(ValueError,'executable.*changed'):self.execute(plan)
        self.assertFalse(self.project.exists());self.assertFalse((self.state/'setup-plans'/plan['id']/'started.json').exists())

    def test_retargeted_alias_blocks_before_creation(self):
        alias=self.alias();self.step(alias);plan=self.plan()
        folder=alias.parent
        if os.name=='nt':os.rmdir(folder)
        else:folder.unlink()
        other=self.base/'other-runtime';other.mkdir()
        target=other/alias.name;shutil.copy2(sys.executable,target)
        if os.name!='nt':
            target.chmod(target.stat().st_mode | 0o100)
            self.assertTrue(os.access(target,os.X_OK))
        # Exercise changed executable binding, not a non-executable fixture.
        if os.name=='nt':
            self.assertEqual(subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(folder),str(other)],capture_output=True).returncode,0)
        else:folder.symlink_to(other,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'executable.*changed'):self.execute(plan)
        self.assertFalse(self.project.exists())

    def test_missing_alias_is_actionable(self):
        self.step(self.base/'missing.exe')
        with self.assertRaisesRegex(ValueError,'missing, inaccessible or cyclic'):self.plan()
        self.assertFalse(self.project.exists())

    def test_relative_executable_rejected(self):
        self.step('python')
        with self.assertRaisesRegex(ValueError,'absolute path'):self.plan()

    def test_directory_executable_rejected(self):
        self.step(self.base)
        with self.assertRaisesRegex(ValueError,'shell wrapper or directory'):self.plan()

    def test_cmd_wrapper_rejected(self):
        target=self.base/'wrapper.cmd';target.write_text('echo synthetic');self.step(target)
        with self.assertRaisesRegex(ValueError,'shell wrapper'):self.plan()

    def test_symlinked_source_stays_protected(self):
        alias=self.alias();self.spec['source']=str(alias.parent)
        with self.assertRaisesRegex(ValueError,'Redirected path refused.*protected'):self.plan()

    def test_symlinked_state_stays_protected(self):
        alias=self.alias()
        with self.assertRaisesRegex(ValueError,'Redirected path refused.*protected'):h.init.private(alias.parent)

    def test_legacy_plan_with_commands_requires_fresh_approval(self):
        self.step();plan=self.plan();item=self.item(plan);item.pop('executables')
        with self.assertRaisesRegex(ValueError,'Legacy setup plan'):h.verify_executables(item)
        self.assertFalse(self.project.exists())

    def test_binding_must_match_command(self):
        self.step();plan=self.plan();item=self.item(plan);item['specification']['steps'][0]['argv'][0]=str(self.base/'different.exe')
        with self.assertRaisesRegex(ValueError,'bindings do not match'):h.verify_executables(item)

    def test_recheck_before_each_command(self):
        self.step();plan=self.plan();item=self.item(plan)
        with patch.object(h,'executable_snapshot',return_value=dict(item['executables'][0],sha256='0'*64)),patch.object(h,'command') as run:
            with self.assertRaisesRegex(ValueError,'executable.*changed'):h.reviewed_command(self.state,'synthetic',item['specification']['steps'][0]['argv'],self.state,item)
            run.assert_not_called()

    def test_owner_or_mode_change_invalidates_snapshot(self):
        self.step();plan=self.plan();item=self.item(plan);snapshot=item['executables'][0]
        for field in ('owner','mode'):
            with self.subTest(field=field),patch.object(h,'executable_snapshot',return_value=dict(snapshot,**{field:-1})):
                with self.assertRaisesRegex(ValueError,'executable.*changed'):h.verify_executables(item)

    def test_symlinked_git_real_preflight_and_commit(self):
        self.configure_git();alias=self.alias(self.git);self.spec['git']['executable']=str(alias)
        plan=self.plan();self.assertEqual(plan['git']['executable'],str(Path(self.git).resolve()))
        result=self.execute(plan);self.assertIsNotNone(result['commit']);self.assertFalse(result['pushed'])

    def test_publication_checks_bindings_before_any_command(self):
        self.configure_git();plan=self.plan();result=self.execute(plan);report=self.verification(plan,result)
        item=self.item(plan);snapshot=item['executables'][0]
        with patch.object(h,'executable_snapshot',return_value=dict(snapshot,sha256='0'*64)),patch.object(h,'command') as run:
            with self.assertRaisesRegex(ValueError,'executable.*changed'):h.publish(self.state,plan['id'],report)
            run.assert_not_called()
        self.assertFalse((self.state/'setup-plans'/plan['id']/'push-started.json').exists())
