"""Bounded executable discovery; no real Office process is launched."""
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_attachments as fixtures

helper = fixtures.helper


class RuntimeDiscoveryTests(unittest.TestCase):
    setUp = fixtures.AttachmentTests.setUp
    cli = fixtures.AttachmentTests.cli
    stage_deck = fixtures.AttachmentTests.stage_deck
    flags = fixtures.AttachmentTests.flags
    private_folder = fixtures.AttachmentTests.private_folder

    def test_saved_absolute_executable_has_priority(self):
        executable=self.base/'saved-soffice.exe';executable.write_bytes(b'fixture')
        with patch.object(helper.shutil,'which') as lookup:
            self.assertEqual(helper.libreoffice_executable(str(executable)),str(executable))
        lookup.assert_not_called()

    def test_invalid_saved_path_is_reported_without_fallback(self):
        for preferred in ('relative-soffice.exe',str(self.base/'missing.exe'),str(self.base)):
            with self.subTest(preferred=preferred),patch.object(helper.shutil,'which') as lookup:
                with self.assertRaisesRegex(ValueError,'Configured LibreOffice executable is unavailable'):
                    helper.libreoffice_executable(preferred)
                lookup.assert_not_called()

    def test_path_executable_precedes_standard_locations(self):
        with patch.object(helper.shutil,'which',return_value='path-soffice'),patch.object(helper,'windows_host') as host:
            self.assertEqual(helper.libreoffice_executable(),'path-soffice')
        host.assert_not_called()

    def test_windows_program_roots_find_off_path_installations(self):
        for key in ('ProgramW6432','ProgramFiles','ProgramFiles(x86)'):
            executable=self.base/key/'LibreOffice/program/soffice.exe'
            executable.parent.mkdir(parents=True);executable.write_bytes(b'fixture')
            with self.subTest(key=key),patch.dict(os.environ,{key:str(self.base/key)},clear=True),patch.object(helper,'windows_host',return_value=True),patch.object(helper.shutil,'which',return_value=None):
                self.assertEqual(Path(helper.libreoffice_executable()),executable)

    def test_standard_windows_fallbacks_and_no_recursive_scan(self):
        seen=[]
        def exists(path):
            seen.append(str(path).replace('\\','/'))
            return str(path).replace('\\','/')=='C:/Program Files (x86)/LibreOffice/program/soffice.exe'
        with patch.dict(os.environ,{},clear=True),patch.object(helper,'windows_host',return_value=True),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.Path,'is_file',exists):
            self.assertIn('soffice.exe',helper.libreoffice_executable())
        self.assertEqual(len(seen),2)

    def test_nonwindows_does_not_search_windows_roots(self):
        with patch.object(helper,'windows_host',return_value=False),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.Path,'is_file') as exists:
            self.assertIsNone(helper.libreoffice_executable())
        exists.assert_not_called()

    def test_no_match_returns_none_after_bounded_search(self):
        with patch.dict(os.environ,{},clear=True),patch.object(helper,'windows_host',return_value=True),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.Path,'is_file',return_value=False) as exists:
            self.assertIsNone(helper.libreoffice_executable())
        self.assertEqual(exists.call_count,2)

    def test_powerpoint_registration_success_and_absence(self):
        for code,expected in ((0,'fixture-shell'),(1,None)):
            with self.subTest(code=code),patch.object(helper,'windows_host',return_value=True),patch.object(helper.subprocess,'run',return_value=SimpleNamespace(returncode=code)):
                self.assertEqual(helper.powerpoint_shell('fixture-shell'),expected)

    def test_powerpoint_probe_failures_are_specific_and_do_not_leak_output(self):
        failures=[(PermissionError('PRIVATE_SENTINEL'),'blocked'),(FileNotFoundError('PRIVATE_SENTINEL'),'could not launch'),(subprocess.TimeoutExpired('fixture',20,output='PRIVATE_SENTINEL'),'timed out')]
        for error,message in failures:
            with self.subTest(message=message),patch.object(helper,'windows_host',return_value=True),patch.object(helper.subprocess,'run',side_effect=error):
                with self.assertRaisesRegex(ValueError,message) as caught:helper.powerpoint_shell('fixture-shell')
                self.assertNotIn('PRIVATE_SENTINEL',str(caught.exception))

    def test_unexpected_probe_exit_is_not_treated_as_absence(self):
        with patch.object(helper,'windows_host',return_value=True),patch.object(helper.subprocess,'run',return_value=SimpleNamespace(returncode=7,stderr='PRIVATE_SENTINEL')):
            with self.assertRaisesRegex(ValueError,'failed .exit 7') as caught:helper.powerpoint_shell('fixture-shell')
        self.assertNotIn('PRIVATE_SENTINEL',str(caught.exception))

    def test_powerpoint_available_skips_irrelevant_stale_soffice(self):
        self.config['attachments']['soffice']=str(self.base/'missing.exe')
        (self.state/'config.json').write_text(__import__('json').dumps(self.config))
        with patch.object(helper,'powerpoint_shell',return_value='fixture-shell'),patch.object(helper,'libreoffice_executable') as discover,patch.object(helper.subprocess,'run',side_effect=fixtures.AttachmentTests.successful_powerpoint.__get__(self)):
            item=self.stage_deck(*self.flags())
        discover.assert_not_called();self.assertEqual(item['review_status'],'pending_visual_privacy_review')

    def test_off_path_libreoffice_stage_still_requires_privacy_review(self):
        executable=self.base/'office/LibreOffice/program/soffice.exe'
        executable.parent.mkdir(parents=True);executable.write_bytes(b'fixture')
        def convert(engine,source,dest):
            self.assertEqual(Path(engine),executable);fixtures.pdf(dest)
        with patch.dict(os.environ,{'ProgramFiles':str(self.base/'office')},clear=True),patch.object(helper,'windows_host',return_value=True),patch.object(helper,'powerpoint_shell',return_value=None),patch.object(helper.shutil,'which',return_value=None),patch.object(helper,'convert_libreoffice',side_effect=convert):
            item=self.stage_deck(*self.flags())
        self.assertEqual(item['review_status'],'pending_visual_privacy_review');self.assertFalse(self.target.exists())


if __name__=='__main__':unittest.main()
