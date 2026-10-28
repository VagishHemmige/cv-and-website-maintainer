"""Helper responsibilities remain distinct from consumer review and authorization."""
from pathlib import Path
import unittest

TEXT=(Path(__file__).resolve().parents[1]/'skills/update-academic-records/SKILL.md').read_text(encoding='utf-8')

class HelperWorkflowDocumentationTests(unittest.TestCase):
    def test_helpers_own_snapshot_backup_and_revalidation(self):
        for phrase in ('Use helper-managed snapshots and backups','unique hash-verified backup of its target','Do not create duplicate manual copies','rather than separately running the same validator','helper receipt/status'):
            self.assertIn(phrase,TEXT)
        self.assertNotIn('Before the first record change of the run, copy all files',TEXT)
        self.assertNotIn('Revalidate the real files',TEXT)

    def test_consumer_approval_and_project_requirements_stay_explicit(self):
        for phrase in ('actual project instructions require an additional run-level backup','Inspect the actual website/CV consumers','separately check resource links and facts','STOP before any live write and request approval','Never bypass a helper blocker with an ad-hoc write'):
            self.assertIn(phrase,TEXT)

    def test_missing_validator_allows_assessment_without_saving(self):
        self.assertIn('safe parser may support a read-only assessment',TEXT)
        self.assertIn('hold saving pending until the required helper validation can run',TEXT)
        self.assertIn('counted occurrences under verification.md',TEXT)
        self.assertNotIn('conservative same-record/row-move limitations',TEXT)
