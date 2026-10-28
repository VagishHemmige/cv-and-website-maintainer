"""Generic starter output on disposable records, actual R/Quarto, no user project."""
import json,os,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from html.parser import HTMLParser
import test_talk_categories as cv
import test_proposals as records

ROOT=Path(__file__).resolve().parents[1]

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)

@unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real starter CV checks')
class StarterCleanupTests(unittest.TestCase):
    project=cv.TalkCategoryTests.project
    paragraphs=cv.TalkCategoryTests.paragraphs
    def setUp(self):
        temp=tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'));self.addCleanup(temp.cleanup)
        self.base=Path(temp.name).resolve();self.root=self.project(self.base)
        self.env=dict(os.environ,R_LIBS_USER=os.environ.get('TEST_R_LIBRARY',''))
    def write(self,name,rows):
        (self.root/'data'/name).write_text(json.dumps(rows),encoding='utf-8')
    def generate(self):
        expression='cfg <- yaml::read_yaml("site.yml"); cfg$website <- NULL; yaml::write_yaml(cfg,"site.yml"); source("R/cv.R", encoding="UTF-8")'
        result=subprocess.run([os.environ['TEST_RSCRIPT'],'-e',expression],cwd=self.root,env=self.env,capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return self.paragraphs(self.root)
    def test_real_r_empty_cv_has_no_activity_or_bibliography_headings(self):
        paras=self.generate()
        self.assertIn('CURRICULUM VITAE',paras)
        for heading in ('Education','Postgraduate Training','Professional Employment and Hospital Appointments','Board Certification','Professional Society Membership','Awards and Honors','Other Professional Activities','Extramural Activities:','Intramural Activities:','Research','Grant Support','Bibliography','A. Original Contributions in Reviewed Journals:','B. Books, Chapters in Books, and Review Articles:','C. Abstracts:','D. Websites'):
            with self.subTest(heading=heading):self.assertNotIn(heading,paras)
    def test_real_r_populated_sections_remain_and_empty_subsections_disappear(self):
        for name,row in records.records(False).items():self.write(name+'.yml',[row])
        paras=self.generate();full='\n'.join(paras)
        for heading in ('Education','Postgraduate Training','Board Certification','Professional Society Membership','Awards and Honors','Other Professional Activities','Intramural Activities:','Grant Support','Bibliography','C. Abstracts:'):
            self.assertIn(heading,paras)
        self.assertIn('Teaching award',full);self.assertIn('Example abstract',full)
        self.assertNotIn('Extramural Activities:',paras)
        self.assertNotIn('A. Original Contributions in Reviewed Journals:',paras)
        self.assertNotIn('B. Books, Chapters in Books, and Review Articles:',paras)
        self.assertNotIn('D. Websites',paras)
    def test_real_r_service_only_appointment_not_an_empty_employment_section(self):
        row=records.records(False)['appointments'];row['cv_sections']=['service']
        self.write('appointments.yml',[row]);paras=self.generate();full='\n'.join(paras)
        self.assertNotIn('Professional Employment and Hospital Appointments',paras)
        self.assertIn('Other Professional Activities',paras);self.assertIn('Intramural Activities:',paras)
        self.assertNotIn('Extramural Activities:',paras);self.assertEqual(full.count('Professor'),1)
    def test_real_r_grants_with_and_without_award_number(self):
        grant=records.records(False)['grants']
        self.write('grants.yml',[dict(grant,id='one',sponsor='NIH',award_number=None),dict(grant,id='two',sponsor='Foundation',award_number='AW-1')])
        full='\n'.join(self.generate())
        self.assertIn('NIH.',full);self.assertNotIn('NIH .',full)
        self.assertIn('Foundation AW-1.',full)
    @unittest.skipUnless(os.environ.get('TEST_QUARTO'),'Set TEST_QUARTO for actual page output checks')
    def test_real_quarto_unknown_locations_links_and_footer(self):
        talk=records.records(False)['talks']
        self.write('talks.yml',[dict(talk,title='UNKNOWN CITY TALK',city=None,state=None,slides=None,link=None),dict(talk,title='KNOWN CITY TALK',city='Boston',state='MA',slides=None,link=None)])
        abstract=records.records(False)['abstracts']
        self.write('abstracts.yml',[dict(abstract,title='ABSTRACT NO LINKS',pdf=None,link=None),dict(abstract,title='ABSTRACT WITH LINK',pdf=None,link='https://example.invalid/abstract')])
        project=records.records(False)['projects']
        self.write('projects.yml',[dict(project,title='PROJECT NO LINKS',site=None,repo=None,methods=[]),dict(project,title='PROJECT WITH LINK',site=None,repo='https://example.invalid/repo',methods=['Synthetic method'])])
        env=dict(self.env,QUARTO_R=str(Path(os.environ['TEST_RSCRIPT']).parent))
        result=subprocess.run([os.environ['TEST_QUARTO'],'render'],cwd=self.root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        def page(name):
            raw=(self.root/'docs'/name).read_text(encoding='utf-8');parser=Text();parser.feed(raw)
            return raw,' '.join(parser.parts)
        raw,text=page('presentation.html')
        self.assertIn('Location not specified',text);self.assertIn('Boston, MA',text);self.assertNotIn('Virtual',text)
        self.assertNotIn('pkgdown-style',text)
        raw,text=page('abstracts.html')
        self.assertIn('ABSTRACT NO LINKS',text);self.assertIn('ABSTRACT WITH LINK',text)
        self.assertIn('href="https://example.invalid/abstract"',raw)
        self.assertNotIn('File | Link',text);self.assertNotIn('>File<',raw)
        raw,text=page('Projects.html')
        self.assertIn('PROJECT NO LINKS',text);self.assertIn('PROJECT WITH LINK',text)
        self.assertIn('href="https://example.invalid/repo"',raw)
        self.assertNotIn('Project Site | GitHub',text);self.assertNotIn('>Project Site<',raw)

class GenericGuidanceTests(unittest.TestCase):
    def test_optional_design_context_and_neutral_deferral_examples(self):
        text=(ROOT/'references/project.md').read_text(encoding='utf-8')
        self.assertIn('optional development context',text)
        preferences=(ROOT/'references/preferences.md').read_text(encoding='utf-8')
        self.assertIn('do not require a development plan',preferences)
        for name in ('references/deferrals.md','skills/discover-academic-updates/SKILL.md'):
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertNotIn('review-test',text);self.assertNotIn('review test',text)
