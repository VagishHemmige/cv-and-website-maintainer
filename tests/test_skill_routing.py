"""Explicit skill routing instructions; no claim of host classifier enforcement."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SkillRoutingTests(unittest.TestCase):
    def test_maintenance_entry_points_name_configuration_and_initialization(self):
        for name in ('update-academic-records','discover-academic-updates','update-zotero-records','handoff-academic-update'):
            with self.subTest(skill=name):
                path=ROOT/'skills'/name/'SKILL.md';text=path.read_text(encoding='utf-8')
                self.assertNotIn('Missing setup triggers guided initialization',text)
                for target in ('configure-academic-records','initialize-academic-records'):
                    link='../'+target+'/SKILL.md';self.assertIn(link,text);self.assertTrue((path.parent/link).is_file())
                for phrase in ('existing records project','requested first-time CV/site setup','missing profile alone','repeated CV import','ask one focused question','corrupt existing state','not initialization'):
                    self.assertIn(phrase,text)

    def test_configuration_entry_point_supports_existing_project_without_profile(self):
        text=(ROOT/'skills/configure-academic-records/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('For an existing records project, guide preference setup here when no profile exists',text)
        self.assertIn('use [initialize-academic-records]',text)
        self.assertIn('Does not import a CV or create a website',text)

    def test_initializer_routes_existing_project_preferences_back_to_configuration(self):
        text=(ROOT/'skills/initialize-academic-records/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('existing-project preferences, including a missing profile',text)
        self.assertIn('without repeating CV import',text)
        self.assertIn('corrupt profile requires access/reviewed recovery',text)
