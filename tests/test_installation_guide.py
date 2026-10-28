"""Distribution fixture checks do not register a marketplace or modify a host."""
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class InstallGuideTests(unittest.TestCase):
    def test_catalog_resolves_complete_plugin_and_all_six_skills_in_isolated_root(self):
        catalog=json.loads((ROOT/'examples/local-marketplace.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            distribution=Path(tmp)
            source=distribution/'academic-records'
            shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('__pycache__'))
            folder=distribution/'.agents/plugins';folder.mkdir(parents=True)
            (folder/'marketplace.json').write_text(json.dumps(catalog))
            entry=catalog['plugins'][0]
            resolved=(distribution/entry['source']['path']).resolve()
            self.assertTrue(resolved.is_relative_to(distribution.resolve()))
            manifest=json.loads((resolved/'plugin.json').read_text())
            self.assertEqual(manifest['name'],entry['name'])
            self.assertEqual(entry['policy']['installation'],'AVAILABLE')
            skills=list((resolved/'skills').glob('*/SKILL.md'))
            self.assertEqual(len(skills),6)
            for skill in skills:
                self.assertTrue(skill.read_text(encoding='utf-8').startswith('---'))
            self.assertTrue((resolved/'assets/starter.zip').is_file())

    def test_installation_relative_links_resolve(self):
        doc=ROOT/'references/installation.md'
        links=re.findall(r'\]\(([^)]+)\)',doc.read_text(encoding='utf-8'))
        for target in links:
            if not target.startswith('https://'):
                with self.subTest(target=target):self.assertTrue((doc.parent/target).is_file())

    def test_public_entrypoint_reaches_guide_and_readiness(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('(references/installation.md)',readme)
        self.assertIn('(references/readiness.md)',readme)
        catalog=json.loads((ROOT/'examples/local-marketplace.json').read_text())
        self.assertEqual(catalog['plugins'][0]['source'],{'source':'local','path':'./academic-records'})
