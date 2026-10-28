"""Disposable real R/Quarto integration; set TEST_QUARTO, TEST_RSCRIPT (or TEST_R_BIN), and optional TEST_R_LIBRARY."""
import hashlib
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
import zipfile


def configured_quarto_r():
    """Use explicit test configuration; never assume a particular host installation."""
    directory=os.environ.get('TEST_R_BIN')
    if directory:
        path=pathlib.Path(directory)
        if not path.is_absolute() or not path.is_dir() or not any((path/name).is_file() for name in ('Rscript','Rscript.exe')):
            raise unittest.SkipTest('TEST_R_BIN must name an existing absolute R bin directory containing Rscript')
        return str(path.resolve())
    rscript=os.environ.get('TEST_RSCRIPT')
    if not rscript:
        raise unittest.SkipTest('Set TEST_R_BIN or TEST_RSCRIPT for the R/Quarto page-adaptation test')
    path=pathlib.Path(rscript)
    if not path.is_absolute() or not path.is_file():
        raise unittest.SkipTest('TEST_RSCRIPT must name an existing absolute Rscript executable')
    return str(path.resolve().parent)

class PageAdaptationTests(unittest.TestCase):
    def test_record_shape_errors_and_missing_optional_values_in_real_r(self):
        rscript=os.environ.get('TEST_RSCRIPT')
        if not rscript:self.skipTest('TEST_RSCRIPT not supplied')
        plugin=pathlib.Path(__file__).resolve().parents[1]
        code=(plugin/'examples/yaml-records.qmd').read_text(encoding='utf-8').split('```{r}\n',1)[1].rsplit('```',1)[0]
        with tempfile.TemporaryDirectory(prefix='page-shapes-',dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            project=pathlib.Path(temp);(project/'data').mkdir()
            script=project/'render.R';script.write_text(code,encoding='utf-8')
            env=dict(os.environ)
            if env.get('TEST_R_LIBRARY'):env['R_LIBS_USER']=env['TEST_R_LIBRARY']
            for value,ok,expected in [('title: wrong-shape\n',False,'Expected a YAML sequence'),('- title: [bad, list]\n',False,'Visible fields must be scalar'),('- title: "Only title"\n',True,'Only title')]:
                with self.subTest(value=value):
                    (project/'data/grants.yml').write_text(value,encoding='utf-8')
                    result=subprocess.run([rscript,str(script)],cwd=project,env=env,capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode==0,ok,result.stderr)
                    self.assertIn(expected,result.stdout+result.stderr)

    def test_add_grants_hide_mentoring_empty_and_synthetic(self):
        plugin=pathlib.Path(__file__).resolve().parents[1]
        archive=pathlib.Path(os.environ.get("TEST_STARTER",str(plugin/"assets/starter.zip")))
        quarto=os.environ.get("TEST_QUARTO")
        if not quarto:self.skipTest("TEST_QUARTO not supplied")
        r_bin=configured_quarto_r()
        with tempfile.TemporaryDirectory(prefix="page-adaptation-",dir=os.environ.get("TEST_TMP_ROOT")) as temp:
            project=pathlib.Path(temp)
            with zipfile.ZipFile(archive) as z:z.extractall(project)
            roots=list(project.rglob('_quarto.yml'))
            self.assertEqual(len(roots),1)
            project=roots[0].parent
            data=project/"data"
            baseline={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.glob("*.yml")}
            mentoring_source=(project/"mentoring.qmd").read_bytes()
            shutil.copyfile(plugin/"examples/yaml-records.qmd",project/"grants.qmd")
            config=project/"_quarto.yml"
            text=config.read_text(encoding="utf-8")
            self.assertIn('- "*.qmd"',text)
            text=text.replace('- "*.qmd"','- "*.qmd"\n    - "!mentoring.qmd"')
            text=text.replace('      - href: mentoring.qmd\n        text: Mentoring','      - href: grants.qmd\n        text: Grants')
            config.write_text(text,encoding="utf-8")
            env=dict(os.environ)
            if env.get("TEST_R_LIBRARY"):env["R_LIBS_USER"]=env["TEST_R_LIBRARY"]
            env["QUARTO_R"]=r_bin
            def render():
                result=subprocess.run([quarto,"render"],cwd=project,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=300)
                self.assertEqual(result.returncode,0,result.stdout[-4000:]+result.stderr[-4000:])
            render()
            html=(project/"docs/grants.html").read_text(encoding="utf-8")
            self.assertIn("No records to display.",html)
            self.assertFalse((project/"docs/mentoring.html").exists())
            self.assertEqual((project/"mentoring.qmd").read_bytes(),mentoring_source)
            self.assertEqual(baseline,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.glob("*.yml")})
            home=(project/"docs/index.html").read_text(encoding="utf-8")
            self.assertIn('href="./grants.html"',home)
            self.assertNotIn('href="./mentoring.html"',home)
            (data/"grants.yml").write_text('- id: synthetic-only\n  title: "Example <script>alert(1)</script> & award"\n  sponsor: null\n  role: PI\n  total_support: PRIVATE_SENTINEL_928\n',encoding="utf-8")
            render()
            html=(project/"docs/grants.html").read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; award",html)
            self.assertNotIn("PRIVATE_SENTINEL_928",html)
            self.assertNotIn("No records to display.",html)
            self.assertFalse((project/"docs/mentoring.html").exists())
            for name,digest in baseline.items():
                if name!="grants.yml":self.assertEqual(hashlib.sha256((data/name).read_bytes()).hexdigest(),digest)
            self.assertEqual((project/"mentoring.qmd").read_bytes(),mentoring_source)

if __name__=="__main__":unittest.main()
