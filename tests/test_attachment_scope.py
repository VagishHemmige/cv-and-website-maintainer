"""F7: irrelevant preferences versus attachment authority, synthetic files only."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_attachments as base

helper = base.helper


class AttachmentScopeTests(unittest.TestCase):
    setUp = base.AttachmentTests.setUp
    cli = base.AttachmentTests.cli
    stage_pdf = base.AttachmentTests.stage_pdf
    stage_deck = base.AttachmentTests.stage_deck
    save = base.AttachmentTests.save
    flags = base.AttachmentTests.flags
    successful_powerpoint = base.AttachmentTests.successful_powerpoint

    def update_config(self):
        (self.state / 'config.json').write_text(json.dumps(self.config), encoding='utf-8')

    def approve(self, item):
        return self.save(item, '--privacy-reviewed', '--public-approved')

    def manifest(self, item):
        return Path(item['staged_pdf']).parent / 'manifest.json'

    def legacy(self, item):
        path = self.manifest(item)
        value = json.loads(path.read_text(encoding='utf-8'))
        del value['save_scope_version']; del value['save_scope_sha256']
        path.write_text(json.dumps(value), encoding='utf-8')

    def test_unrelated_checkin_change_saves_without_restage_or_manifest_rewrite(self):
        item = self.stage_pdf(); manifest_before = self.manifest(item).read_bytes()
        self.config['review'] = {'check_in': {'last_cycle_id':'next-cycle', 'manual_submission_state':'closed'}}
        self.update_config()
        self.assertEqual(self.approve(item)['status'], 'saved_bytes_verified')
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        self.assertEqual(len(list((self.state / 'attachments').iterdir())), 1)
        self.assertEqual(self.manifest(item).read_bytes(), manifest_before)

    def test_unrelated_setup_source_runtime_and_unknown_preferences_do_not_invalidate_pdf(self):
        item = self.stage_pdf()
        self.config.update(setup={'next_question_id':'new-question'}, discovery={'sources':['fixture']},
                           runtime={'powershell':'changed-after-conversion'}, unknown={'new':True})
        self.update_config()
        self.approve(item)
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())

    def test_formatting_and_object_key_order_do_not_invalidate_scope(self):
        item = self.stage_pdf()
        reordered = {key:self.config[key] for key in reversed(self.config)}
        reordered['attachments'] = dict(reversed(list(self.config['attachments'].items())))
        (self.state / 'config.json').write_text(json.dumps(reordered, indent=4), encoding='utf-8')
        self.assertEqual(self.approve(item)['status'], 'saved_bytes_verified')

    def test_all_attachment_setting_changes_require_review(self):
        item = self.stage_pdf(); original = copy.deepcopy(self.config)
        alternatives = [
            {'approved_pdf_dirs':['teaching','abstracts']},
            {'routes':{'teaching':'another-authorized-route'}},
            {'soffice':'different-converter'},
            {'future_privacy_policy':'changed'},
        ]
        for change in alternatives:
            with self.subTest(change=change):
                self.config = copy.deepcopy(original)
                self.config['attachments'].update(change); self.update_config()
                with self.assertRaisesRegex(ValueError, 'Attachment settings changed'):
                    self.approve(item)
                self.assertFalse(self.target.exists())
        self.assertEqual(len(list((self.state / 'attachments').iterdir())), 1)

    def test_revoked_destination_still_blocks_save(self):
        item = self.stage_pdf()
        self.config['attachments']['approved_pdf_dirs'] = ['abstracts']; self.update_config()
        with self.assertRaisesRegex(ValueError, 'not explicitly approved'):
            self.approve(item)
        self.assertFalse(self.target.exists())

    def test_changed_approval_policy_still_blocks_save(self):
        item = self.stage_pdf()
        self.config['approval_policy'] = 'automatic'; self.update_config()
        with self.assertRaisesRegex(ValueError, 'per_change approval required'):
            self.approve(item)
        self.assertFalse(self.target.exists())

    def test_changed_project_cannot_redirect_approved_pdf(self):
        item = self.stage_pdf()
        other = self.base / 'other-project'; (other / 'teaching').mkdir(parents=True)
        self.config['project_root'] = str(other); self.update_config()
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.approve(item)
        self.assertFalse(self.target.exists())
        self.assertFalse((other / 'teaching' / 'material.pdf').exists())

    def test_legacy_manifest_with_unchanged_profile_remains_usable(self):
        item = self.stage_pdf(); self.legacy(item)
        before = self.manifest(item).read_bytes()
        self.assertEqual(self.approve(item)['status'], 'saved_bytes_verified')
        self.assertEqual(self.manifest(item).read_bytes(), before)

    def test_legacy_manifest_with_changed_profile_is_not_silently_migrated(self):
        item = self.stage_pdf(); self.legacy(item)
        before = self.manifest(item).read_bytes()
        self.config['review'] = {'check_in':{'last_cycle_id':'later'}}; self.update_config()
        with self.assertRaisesRegex(ValueError, 'Legacy staged attachment profile changed'):
            self.approve(item)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.manifest(item).read_bytes(), before)
        self.assertEqual(len(list((self.state / 'attachments').iterdir())), 1)

    def test_unknown_or_incomplete_scope_metadata_fails_closed(self):
        item = self.stage_pdf(); path = self.manifest(item)
        original = json.loads(path.read_text(encoding='utf-8'))
        for version in (2, None, True):
            with self.subTest(version=version):
                value = dict(original, save_scope_version=version)
                path.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Unsupported attachment save-scope version'):
                    self.approve(item)
                self.assertFalse(self.target.exists())
        value = dict(original); del value['save_scope_sha256']
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Attachment settings changed'):
            self.approve(item)
        self.assertFalse(self.target.exists())

    def test_changed_pdf_is_still_blocked_after_unrelated_preference_change(self):
        item = self.stage_pdf()
        self.config['setup'] = {'status':'updated'}; self.update_config()
        staged = Path(item['staged_pdf']); staged.write_bytes(staged.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'staged_changed'):
            self.approve(item)
        self.assertFalse(self.target.exists())

    def test_scope_revoked_during_pdf_validation_blocks_public_creation(self):
        item = self.stage_pdf(); real = helper.pdf_pages
        def revoke(path):
            pages = real(path)
            self.config['attachments']['routes']['teaching'] = 'revoked-route'; self.update_config()
            return pages
        with patch.object(helper, 'pdf_pages', side_effect=revoke):
            with self.assertRaisesRegex(ValueError, 'Attachment settings changed'):
                self.approve(item)
        self.assertFalse(self.target.exists())

    def test_unrelated_change_during_pdf_validation_allows_exact_pdf(self):
        item = self.stage_pdf(); real = helper.pdf_pages
        def unrelated(path):
            pages = real(path)
            self.config['review'] = {'check_in':{'last_cycle_id':'while-reviewing'}}; self.update_config()
            return pages
        with patch.object(helper, 'pdf_pages', side_effect=unrelated):
            self.approve(item)
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())

    def test_powerpoint_is_not_reconverted_after_unrelated_preference_change(self):
        with patch.object(helper, 'powerpoint_shell', return_value='mock-pwsh'), \
                patch.object(helper.shutil, 'which', return_value=None), \
                patch.object(helper.subprocess, 'run', side_effect=self.successful_powerpoint) as converter:
            item = self.stage_deck(*self.flags())
            staged_bytes = Path(item['staged_pdf']).read_bytes()
            self.config['review'] = {'check_in':{'last_cycle_id':'later'}}; self.update_config()
            self.approve(item)
            self.assertEqual(converter.call_count, 1)
        self.assertEqual(self.target.read_bytes(), staged_bytes)
        self.assertEqual(len(list((self.state / 'attachments').iterdir())), 1)
