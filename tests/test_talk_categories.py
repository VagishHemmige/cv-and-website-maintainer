"""B1: real R-generated Word CV section placement on disposable starter records."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

HEADINGS = {'invited':'Invited Presentations', 'conference':'Conference Presentations',
            'grand_rounds':'Grand Rounds', 'teaching':'Teaching Presentations'}

@unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real Word CV tests')
class TalkCategoryTests(unittest.TestCase):
    def project(self, base):
        root=base/'project';root.mkdir()
        with zipfile.ZipFile(Path(__file__).resolve().parents[1]/'assets/starter.zip') as z:
            for name in z.namelist():
                path=Path(name)
                if name.endswith('/'):continue
                self.assertEqual(path.parts[0],'starter')
                self.assertNotIn('..',path.parts)
                target=root.joinpath(*path.parts[1:]);target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(z.read(name))
        return root

    def record(self,title,category='invited',date='2024-01-01'):
        return dict(title=title,category=category,date=date,role='Speaker',venue='Synthetic Venue',
                    city='Example City',state='EX',slides=None,link=None)

    def generate(self,root,records):
        (root/'data/talks.yml').write_text(json.dumps(records),encoding='utf-8')
        env=dict(os.environ,R_LIBS_USER=os.environ.get('TEST_R_LIBRARY',''))
        return subprocess.run([os.environ['TEST_RSCRIPT'],'R/cv.R'],cwd=root,env=env,
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)

    def paragraphs(self,root):
        files=list((root/'cv').glob('*.docx'));self.assertEqual(len(files),1)
        with zipfile.ZipFile(files[0]) as z:doc=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        return [
            ''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]

    def test_real_r_every_talk_appears_once_in_correct_section_sorted_by_date(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            root=self.project(Path(temp).resolve())
            rows=[self.record('B1 INVITED LATER','invited','2025-01-01'),
                  self.record('B1 CONFERENCE','conference'),self.record('B1 TEACHING','teaching'),
                  self.record('B1 INVITED EARLIER','invited','2022-01-01'),
                  self.record('B1 GRAND ROUNDS','grand_rounds')]
            proc=self.generate(root,rows);self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            paras=self.paragraphs(root);full='\n'.join(paras);current=None;placements={}
            for para in paras:
                if para in HEADINGS.values():current=para
                for row in rows:
                    if row['title'] in para:
                        self.assertNotIn(row['title'],placements)
                        placements[row['title']]=current
            for row in rows:
                self.assertEqual(placements.get(row['title']),HEADINGS[row['category']])
                self.assertEqual(full.count(row['title']),1)
            self.assertLess(full.index('B1 INVITED EARLIER'),full.index('B1 INVITED LATER'))
            self.assertNotIn('Invited Extramural Presentations',full)

    def test_real_r_empty_groups_have_no_heading(self):
        for rows in ([],[self.record('B1 CONFERENCE ONLY','conference')]):
            with self.subTest(rows=rows),tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
                root=self.project(Path(temp).resolve())
                proc=self.generate(root,rows);self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
                paras=self.paragraphs(root)
                for key,heading in HEADINGS.items():
                    self.assertEqual(heading in paras,bool(rows) and key=='conference')

    def test_real_r_missing_unknown_or_ambiguous_category_requires_clarification(self):
        for category in (None,'other',['invited','conference']):
            with self.subTest(category=category),tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
                root=self.project(Path(temp).resolve())
                proc=self.generate(root,[self.record('B1 UNRESOLVED',category)])
                self.assertNotEqual(proc.returncode,0)
                self.assertIn('confirm it before generating the CV',proc.stderr)
                self.assertEqual(list((root/'cv').glob('*.docx')),[])

if __name__=='__main__':unittest.main()

