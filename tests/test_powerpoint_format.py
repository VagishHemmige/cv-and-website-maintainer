"""Real ZIP/XML checks and synthetic legacy-parser boundaries; no Office invocation."""
import io
import struct
import sys
import zipfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import test_attachments as fixtures
from test_attachments import deck, helper


class PowerPointFormatTests(unittest.TestCase):
    setUp=fixtures.AttachmentTests.setUp
    cli=fixtures.AttachmentTests.cli
    stage_deck=fixtures.AttachmentTests.stage_deck
    flags=fixtures.AttachmentTests.flags
    assert_no_preparation=fixtures.AttachmentTests.assert_no_preparation
    def reject(self, content=None, overrides=None):
        if content is not None:self.deck.write_bytes(content)
        elif overrides is not None:deck(self.deck,overrides)
        before=self.deck.read_bytes()
        with patch.object(helper,'powerpoint_shell') as probe, patch.object(helper.shutil,'copyfile') as copy:
            with self.assertRaises(ValueError):self.stage_deck(*self.flags())
            self.assert_no_preparation(probe);copy.assert_not_called()
        self.assertEqual(self.deck.read_bytes(),before)

    def test_junk_pptx_stops_before_copy_and_forgiving_converter(self):self.reject(b'not a deck')
    def test_pdf_renamed_pptx_rejected(self):self.reject(self.source.read_bytes())
    def test_empty_zip_rejected(self):
        with zipfile.ZipFile(self.deck,'w'):pass
        self.reject()
    def test_missing_presentation_part_rejected(self):self.reject(overrides={'ppt/presentation.xml':None})
    def test_word_package_renamed_pptx_rejected(self):
        self.reject(overrides={'[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'})
    def test_malformed_xml_rejected(self):self.reject(overrides={'ppt/presentation.xml':'<presentation'})
    def test_wrong_presentation_namespace_rejected(self):self.reject(overrides={'ppt/presentation.xml':'<presentation/>'})
    def test_external_relationship_rejected(self):
        with zipfile.ZipFile(self.deck) as package:rels=package.read('_rels/.rels').decode()
        self.reject(overrides={'_rels/.rels':rels.replace('Target=', 'TargetMode="External" Target=')})
    def test_duplicate_parts_rejected(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(self.deck,'a') as package:package.writestr('ppt/presentation.xml','<presentation/>')
        self.reject()
    def test_parent_path_rejected(self):self.reject(overrides={'../outside':'unread'})
    def test_dtd_rejected(self):self.reject(overrides={'ppt/presentation.xml':'<!DOCTYPE p [<!ENTITY x "text">]><presentation/>'})
    def test_utf16_dtd_rejected(self):self.reject(overrides={'ppt/presentation.xml':'<!DOCTYPE p [<!ENTITY x "text">]><presentation/>'.encode('utf-16')})
    def test_oversized_xml_rejected(self):self.reject(overrides={'ppt/presentation.xml':b' '*(8*1024*1024+1)})
    def test_crc_damage_in_non_xml_part_rejected(self):
        deck(self.deck,{'media.bin':b'UNIQUE_PAYLOAD_FOR_CRC'})
        raw=self.deck.read_bytes().replace(b'UNIQUE_PAYLOAD_FOR_CRC',b'UNIQUE_PAYLOAD_FOR_BAD',1)
        self.reject(raw)
    def test_strict_namespace_recognized(self):
        deck(self.deck,{'ppt/presentation.xml':'<p:presentation xmlns:p="http://purl.oclc.org/ooxml/presentationml/main"/>'})
        helper.powerpoint_format(self.deck,'.pptx')
    def slides(self):
        return {
          'ppt/presentation.xml':'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst></p:presentation>',
          'ppt/_rels/presentation.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/></Relationships>',
          'ppt/slides/slide1.xml':'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>'}
    def test_slide_relationship_recognized(self):
        deck(self.deck,self.slides());helper.powerpoint_format(self.deck,'.pptx')
    def test_missing_referenced_slide_rejected(self):
        parts=self.slides();parts['ppt/slides/slide1.xml']=None;self.reject(overrides=parts)
    def test_corrupt_referenced_slide_rejected(self):
        parts=self.slides();parts['ppt/slides/slide1.xml']='<sld';self.reject(overrides=parts)
    def test_missing_slide_relationship_rejected(self):
        parts=self.slides();parts['ppt/_rels/presentation.xml.rels']=None;self.reject(overrides=parts)
    def test_truncated_zip_rejected(self):self.reject(self.deck.read_bytes()[:-30])
    def test_encrypted_zip_flag_rejected(self):
        raw=bytearray(self.deck.read_bytes())
        for signature,offset in ((b'PK\x03\x04',6),(b'PK\x01\x02',8)):
            start=0
            while True:
                index=raw.find(signature,start)
                if index<0:break
                raw[index+offset]|=1;start=index+4
        self.reject(bytes(raw))
    def test_screening_precedes_format_read(self):
        with patch.object(helper,'powerpoint_format') as check:
            with self.assertRaises(ValueError):self.stage_deck('--private-copy-approved')
            check.assert_not_called()
    def test_copy_approval_precedes_format_read(self):
        with patch.object(helper,'powerpoint_format') as check:
            with self.assertRaises(ValueError):self.stage_deck('--source-screening','not_flagged')
            check.assert_not_called()
    def test_mutation_during_format_check_rejected_before_copy(self):
        def change(path,ext):path.write_bytes(b'changed')
        with patch.object(helper,'powerpoint_format',side_effect=change),patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'changed during'):self.stage_deck(*self.flags())
            self.assert_no_preparation(probe)
    def test_mutation_after_validation_rejected_before_copy(self):
        original=helper.write_json
        def change(path,value):
            original(path,value)
            if path.name=='staging.json':self.deck.write_bytes(b'changed after validation')
        with patch.object(helper,'write_json',side_effect=change),patch.object(helper.shutil,'copyfile') as copy,patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'source_copy'):self.stage_deck(*self.flags())
            copy.assert_not_called();probe.assert_not_called()
        self.assertFalse(self.target.exists())
    def test_junk_ppt_rejected_before_optional_parser(self):
        self.deck=self.base/'bad.ppt';self.deck.write_bytes(b'not compound')
        self.reject()
    def test_legacy_missing_parser_is_actionable_and_stops_preparation(self):
        self.deck=self.base/'legacy.ppt';self.deck.write_bytes(bytes.fromhex('d0cf11e0a1b11ae1')+b'0'*512)
        with patch.dict(sys.modules,{'olefile':None}),patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'requires olefile'):self.stage_deck(*self.flags())
            self.assert_no_preparation(probe)
    def legacy(self,missing=False,offset=0,token=0xE391C05F,truncated=False):
        self.deck=self.base/'legacy.ppt';self.deck.write_bytes(bytes.fromhex('d0cf11e0a1b11ae1'))
        current=bytearray(32);struct.pack_into('<H',current,2,4086);struct.pack_into('<II',current,12,token,offset)
        document=struct.pack('<HHI',0,4085,28)+b'0'*(0 if truncated else 28)
        class Ole:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def exists(self,name):return not missing and name in ('Current User','PowerPoint Document')
            def openstream(self,name):return io.BytesIO(current if name=='Current User' else document)
            def get_size(self,name):return len(document)
        return SimpleNamespace(OleFileIO=Ole,DEFECT_INCORRECT=30)
    def test_legacy_stream_recognition_with_synthetic_parser(self):
        module=self.legacy()
        with patch.dict(sys.modules,{'olefile':module}):helper.powerpoint_format(self.deck,'.ppt')
    def test_legacy_wrong_streams_rejected(self):
        module=self.legacy(missing=True)
        with patch.dict(sys.modules,{'olefile':module}):self.reject()
    def test_legacy_bad_offset_rejected(self):
        module=self.legacy(offset=1000)
        with patch.dict(sys.modules,{'olefile':module}):self.reject()
    def test_legacy_encrypted_token_rejected(self):
        module=self.legacy(token=0)
        with patch.dict(sys.modules,{'olefile':module}):self.reject()
    def test_legacy_truncated_edit_rejected(self):
        module=self.legacy(truncated=True)
        with patch.dict(sys.modules,{'olefile':module}):self.reject()
