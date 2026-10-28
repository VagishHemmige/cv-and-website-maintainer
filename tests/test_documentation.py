"""Documentation entry points match packaged skills and preserve workflow boundaries."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class DocumentationTests(unittest.TestCase):
    def test_readme_lists_every_packaged_skill(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        skills=list((ROOT/'skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills),6)
        for skill in skills:self.assertIn(skill.relative_to(ROOT).as_posix(),readme)

    def test_entry_point_links_exist(self):
        for name in ('README.md','CHANGELOG.md','references/check-in.md','references/zotero.md'):
            path=ROOT/name
            for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
                if '://' in target or target.startswith('#'):continue
                with self.subTest(file=name,target=target):
                    self.assertTrue((path.parent/target.split('#',1)[0]).exists())

    def test_readme_is_current_guide_not_accumulated_history(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertLess(len(readme.split()),950)
        self.assertNotIn('Implementation and maintenance notes',readme)
        self.assertNotIn('requires an approval assertion',readme)
        self.assertNotIn('tests/test_proposals.py',readme)
        self.assertIn('unittest discover -s tests',readme)
        self.assertIn('CHANGELOG.md',readme)
        history=(ROOT/'CHANGELOG.md').read_text(encoding='utf-8')
        self.assertIn('Through 0.1.51',history)
        self.assertIn('not a complete release-by-release ledger',history)

    def test_readme_retains_approval_privacy_and_execution_limits(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        for phrase in ('exact [approval evidence]','Possible patient identifiers','does not de-identify','does not automatically regenerate','explicit human authorization','remote push and Office conversion tests are mocked'):
            with self.subTest(phrase=phrase):self.assertIn(phrase,readme)

    def test_checkin_retains_runtime_and_deferral_links(self):
        text=(ROOT/'references/check-in.md').read_text(encoding='utf-8')
        self.assertIn('private-state.md#routine-check-in-progress',text)
        self.assertIn('deferrals.md',text)

    def test_zotero_keeps_import_export_separate_from_search_coverage(self):
        text=(ROOT/'references/zotero.md').read_text(encoding='utf-8')
        for phrase in ('deferrals.md','private-state.md','keep library import/export evidence separate','never advance successful search coverage from an import receipt alone'):
            self.assertIn(phrase,text)
