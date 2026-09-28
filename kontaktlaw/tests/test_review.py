"""Synthetic document, review-state, anchor and loopback-server regression tests."""
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/legal-review/scripts'))
import review_document as r
from test_comparison import make_docx, raw_docx


def grammar_packet(state, corrections=None):
    return {'original_version': state['original_version'], 'reviewed_complete_document': True,
            'protected_terms': ['Satıcı', 'Alıcı', 'AZN', 'ödəməlidir', 'ödəməməlidir'],
            'parties': [{'id': 'buyer', 'name': 'Alıcı', 'role': 'Alıcı', 'span_id': 's1',
                         'quote': 'Alıcı', 'occurrence': 1}],
            'corrections': corrections or []}


def correction(quote, replacement, span='s2', occurrence=1):
    return {'span_id': span, 'quote': quote, 'replacement': replacement,
            'occurrence': occurrence, 'reason': 'Təkrar boşluq aradan qaldırılır.',
            'meaning_preserved': True, 'verified': True}


def risk_packet(state, quote='Alıcı', span='s1', occurrence=1):
    return {'document_version': state['document_version'], 'selected_party': state['selected_party'],
            'reviewed_complete_document': True, 'findings': [{
                'title': 'Sintetik sınaq nəticəsi',
                'paragraphs': dict(zip(r.LABELS, ['1-ci bənd', quote, 'Sınaq izahı.',
                                                 'Sınaqdır; hüquqi iddia deyil.', 'Sınaq təklifi.', 'Orta'])),
                'anchors': [{'document_version': state['document_version'], 'span_id': span,
                             'quote': quote, 'occurrence': occurrence}]}]}


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = make_docx(self.base/'input.docx', ['Satıcı və Alıcı.', '2. Alıcı  ödənişi etməlidir. 100 AZN.',
                                                        '3. Eyni mətn. Eyni mətn.'])
        self.output = self.base/'review'
        self.state = r.prepare(self.source, self.output, mode='never')

    def ready(self, edits=None):
        return r.select_party(r.apply_grammar(self.state, grammar_packet(self.state, edits)), 'buyer')

    def test_prepare_idempotent_preserves_stage_and_source(self):
        original = self.source.read_bytes()
        ready = self.ready()
        r.save(self.output, ready)
        resumed = r.prepare(self.source, self.output, mode='never')
        self.assertEqual(resumed, ready)
        self.assertEqual(self.source.read_bytes(), original)

    def test_changed_source_and_options_rejected(self):
        with self.assertRaises(r.ReviewError):
            r.prepare(self.source, self.output, mode='auto')
        make_docx(self.source, ['Changed'])
        with self.assertRaises(r.ReviewError):
            r.prepare(self.source, self.output, mode='never')

    def test_output_boundaries(self):
        with self.assertRaises(r.ReviewError):
            r.output_dir(ROOT/'private-review')
        with self.assertRaises(r.ReviewError):
            r.prepare(self.source, self.base)

    def test_stage_order_and_party_change(self):
        with self.assertRaises(r.ReviewError):
            r.select_party(self.state, 'buyer')
        with self.assertRaises(r.ReviewError):
            r.finalize_findings(self.state, risk_packet(self.state))
        state = self.ready()
        with self.assertRaises(r.ReviewError):
            r.select_party(state, 'invented')
        state = r.finalize_findings(state, risk_packet(state))
        self.assertEqual(r.select_party(state, 'buyer'), state)
        general = r.select_party(state, 'general')
        self.assertEqual(general['findings'], [])
        self.assertEqual(general['stage'], 'party_selected')

    def test_grammar_retry_and_rewrite_guard(self):
        packet = grammar_packet(self.state, [correction('Alıcı  ödənişi', 'Alıcı ödənişi')])
        result = r.apply_grammar(self.state, packet)
        self.assertEqual(r.apply_grammar(result, packet), result)
        with self.assertRaises(r.ReviewError):
            r.apply_grammar(result, grammar_packet(self.state))
        self.assertIn('Alıcı  ödənişi', result['original'][1]['text'])
        self.assertIn('Alıcı ödənişi', result['corrected'][1]['text'])

    def test_grammar_protects_numbers_terms_negations(self):
        for before, after in [('100 AZN', '200 AZN'), ('Alıcı', 'Satıcı'),
                              ('100.50 AZN', '100,50 AZN'),
                              ('not required', 'required'), ('shall pay', 'may pay'),
                              ('ödəməlidir', 'ödəməməlidir')]:
            with self.subTest(before=before), self.assertRaises(r.ReviewError):
                r.check_grammar(before, after, ['Alıcı', 'ödəməlidir', 'ödəməməlidir'])

    def test_overlap_mismatch_and_missing_verification_fail_without_mutation(self):
        packets = []
        packets.append(grammar_packet(self.state, [correction('Alıcı', 'Alıcı'), correction('Alıcı', 'Other')]))
        packets.append(grammar_packet(self.state, [correction('absent', 'new')]))
        bad = grammar_packet(self.state, [correction('  ödənişi', ' ödənişi')])
        bad['corrections'][0]['meaning_preserved'] = False
        packets.append(bad)
        overlap = grammar_packet(self.state, [correction('  ödənişi', ' ödənişi'), correction('Alıcı  ödənişi','Alıcı ödənişi')])
        packets.append(overlap)
        original = copy.deepcopy(self.state)
        for packet in packets:
            with self.assertRaises(r.ReviewError):
                r.apply_grammar(self.state, packet)
        self.assertEqual(self.state, original)

    def test_original_mapping_after_shift_and_inside_replacement(self):
        state = self.ready([correction('Alıcı  ödənişi', 'Alıcı ödənişi')])
        result = r.finalize_findings(state, risk_packet(state, '100 AZN', 's2'))
        anchor = result['findings'][0]['anchors'][0]
        self.assertEqual(anchor['original']['quote'], '100 AZN')
        self.assertEqual(anchor['original']['start'], anchor['corrected']['start']+1)
        result = r.finalize_findings(state, risk_packet(state, 'ödənişi', 's2'))
        self.assertEqual(result['findings'][0]['anchors'][0]['original']['quote'], 'Alıcı  ödənişi')

    def test_second_occurrence_and_identical_paragraphs(self):
        state = self.ready()
        result = r.finalize_findings(state, risk_packet(state, 'Eyni mətn.', 's3', 2))
        anchor = result['findings'][0]['anchors'][0]
        self.assertEqual(anchor['corrected']['start'], state['corrected'][2]['text'].rindex('Eyni mətn.'))
        state['original'].append({**state['original'][2], 'id': 's4'})
        state['corrected'].append({**state['corrected'][2], 'id': 's4'})
        state['document_version'] = r.digest(state['corrected'])
        result = r.finalize_findings(state, risk_packet(state, 'Eyni mətn.', 's4', 1))
        self.assertEqual(result['findings'][0]['anchors'][0]['span_id'], 's4')

    def test_stale_packet_rejected_invalid_anchor_disabled(self):
        state = self.ready()
        packet = risk_packet(state)
        packet['document_version'] = 'stale'
        with self.assertRaises(r.ReviewError):
            r.finalize_findings(state, packet)
        for field, value in [('quote', 'absent'), ('span_id', 'missing'), ('occurrence', None),
                              ('document_version', 'stale')]:
            packet = risk_packet(state)
            packet['findings'][0]['anchors'][0][field] = value
            finding = r.finalize_findings(state, packet)['findings'][0]
            self.assertEqual(finding['anchors'], [])
            self.assertTrue(finding['link_error'])

    def test_exact_six_paragraphs_and_quote_consistency(self):
        state = self.ready()
        packet = risk_packet(state)
        packet['findings'][0]['paragraphs']['extra'] = 'not allowed'
        with self.assertRaises(r.ReviewError):
            r.finalize_findings(state, packet)
        packet = risk_packet(state)
        packet['findings'][0]['paragraphs']['Problemli mətn'] = 'Different quotation'
        self.assertTrue(r.finalize_findings(state, packet)['findings'][0]['link_error'])

    def test_unverified_ocr_is_not_edited_or_linked(self):
        self.state['original'][1]['method'] = 'ocr'
        self.state['corrected'][1]['method'] = 'ocr'
        packet = grammar_packet(self.state, [correction('  ödənişi', ' ödənişi')])
        with self.assertRaises(r.ReviewError):
            r.apply_grammar(self.state, packet)
        state = self.ready()
        self.assertTrue(r.finalize_findings(state, risk_packet(state, '100 AZN','s2'))['findings'][0]['link_error'])
        packet['verified_ocr'] = [{'span_id': 's2', 'quote': self.state['original'][1]['text'], 'visually_verified': True}]
        state = r.select_party(r.apply_grammar(self.state, packet), 'buyer')
        self.assertIsNone(r.finalize_findings(state, risk_packet(state, '100 AZN','s2'))['findings'][0]['link_error'])

    def test_unicode_and_multi_paragraph_selection(self):
        self.state['original'][2]['text'] = self.state['corrected'][2]['text'] = '🧾 Əmək müqaviləsi. Şərtlər.'
        state = self.ready()
        packet = risk_packet(state, 'Şərtlər.', 's3')
        packet['findings'][0]['paragraphs']['Problemli mətn'] += '\nAlıcı'
        packet['findings'][0]['anchors'].append({'document_version':state['document_version'], 'span_id':'s1','quote':'Alıcı','occurrence':1})
        finding = r.finalize_findings(state, packet)['findings'][0]
        self.assertEqual(len(finding['anchors']), 2)
        self.assertEqual(finding['anchors'][0]['original']['quote'], 'Şərtlər.')

    def test_tables_and_source_preservation(self):
        path = raw_docx(self.base/'table.docx', '<w:p><w:r><w:t>Başlıq</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Satıcı</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Alıcı</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        state = r.prepare(path, self.base/'table-review', mode='never')
        self.assertIn('table 1, row 1, cell 2', state['original'][2]['locator'])
        self.assertEqual(state['tables'][0]['rows'], [['Satıcı', 'Alıcı']])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_text_pdf_and_scan_coverage(self):
        import pymupdf
        pdf = self.base/'text.pdf'
        with pymupdf.open() as doc:
            doc.new_page().insert_text((50,50), 'Buyer pays 100 AZN.')
            doc.save(pdf)
        state = r.prepare(pdf, self.base/'pdf-review', mode='never')
        self.assertIn('Buyer pays', state['original'][0]['text'])
        self.assertEqual(state['original'][0]['page'], 1)
        from PIL import Image
        image = self.base/'scan.png'
        Image.new('RGB',(100,100),'white').save(image)
        state = r.prepare(image, self.base/'scan-review', mode='never')
        self.assertFalse(state['coverage']['extraction_complete'])
        self.assertEqual(state['original'], [])
        with self.assertRaises(r.ReviewError):
            r.apply_grammar(state,grammar_packet(state))

    @unittest.skipUnless(os.environ.get('KONTAKTLAW_RUN_OCR_TESTS') == '1', 'Opt-in real review OCR')
    def test_real_scan_review_does_not_link_unverified_ocr(self):
        from PIL import Image, ImageDraw, ImageFont
        image=Image.new('RGB',(2600,400),'white')
        font_path=os.environ.get('KONTAKTLAW_TEST_FONT','C:/Windows/Fonts/arial.ttf')
        ImageDraw.Draw(image).text((60,80),'Buyer shall pay 100 AZN within 30 days.',
                                  font=ImageFont.truetype(font_path,60),fill='black')
        path=self.base/'real-scan.png'
        image.save(path)
        state=r.prepare(path,self.base/'real-scan-review',languages='eng')
        self.assertFalse(state['coverage']['extraction_complete'])
        span=next(s for s in state['original'] if '100' in s['text'])
        self.assertEqual(span['method'],'ocr')
        packet=grammar_packet(state)
        packet['parties']=[]
        state=r.select_party(r.apply_grammar(state,packet),'general')
        result=r.finalize_findings(state,risk_packet(state,'100',span['id']))
        self.assertIn('visually verified',result['findings'][0]['link_error'])

    def test_scan_extraction_adapter_preserves_unverified_evidence(self):
        from PIL import Image
        image = self.base/'scan.png'
        Image.new('RGB',(100,100),'white').save(image)
        def append(_ocr, document, bitmap, locator, **meta):
            document['spans'].append({'id':'s1','text':'OCR müqavilə', 'locator':locator,'method':'ocr',**meta})
        with patch.object(r.OCR,'append',append):
            state = r.prepare(image,self.base/'ocr-review')
        self.assertEqual(state['original'][0]['method'],'ocr')
        self.assertEqual(state['verified_ocr'],[])


class ServerTests(unittest.TestCase):
    setUp = ReviewTests.setUp
    ready = ReviewTests.ready
    def test_server_routes_and_private_exports(self):
        state = self.ready([correction('  ödənişi', ' ödənişi')])
        r.save(self.output,state)
        server = r.make_server(self.output)
        worker = threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with urlopen(server.review_url+'review.json') as response:
            data = json.load(response)
            self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])
            self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertNotIn(str(self.source),json.dumps(data))
        with urlopen(server.review_url+'corrected.txt') as response:
            self.assertIn('Alıcı ödənişi',response.read().decode('utf-8-sig'))
            self.assertIn('attachment',response.headers['Content-Disposition'])
        parsed = urlsplit(server.review_url)
        for path, host in [('/', parsed.netloc),(parsed.path+'../review.json',parsed.netloc),
                           (parsed.path+'service.json',parsed.netloc),(parsed.path,'evil.example')]:
            conn = http.client.HTTPConnection('127.0.0.1',parsed.port)
            conn.request('GET',path,headers={'Host':host})
            self.assertEqual(conn.getresponse().status,404)
            conn.close()
        for filename in ['','viewer.js','viewer.css']:
            with urlopen(server.review_url+filename) as response:
                self.assertEqual(response.status,200)


if __name__ == '__main__':
    unittest.main()
