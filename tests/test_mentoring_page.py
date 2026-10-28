"""B5: real R/Quarto mentoring output hides setup while preserving linked records."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

@unittest.skipUnless(os.environ.get('TEST_RSCRIPT') and os.environ.get('TEST_QUARTO'),
                     'Set TEST_RSCRIPT and TEST_QUARTO for real page checks')
class MentoringPageTests(unittest.TestCase):
    def test_real_r_quarto_shows_mentees_links_and_no_setup_code_or_messages(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            root=Path(temp).resolve()/'project';root.mkdir()
            with zipfile.ZipFile(Path(__file__).resolve().parents[1]/'assets/starter.zip') as z:
                for name in z.namelist():
                    if name.endswith('/'):continue
                    parts=Path(name).parts
                    self.assertEqual(parts[0],'starter');self.assertNotIn('..',parts)
                    target=root.joinpath(*parts[1:]);target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(z.read(name))
            def records(name,rows):
                (root/'data'/name).write_text(json.dumps(rows),encoding='utf-8')
            records('mentoring.yml',[
                dict(name='B5 Active Learner',status='Active',role='Research mentor',level='Resident',
                     projects=['B5 Linked Project'],manuscripts=['b5Manuscript'],text='B5 research description'),
                dict(name='B5 Former Learner',status='Former',role='Research mentor',level='Student')])
            records('projects.yml',[dict(title='B5 Linked Project',theme='Education',
                    description='Synthetic project',status='active')])
            records('abstracts.yml',[dict(title='B5 Linked Abstract',authors='Example A.',
                    meeting='B5 Meeting',date='2025-05-12',city='Example City',state='EX',
                    type='poster',scope='local',mentees=['B5 Active Learner'],pdf=None,link=None)])
            (root/'data/publications.bib').write_text(
                '@article{b5Manuscript, title={B5 Linked Manuscript}, author={Example, Alex}, journal={Synthetic Journal}, year={2025}}\n',
                encoding='utf-8')
            env=dict(os.environ,R_LIBS_USER=os.environ.get('TEST_R_LIBRARY',''),
                     QUARTO_R=str(Path(os.environ['TEST_RSCRIPT']).parent))
            proc=subprocess.run([os.environ['TEST_QUARTO'],'render','mentoring.qmd'],cwd=root,env=env,
                                capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
            self.assertEqual(proc.returncode,0,proc.stdout[-2000:]+proc.stderr[-2000:])
            html=(root/'docs/mentoring.html').read_text(encoding='utf-8')
            for visible in ['B5 Active Learner','B5 Former Learner','B5 research description',
                            'B5 Linked Project','B5 Linked Manuscript','B5 Linked Abstract']:
                self.assertIn(visible,html)
            for link in ['Projects.html#b5-linked-project','manuscripts.html#b5Manuscript',
                         'abstracts.html#b5-linked-abstract-b5-meeting-2025']:
                self.assertIn(link,html)
            for leaked in ['library(dplyr)','render_mentee &lt;-','read_starter_records(',
                           'Attaching package:','masked from','sourceCode r','cell-output-stderr']:
                self.assertFalse(leaked in html, 'Setup detail leaked into public HTML: ' + leaked)
            # Logs remain available to the operator; hiding output is not a successful render assertion.
            self.assertIn('mentoring',proc.stdout+proc.stderr)

if __name__=='__main__':unittest.main()

