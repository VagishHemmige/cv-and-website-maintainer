import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("personal_site",Path(__file__).resolve().parents[1]/"scripts/personal_site.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class PersonalSiteTests(unittest.TestCase):
    def setUp(self):
        self.p=m.plan("New-User","main")
        self.o=dict(repository="new-user.github.io",owner="new-user",branch="main",site_url="https://new-user.github.io/",output_dir="docs",pages_source="/docs",pages_method="branch-docs",public_files=["docs/index.html","docs/.nojekyll","docs/site_libs/a.css"],identity_verified=True,visibility_verified=True,privacy_review=True,root_review=True,assets_and_links_review=True,intended_commit="a"*40,deployed_commit="a"*40,deployment_status="success")
    def test_personal_address_and_order(self):
        self.assertEqual(self.p["remote"],"https://github.com/new-user/new-user.github.io")
        self.assertEqual(self.p["site_url"],"https://new-user.github.io/")
        self.assertLess(self.p["steps"].index("push"),self.p["steps"].index("configure_pages"))
    def test_invalid_identity_and_branch(self):
        for user in ["../alice","-alice","alice--bob","https://github.com/alice",""]:
            with self.subTest(user=user),self.assertRaises(ValueError):m.plan(user,"main")
        for branch in ["-main","a..b","a/.b","a.lock","a//b","a/","a b"]:
            with self.subTest(branch=branch),self.assertRaises(ValueError):m.plan("alice",branch)
    def test_existing_repository_or_folder_holds(self):
        for kwargs in [dict(repository_exists=True),dict(local_exists=True)]:
            p=m.plan("New-User","main",**kwargs)
            self.assertEqual(p["action"],"inspect_existing")
            self.assertFalse(m.check(p,self.o)["deployment_verified"])
    def test_complete_observations_pass(self):
        self.assertTrue(m.check(self.p,self.o)["deployment_verified"])
    def test_configuration_mismatch_blocks(self):
        for key,value in [("site_url","https://new-user.github.io/project/"),("pages_source","/"),("pages_method","workflow"),("branch","gh-pages"),("owner","other"),("output_dir","_site")]:
            with self.subTest(key=key):
                o={**self.o,key:value};self.assertIn(key,m.check(self.p,o)["blockers"])
    def test_private_and_unsafe_files_block(self):
        for path in ["cv/private.yml","docs/cv/cv.docx","docs/raw/a.pdf","docs/.env","docs/config.json","docs/AGENTS.md","docs/secret.key","../private.txt","/absolute","docs\\private.yml"]:
            with self.subTest(path=path):
                o={**self.o,"public_files":self.o["public_files"]+[path]}
                self.assertIn("public_files",m.check(self.p,o)["blockers"])
    def test_missing_publishing_file_blocks(self):
        for name in ["docs/.nojekyll","docs/index.html"]:
            o={**self.o,"public_files":[p for p in self.o["public_files"] if p!=name]}
            self.assertIn("publishing_files",m.check(self.p,o)["blockers"])
    def test_failed_pending_unknown_deployment_blocks(self):
        for status in ["failure","pending",None]:
            self.assertIn("deployment_status",m.check(self.p,{**self.o,"deployment_status":status})["blockers"])
    def test_stale_or_absent_commit_blocks(self):
        for commit in ["b"*40,None,""]:
            self.assertIn("deployment_commit",m.check(self.p,{**self.o,"deployed_commit":commit})["blockers"])
    def test_missing_review_blocks(self):
        for key in ["identity_verified","visibility_verified","privacy_review","root_review","assets_and_links_review"]:
            self.assertIn(key,m.check(self.p,{**self.o,key:False})["blockers"])
    def test_changed_plan_cannot_redirect_site(self):
        self.assertIn("plan_site_url",m.check({**self.p,"site_url":"https://other.github.io/"},self.o)["blockers"])
    def test_public_formatting_reference_allowed(self):
        self.assertFalse(m.private_path("templates/cv-styles.docx"))
        self.assertTrue(m.private_path("docs/templates/cv-styles.docx"))

if __name__=="__main__":unittest.main()
